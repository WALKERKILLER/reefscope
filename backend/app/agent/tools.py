"""Agent tools: read tools run immediately; action tools become proposals that a person approves.

Every number a tool returns is registered in the run's evidence ledger under a namespaced ID
(S1.v1.fish.mean_count, T1.b03.mean_count, …). The agent may cite numbers only through those IDs.
"""
import datetime
import math
import uuid

from django.db.models import Count

from app.models import AnalysisRun, EvaluationRun, ModelVersion, ObservationReport, Task, TrainingReport
from app.analysis import coral_query
from app.analysis.contracts import SETTINGS
from app.observation import facts as observation_facts
from app.observation.agent import segments as audit_segments
from app.observation.sources import SOURCES

MAX_BINS = 40


class ToolError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(code)
        self.code, self.detail = code, detail


def entry(label, value, unit, **extra):
    item = observation_facts.metric(label, value, unit, reason=extra.pop("reason", None), source=extra.pop("source", None))
    item["display"] = observation_facts.display(item)
    item["reason_text"] = observation_facts.REASONS.get(item["reason"], item["reason"])
    return item | extra


class Context:
    """Run-scoped state shared by tools: the site, the ledger and the namespace counters."""
    def __init__(self, run):
        self.run, self.site = run, run.session.site
        ledger = run.ledger or {}
        self.metrics, self.sets, self.counters = ledger.get("metrics", {}), ledger.get("sets", {}), ledger.get("counters", {})

    def namespace(self, letter):
        self.counters[letter] = self.counters.get(letter, 0) + 1
        return f"{letter}{self.counters[letter]}"

    def register(self, prefix, metrics):
        ids = []
        for key, item in metrics.items():
            name = f"{prefix}.{key}"
            self.metrics[name] = {field: item.get(field) for field in ("label", "value", "unit", "display", "status", "reason_text", "source", "user_display",
                                                                       "seek_s", "task_id")}
            ids.append(name)
        return ids

    def dump(self):
        return {"metrics": self.metrics, "sets": self.sets, "counters": self.counters}


def view(metrics, ids):
    """What the model sees for each registered ID: display value or N/A with the reason."""
    return {name: (f"{metrics[name]['display']} · {metrics[name]['label']}" if metrics[name]["value"] is not None
                   else f"N/A（{metrics[name]['reason_text']}）· {metrics[name]['label']}") for name in ids}


def completed_run(value, kind=None):
    try:
        run = AnalysisRun.objects.select_related("model", "task").filter(pk=uuid.UUID(str(value))).first()
    except ValueError:
        run = None
    if run is None:
        raise ToolError("unknown_run", "run_id 不存在，先用 list_videos 查看可用的 Run。")
    if run.status != "completed":
        raise ToolError("run_not_completed", f"这个 Run 的状态是 {run.status}，只有已完成的 Run 可以分析。")
    if kind and run.model.kind != kind:
        raise ToolError("run_kind_mismatch", f"这个工具只接受 {kind} Run。")
    return run


def number(args, key, low, high, default=None):
    value = args.get(key, default)
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ToolError("invalid_argument", f"{key} 应为 {low}–{high} 之间的数值。")
    return float(value)


# --- read tools ---

def update_plan(ctx, args):
    steps = args.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 8:
        raise ToolError("invalid_argument", "steps 应为 1–8 项。")
    plan = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("title"), str) or not 1 <= len(step["title"].strip()) <= 80 \
                or step.get("status", "pending") not in ("pending", "in_progress", "done", "skipped"):
            raise ToolError("invalid_argument", "每一步需要 title（≤ 80 字）和 status（pending / in_progress / done / skipped）。")
        plan.append({"title": step["title"].strip(), "status": step.get("status", "pending")})
    ctx.run.plan = plan
    return {"ok": True}, [], f"计划 {sum(s['status'] == 'done' for s in plan)}/{len(plan)}"


NO_SITE = "这个会话还没有归档到观测点。请用户在面板顶部选择观测点后再试。"


def get_site_overview(ctx, args):
    site = ctx.site
    if site is None:
        raise ToolError("no_site", NO_SITE)
    history = []
    for report in site.reports.order_by("-observed_on", "-created_at")[:10]:
        prefix = f"H{report.observed_on.strftime('%Y%m%d')}"
        picked = {key: report.payload["facts"]["metrics"][key] for key in ("site.fish.mean_count", "site.coral.bleached_coral_fraction", "env.baa_level")
                  if key in report.payload["facts"]["metrics"]}
        ids = ctx.register(prefix, picked)
        history.append({"report_id": str(report.pk), "observed_on": report.observed_on.isoformat(), "videos": len(report.payload["facts"]["videos"]),
                        "camera_motion": report.payload["facts"]["settings"]["camera_motion"], "metrics": view(ctx.metrics, ids)})
    depth = ctx.register("SITE", {"depth": entry("站点水深", site.depth_m, "meters", reason="not_provided")})
    result = {"site": site.name, "depth": view(ctx.metrics, depth), "notes": site.notes[:500], "report_count": site.reports.count(), "recent_reports": history}
    return result, depth + [name for item in history for name in item["metrics"]], f"{len(history)} 份历史报告"


def register_video(ctx, task):
    """Videos are named "视频 #N" to the model; the file name is shown to the user only."""
    return ctx.register(f"V{task.pk}", {"label": entry("视频", f"视频 #{task.pk}", "text", user_display=task.original_filename)})


def list_videos(ctx, args):
    videos = []
    tasks = Task.objects.annotate(n=Count("analysis_runs")).filter(n__gt=0).order_by("-created_at")[:30]
    ids = []
    for task in tasks:
        runs = []
        for run in task.analysis_runs.select_related("model").order_by("-created_at")[:6]:
            runs.append({"run_id": str(run.pk), "kind": run.model.kind, "status": run.status, "model_id": run.model_id,
                         "camera_motion": run.config_snapshot.get("settings", {}).get("camera_motion"), "created_at": run.created_at.date().isoformat()})
        ids += register_video(ctx, task)
        videos.append({"video_id": task.pk, "label_id": f"V{task.pk}.label", "uploaded": task.created_at.date().isoformat(), "runs": runs})
    missing = [{"video_id": v["video_id"], "missing_kinds": sorted({"fish", "coral"} - {r["kind"] for r in v["runs"] if r["status"] == "completed"})} for v in videos]
    return {"videos": videos, "coverage": [m for m in missing if m["missing_kinds"]]}, ids, f"{len(videos)} 段视频"


def compute_observation_metrics(ctx, args):
    run_ids = args.get("run_ids")
    if not isinstance(run_ids, list) or not 1 <= len(run_ids) <= observation_facts.MAX_RUNS:
        raise ToolError("invalid_argument", f"run_ids 应为 1–{observation_facts.MAX_RUNS} 个已完成的 Run。")
    runs = [completed_run(value) for value in run_ids]
    try:
        observed_on = datetime.date.fromisoformat(str(args.get("observed_on") or datetime.date.today().isoformat()))
        environment = observation_facts.validate_environment(args.get("environment"))
        built = observation_facts.build(ctx.site, observed_on, runs, environment)
    except ValueError as exc:
        raise ToolError(str(exc), "检查 run_ids（每段视频每种分析最多一个）和环境数据的取值范围。") from None
    prefix = ctx.namespace("S")
    ids = ctx.register(prefix, built["metrics"])
    ctx.sets[prefix] = {"run_ids": [str(run.pk) for run in runs], "observed_on": observed_on.isoformat(), "environment": environment}
    compared = built["comparison"]
    result = {"metrics_set": prefix, "metrics": view(ctx.metrics, ids),
              "videos": [{"label_id": f"{prefix}.v{v['index']}.label", "video_id": v["task_id"], "analyses": sorted(v["runs"])} for v in built["videos"]],
              "comparison": None if compared is None else {key: compared[key] for key in ("previous_observed_on", "comparable", "reasons")},
              "model_quality": built["model_quality"], "limitations": built["limitations"]}
    return result, ids, f"{prefix} · {len(ids)} 项指标"


def fish_frames_per_window(run, start, end):
    fps, frames = run.summary.get("fps"), run.summary.get("frame_count") or 0
    if not fps:
        raise ToolError("unknown_frame_rate", "视频帧率未知，无法按时间分段。")
    duration = frames / fps
    return fps, duration, max(0, round((min(end, duration) - start) * fps))


def fish_activity_timeline(ctx, args):
    run = completed_run(args.get("run_id"), "fish")
    fps, duration, _ = fish_frames_per_window(run, 0, math.inf)
    width = number(args, "bin_seconds", 1, 3600, 30)
    width = max(width, math.ceil(duration / MAX_BINS))
    counts, times, _ = observation_facts.fish_frames(run)
    bins = []
    for index in range(max(1, math.ceil(duration / width))):
        start, end = index * width, min((index + 1) * width, duration)
        frames = max(1, round((end - start) * fps))
        inside = [counts[f] for f in counts if start * 1000 <= times[f] < end * 1000]
        bins.append({"start": start, "end": end, "mean": sum(inside) / frames, "peak": max(inside, default=0)})
    prefix = ctx.namespace("T")
    metrics = {"bin_seconds": entry("分段长度", width, "seconds")}
    for index, item in enumerate(bins):
        span = f"{item['start']:.0f}–{item['end']:.0f} s"
        metrics[f"b{index:02d}.mean_count"] = entry(f"{span} 平均可见鱼数", item["mean"], "fish_per_frame")
        metrics[f"b{index:02d}.window"] = entry("时段", span, "text", seek_s=item["start"], task_id=run.task_id)
    busiest, quietest = max(range(len(bins)), key=lambda i: bins[i]["mean"]), min(range(len(bins)), key=lambda i: bins[i]["mean"])
    for name, index in (("busiest", busiest), ("quietest", quietest)):
        metrics[f"{name}.window"] = entry("最活跃时段" if name == "busiest" else "最安静时段", f"{bins[index]['start']:.0f}–{bins[index]['end']:.0f} s", "text",
                                          seek_s=bins[index]["start"], task_id=run.task_id)
        metrics[f"{name}.mean_count"] = entry(("最活跃" if name == "busiest" else "最安静") + "时段平均可见鱼数", bins[index]["mean"], "fish_per_frame")
    ids = ctx.register(prefix, metrics)
    note = "处理帧数按帧率估算；画面坐标，镜头运动未知时只描述画面。"
    return {"timeline": prefix, "bin_seconds": width, "metrics": view(ctx.metrics, ids), "note": note}, ids, f"{prefix} · {len(bins)} 个时段"


def fish_window_summary(ctx, args):
    run = completed_run(args.get("run_id"), "fish")
    start, end = number(args, "start_s", 0, 86400), number(args, "end_s", 0, 86400)
    if start is None or end is None or end <= start:
        raise ToolError("invalid_argument", "需要 start_s < end_s（秒）。")
    fps, duration, frames = fish_frames_per_window(run, start, end)
    if frames <= 0:
        raise ToolError("window_outside_video", "时间窗不在视频时长内。")
    counts, times, spans = observation_facts.fish_frames(run)
    inside = {f: counts[f] for f in counts if start * 1000 <= times[f] < end * 1000}
    tracks = {track for track, (first, last) in spans.items() if first < end * 1000 and last >= start * 1000}
    prefix = ctx.namespace("W")
    ids = ctx.register(prefix, {
        "window": entry("时间窗", f"{start:.0f}–{min(end, duration):.0f} s", "text", seek_s=start, task_id=run.task_id),
        "mean_count": entry("时间窗平均可见鱼数", sum(inside.values()) / frames, "fish_per_frame", source="SCHOBERND-2014"),
        "peak_count": entry("时间窗画面峰值", max(inside.values(), default=0), "fish"),
        "occupied_fraction": entry("时间窗有鱼帧比例", len(inside) / frames, "fraction"),
        "track_count": entry("时间窗内出现的追踪 ID", len(tracks), "count")})
    return {"window": prefix, "metrics": view(ctx.metrics, ids), "note": "处理帧数按帧率估算。"}, ids, prefix


def coral_frame_review(ctx, args):
    run = completed_run(args.get("run_id"), "coral")
    limit = int(number(args, "limit", 1, 10, 3))
    series = coral_query.summarize(run, coral_query.window({}))["series"]
    separated = [row for row in series if row["coral_share"] is not None]
    prefix = ctx.namespace("C")
    metrics, frames = {}, []
    groups = {"bleached": sorted((r for r in separated if r["bleached_coral_fraction"]), key=lambda r: -r["bleached_coral_fraction"])[:limit],
              "most_coral": sorted(separated, key=lambda r: -r["coral_share"])[:limit],
              "least_coral": sorted(separated, key=lambda r: r["coral_share"])[:limit]}
    labels = {"bleached": "白化比例最高", "most_coral": "珊瑚占比最高", "least_coral": "珊瑚占比最低"}
    for group, rows in groups.items():
        for rank, row in enumerate(rows, start=1):
            key = f"{group}{rank}"
            metrics[f"{key}.time"] = entry(f"{labels[group]}第 {rank} 帧的时间", row["timestamp_ms"] / 1000, "seconds", seek_s=row["timestamp_ms"] / 1000, task_id=run.task_id)
            metrics[f"{key}.coral_share"] = entry(f"{labels[group]}第 {rank} 帧珊瑚占比", row["coral_share"], "fraction")
            metrics[f"{key}.bleached_fraction"] = entry(f"{labels[group]}第 {rank} 帧白化比例", row["bleached_coral_fraction"], "fraction")
            frames.append({"group": group, "rank": rank, "frame": row["frame"], "timestamp_ms": row["timestamp_ms"], "run_id": str(run.pk)})
    metrics["unseparated_frames"] = entry("未分离背景的采样帧", len(series) - len(separated), "frames")
    ids = ctx.register(prefix, metrics)
    note = "没有白化像素时 bleached 组为空。帧时间可供人工在工作台复核掩膜。"
    return {"review": prefix, "metrics": view(ctx.metrics, ids), "frames": frames, "note": note}, ids, f"{prefix} · {len(frames)} 帧"


def get_playback_context(ctx, args):
    """What the observer sees on the monitoring wall at the moment they sent the message."""
    context = ctx.run.context or {}
    if not context.get("task_id"):
        raise ToolError("no_playback_context", "这个任务不是从监测大屏发起的，没有当前画面。")
    task = Task.objects.filter(pk=context["task_id"]).first()
    if task is None:
        raise ToolError("unknown_video", "监测大屏上的视频已被删除。")
    now = context.get("current_time_s") or 0.0
    prefix = ctx.namespace("P")
    metrics = {"label": entry("视频", f"视频 #{task.pk}", "text", user_display=task.original_filename),
               "time": entry("当前播放时刻", now, "seconds", seek_s=now, task_id=task.pk)}
    runs = {}
    if context.get("fish_run_id"):
        run = completed_run(context["fish_run_id"], "fish")
        counts, times, _ = observation_facts.fish_frames(run)
        fps, frames = run.summary.get("fps"), run.summary.get("frame_count") or 0
        frame = min(round(now * fps), max(frames - 1, 0)) if fps else None
        metrics["fish.visible_now"] = entry("当前帧可见鱼数", counts.get(frame, 0) if frame is not None else None, "fish", reason="unknown_frame_rate")
        metrics["fish.mean_count"] = entry("全片平均可见鱼数", sum(counts.values()) / frames if frames else None, "fish_per_frame",
                                           reason="no_processed_frames", source="SCHOBERND-2014")
        runs["fish_run_id"] = str(run.pk)
    if context.get("coral_run_id"):
        run = completed_run(context["coral_run_id"], "coral")
        series = [row for row in coral_query.summarize(run, coral_query.window({}))["series"] if row["coral_share"] is not None]
        if series:
            row = min(series, key=lambda r: abs(r["timestamp_ms"] / 1000 - now))
            metrics["coral.sample_time"] = entry("最近的珊瑚采样帧时间", row["timestamp_ms"] / 1000, "seconds", seek_s=row["timestamp_ms"] / 1000, task_id=task.pk)
            metrics["coral.coral_share"] = entry("该采样帧珊瑚像素占比", row["coral_share"], "fraction")
            metrics["coral.bleached_fraction"] = entry("该采样帧白化像素比例", row["bleached_coral_fraction"], "fraction")
        runs["coral_run_id"] = str(run.pk)
    ids = ctx.register(prefix, metrics)
    return {"context": prefix, "video_id": task.pk, "label_id": f"{prefix}.label", **runs, "metrics": view(ctx.metrics, ids),
            "note": "当前帧可见鱼数是单帧计数，会随画面快速变化；需要更稳定的描述时用 fish_window_summary 看前后一段时间。"}, ids, f"{prefix} · {len(ids)} 项"


def model_evidence(ctx, args):
    model = ModelVersion.objects.filter(pk=str(args.get("model_id", ""))).first()
    if model is None:
        raise ToolError("unknown_model", "model_id 不存在。")
    report = TrainingReport.objects.filter(model=model).order_by("-created_at").first()
    evaluations = EvaluationRun.objects.filter(model=model).count()
    return {"model_id": model.pk, "kind": model.kind, "labels": model.labels, "training_reports": TrainingReport.objects.filter(model=model).count(),
            "independent_evaluations": evaluations, "latest_report_missing_inputs": report.payload.get("missing_inputs", []) if report else None,
            "note": "没有独立评估时，不能评价模型精度。"}, [], f"{model.pk} · 独立评估 {evaluations}"


def crw_alert_level(ctx, args):
    hotspot, dhw = number(args, "hotspot_c", -15, 15), number(args, "dhw_c_weeks", 0, 100)
    code, label, impact = observation_facts.alert_area(hotspot, dhw)
    prefix = ctx.namespace("E")
    ids = ctx.register(prefix, {"hotspot": entry("HotSpot", hotspot, "celsius", reason="not_provided"), "dhw": entry("DHW", dhw, "c_weeks", reason="not_provided"),
                                "level": entry("CRW 白化警报等级", label if code else None, "text", reason=label if not code else None, source="CRW-BAA"),
                                "impact": entry("潜在影响", impact, "text", reason="no_alert_level")})
    return {"alert": prefix, "metrics": view(ctx.metrics, ids)}, ids, f"{prefix} · {label if code else 'N/A'}"


def search_references(ctx, args):
    query = str(args.get("query", "")).strip().lower()
    words = [word for word in query.replace("，", " ").split() if word]
    hits = {key: card for key, card in SOURCES.items()
            if not words or any(word in (card["title"] + card["supports"] + card["limits"] + key).lower() for word in words)}
    return {"sources": {key: {name: card[name] for name in ("title", "year", "supports", "limits")} for key, card in (hits or SOURCES).items()}}, [], f"{len(hits or SOURCES)} 张资料卡"


# --- action tools: prepare() validates and builds the proposal; apply() runs after approval ---

def prepare_analysis_run(ctx, args):
    kind = args.get("kind")
    task = Task.objects.filter(pk=args.get("video_id")).first() if type(args.get("video_id")) is int else None
    if task is None or kind not in SETTINGS:
        raise ToolError("invalid_argument", "需要已有视频的 video_id 和 kind（fish 或 coral）。")
    model = ModelVersion.objects.filter(kind=kind).order_by("-created_at").first()
    if model is None:
        raise ToolError("no_model_for_kind", f"平台还没有注册 {kind} 模型。")
    if task.analysis_runs.filter(model__kind=kind, status__in=("queued", "running")).exists():
        raise ToolError("run_already_pending", "这段视频已有排队或进行中的同类分析。")
    return {"video_id": task.pk, "filename": task.original_filename, "kind": kind, "model_id": model.pk, "settings": SETTINGS[kind]({})}


def apply_analysis_run(ctx, proposal):
    model = ModelVersion.objects.get(pk=proposal["model_id"])
    run = AnalysisRun.objects.create(task_id=proposal["video_id"], model=model,
                                     config_snapshot={"models": {model.kind: model.pk}, "model_sha256": model.sha256, "settings": proposal["settings"]})
    return {"run_id": str(run.pk), "status": "queued", "note": "分析已排队，由分析 Worker 处理；完成前不能用于计算指标。"}


SECTIONS = ("observations", "interpretation", "limitations", "next_steps")


def prepare_report(ctx, args):
    prefix, narrative = args.get("metrics_set"), args.get("narrative")
    if ctx.site is None:
        raise ToolError("no_site", "保存报告需要观测点。" + NO_SITE)
    if prefix not in ctx.sets:
        raise ToolError("unknown_metrics_set", "先调用 compute_observation_metrics，再用返回的 metrics_set 起草报告。")
    if not isinstance(narrative, dict) or not isinstance(narrative.get("summary"), str) or not narrative["summary"].strip() or len(narrative["summary"]) > 1200:
        raise ToolError("invalid_narrative", "narrative.summary 必填，不超过 1200 字。")
    for name in SECTIONS:
        items = narrative.get(name, [])
        if not isinstance(items, list) or len(items) > 8 or not all(isinstance(x, str) and len(x) <= 800 for x in items):
            raise ToolError("invalid_narrative", f"narrative.{name} 应为不超过 8 条、每条 ≤ 800 字的字符串数组。")
    scoped = {name[len(prefix) + 1:]: item for name, item in ctx.metrics.items() if name.startswith(prefix + ".")}
    audit = {"unverified_numbers": [], "unknown_metrics": [], "unknown_citations": [], "citations": []}
    # The report stores unprefixed IDs so its segments resolve against its own facts.
    strip = lambda text: text.replace("{{" + prefix + ".", "{{").replace("{{ " + prefix + ".", "{{")
    parts = {"summary": audit_segments(strip(narrative["summary"]), scoped, audit),
             **{name: [audit_segments(strip(x), scoped, audit) for x in narrative.get(name, []) if x.strip()] for name in SECTIONS}}
    audit = {key: sorted(set(values)) for key, values in audit.items()}
    return {"metrics_set": prefix, **ctx.sets[prefix], "narrative": parts, "audit": audit}


def apply_report(ctx, proposal):
    from app.observation import report as render
    runs = [completed_run(value) for value in proposal["run_ids"]]
    built = observation_facts.build(ctx.site, datetime.date.fromisoformat(proposal["observed_on"]), runs, proposal["environment"])
    record = {"status": "generated", "mode": "agent_run", "agent_run_id": str(ctx.run.pk), **{k: ctx.run.agent.get(k) for k in ("prompt_version", "api_format", "model", "host")},
              "narrative": proposal["narrative"], "audit": proposal["audit"], "latency_ms": None, "usage": ctx.run.usage, "error_code": None, "http_status": None}
    payload, markdown, html = render.make(built, record)
    item = ObservationReport.objects.create(site=ctx.site, observed_on=built["observed_on"], payload=payload, markdown=markdown, html=html)
    return {"report_id": str(item.pk), "title": payload["title"]}


def schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required)}


ENV = {"type": "object", "description": "用户提供的环境数据（可选）。只填用户明确给出的数值。",
       "properties": {"sst_c": {"type": "number"}, "in_situ_temp_c": {"type": "number"}, "hotspot_c": {"type": "number"},
                      "dhw_c_weeks": {"type": "number"}, "source": {"type": "string"}, "product_date": {"type": "string", "description": "YYYY-MM-DD"}}}
NARRATIVE = {"type": "object", "required": ["summary"], "properties": {
    "summary": {"type": "string", "description": "两三句总体结论"},
    **{name: {"type": "array", "items": {"type": "string"}} for name in SECTIONS}}}

TOOLS = {
    "update_plan": {"kind": "read", "title": "更新计划", "handler": update_plan,
                    "description": "记录或更新本次任务的执行计划（1–8 步）。开始时先调用一次，完成或调整步骤后再次调用，用户会看到这份清单。",
                    "parameters": schema({"steps": {"type": "array", "items": schema({"title": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "done", "skipped"]}}, ["title", "status"])}}, ["steps"])},
    "get_playback_context": {"kind": "read", "title": "读取当前画面", "handler": get_playback_context,
                             "description": "读取用户在监测大屏上正在看的视频、分析 Run 和当前播放时刻，以及该时刻的可见鱼数和最近的珊瑚采样帧。用户问“现在”“这里”“当前画面”时先调用。",
                             "parameters": schema({})},
    "get_site_overview": {"kind": "read", "title": "读取观测点概况", "handler": get_site_overview,
                          "description": "读取当前观测点的水深、备注和最近 10 份报告的关键指标，用于了解历史与趋势。",
                          "parameters": schema({})},
    "list_videos": {"kind": "read", "title": "列出视频与分析", "handler": list_videos,
                    "description": "列出平台中的视频（video_id）及其鱼类、珊瑚分析 Run 的状态、模型和机位，并指出哪些视频缺少已完成的分析。",
                    "parameters": schema({})},
    "compute_observation_metrics": {"kind": "read", "title": "计算观测指标", "handler": compute_observation_metrics,
                                    "description": "对选定的已完成 Run 计算确定性观测指标（鱼类 MeanCount、峰值、轨迹；珊瑚像素占比、白化比例；CRW 等级；与上次报告比较）。返回 metrics_set（如 S1）和带命名空间的指标 ID。每段视频每种分析最多一个 Run。",
                                    "parameters": schema({"run_ids": {"type": "array", "items": {"type": "string"}}, "observed_on": {"type": "string", "description": "观测日期 YYYY-MM-DD，默认今天"}, "environment": ENV}, ["run_ids"])},
    "fish_activity_timeline": {"kind": "read", "title": "鱼类活动时间线", "handler": fish_activity_timeline,
                               "description": "把一个鱼类 Run 按时间分段（默认 30 s，最多 40 段），给出每段的平均可见鱼数以及最活跃、最安静的时段。",
                               "parameters": schema({"run_id": {"type": "string"}, "bin_seconds": {"type": "number"}}, ["run_id"])},
    "fish_window_summary": {"kind": "read", "title": "时间窗鱼类统计", "handler": fish_window_summary,
                            "description": "统计鱼类 Run 在指定时间窗（秒）内的平均可见鱼数、峰值、有鱼帧比例和出现的追踪 ID 数，用于深入查看某个时段。",
                            "parameters": schema({"run_id": {"type": "string"}, "start_s": {"type": "number"}, "end_s": {"type": "number"}}, ["run_id", "start_s", "end_s"])},
    "coral_frame_review": {"kind": "read", "title": "珊瑚采样帧复核", "handler": coral_frame_review,
                           "description": "找出珊瑚 Run 中白化比例最高、珊瑚占比最高和最低的采样帧及其时间，供人工复核掩膜。",
                           "parameters": schema({"run_id": {"type": "string"}, "limit": {"type": "integer"}}, ["run_id"])},
    "model_evidence": {"kind": "read", "title": "查看模型证据", "handler": model_evidence,
                       "description": "查看模型的类别、训练报告数、独立评估数和缺失的评估输入，用于说明结果的可信边界。",
                       "parameters": schema({"model_id": {"type": "string"}}, ["model_id"])},
    "crw_alert_level": {"kind": "read", "title": "计算 CRW 警报等级", "handler": crw_alert_level,
                        "description": "按 NOAA Coral Reef Watch v3.1 根据 HotSpot 与 DHW 计算白化警报等级。只使用用户提供的数值。",
                        "parameters": schema({"hotspot_c": {"type": "number"}, "dhw_c_weeks": {"type": "number"}}, ["hotspot_c"])},
    "search_references": {"kind": "read", "title": "检索资料卡", "handler": search_references,
                          "description": "按关键词检索平台核对过的文献与方法资料卡，返回 ID、适用范围和限制。引用时写 [ID]。",
                          "parameters": schema({"query": {"type": "string"}})},
    "propose_analysis_run": {"kind": "action", "title": "提议运行分析", "prepare": prepare_analysis_run, "apply": apply_analysis_run,
                             "description": "提议为某段视频排队一次鱼类或珊瑚分析（使用最新注册的模型和默认参数）。需要用户批准；批准后由分析 Worker 处理，本次任务中不会完成。",
                             "parameters": schema({"video_id": {"type": "integer"}, "kind": {"type": "string", "enum": ["fish", "coral"]}}, ["video_id", "kind"])},
    "propose_observation_report": {"kind": "action", "title": "提议保存观测报告", "prepare": prepare_report, "apply": apply_report,
                                   "description": "用一个 metrics_set 的指标起草观测报告并提交用户批准。narrative 中的数值只能写该 metrics_set 的占位符，如 {{S1.v1.fish.mean_count}}；平台先审计，有问题会退回。批准后保存为不可修改的报告。",
                                   "parameters": schema({"metrics_set": {"type": "string"}, "narrative": NARRATIVE}, ["metrics_set", "narrative"])},
}


def definitions():
    return [{"name": name, "description": tool["description"], "parameters": tool["parameters"]} for name, tool in TOOLS.items()]
