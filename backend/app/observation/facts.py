"""Deterministic observation facts: every number in a report comes from here, never from the agent.

Fish counts follow MeanCount (Schobernd et al. 2014): tracked boxes per processed frame, where every
frame is processed (`tracking_frame_stride` is fixed at 1), so frames without fish count as zero.
Coral shares reuse `coral_query.summarize`. Bleaching Alert Area levels follow NOAA CRW v3.1.
"""
import datetime
import math
import statistics

from app.models import EvaluationRun, ObservationReport
from app.analysis import coral_query
from app.analysis.query import parameters, records
from app.analysis.summary import summarize as fish_summary

SCHEMA = "observation-facts/v1"
MAX_RUNS = 8
ENVIRONMENT_RANGES = {"sst_c": (-5, 45), "in_situ_temp_c": (-5, 45), "hotspot_c": (-15, 15), "dhw_c_weeks": (0, 100)}
BAA_LEVELS = [
    (4, "warning", "白化预警（Bleaching Warning）", "可能出现白化"),
    (8, "alert_1", "白化警报 1 级（Alert Level 1）", "可能出现礁区范围的白化"),
    (12, "alert_2", "白化警报 2 级（Alert Level 2）", "可能出现礁区范围的白化，热敏感珊瑚死亡"),
    (16, "alert_3", "白化警报 3 级（Alert Level 3）", "可能出现多物种死亡"),
    (20, "alert_4", "白化警报 4 级（Alert Level 4）", "可能出现严重的多物种死亡（超过 50% 的珊瑚）"),
    (math.inf, "alert_5", "白化警报 5 级（Alert Level 5）", "可能出现几乎全部死亡（超过 80% 的珊瑚）"),
]


REASONS = {
    "no_processed_frames": "没有处理过的帧", "no_fish_observed": "没有检测到鱼", "no_tracks": "没有追踪轨迹",
    "no_observations": "没有追踪观测", "missing_independent_ground_truth": "需要独立的人工标注测试集",
    "missing_manual_identity_ground_truth": "需要连续帧的人工身份真值", "no_sampled_frames": "没有采样帧",
    "no_background_separated_frames": "没有背景已分离的采样帧", "no_coral_pixels": "画面中没有识别到珊瑚像素",
    "requires_approved_benthic_roi": "需要经批准的底栖 ROI 与覆盖率调查方法", "requires_colony_level_survey": "需要群体级的现场调查",
    "no_local_bleached_ground_truth": "没有本地白化标注真值", "model_has_three_classes_only": "当前模型只区分背景、未白化、白化三类",
    "not_provided": "未录入", "missing_hotspot": "需要 HotSpot", "missing_dhw": "HotSpot ≥ 1 °C 时需要 DHW 才能分级",
    "inconsistent_hotspot_and_dhw": "HotSpot ≥ 1 °C 时 DHW 应大于 0，请核对录入值", "no_alert_level": "没有对应的警报等级",
    "unknown_frame_rate": "视频帧率未知", "not_recorded": "上次报告未记录", "not_computable": "无法计算",
    "model_changed": "使用的模型不同", "fish_settings_changed": "鱼类分析参数不同", "coral_settings_changed": "珊瑚分析参数不同",
    "camera_motion_not_fixed": "镜头不是两次都标记为固定机位",
}


def metric(label, value, unit, *, reason=None, denominator=None, numerator=None, source=None):
    return {"label": label, "value": value, "unit": unit, "status": "available" if value is not None else "unavailable",
            "reason": None if value is not None else reason, "denominator": denominator, "numerator": numerator, "source": source}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def display(item):
    value, unit = item["value"], item["unit"]
    if value is None:
        return "N/A"
    if unit == "text":
        return str(value)
    if unit == "fraction":
        percent = value * 100
        if percent == 0 or percent >= 1:
            return f"{percent:.1f}%"
        return f"{percent:.2f}%" if percent >= 0.01 else "<0.01%"
    formats = {"fish_per_frame": "{:.2f} 尾/帧", "fish": "{:,.0f} 尾", "count": "{:,.0f}", "frames": "{:,.0f} 帧",
               "seconds": "{:.1f} s", "track_seconds": "{:,.0f} track-s", "c_weeks": "{:.1f} °C-weeks", "celsius": "{:.2f} °C",
               "meters": "{:.1f} m", "ms": "{:.0f} ms"}
    return formats.get(unit, "{:.4g}").format(value)


def fish_frames(run):
    """One pass over observed tracks: per-frame counts (deduplicated by ID), frame times and track spans."""
    counts, times, spans = {}, {}, {}
    previous_frame, frame_ids = None, set()
    for point in records(run):
        if point.get("observed") is not True:
            continue
        frame, timestamp = point["frame"], point["timestamp_ms"]
        if previous_frame != frame:
            previous_frame, frame_ids = frame, set()
        if point["track_id"] in frame_ids:
            continue
        frame_ids.add(point["track_id"])
        counts[frame] = counts.get(frame, 0) + 1
        times[frame] = timestamp
        first, last = spans.get(point["track_id"], (timestamp, timestamp))
        spans[point["track_id"]] = (min(first, timestamp), max(last, timestamp))
    return counts, times, spans


def fish_metrics(prefix, run):
    frames = run.summary.get("frame_count") or 0
    counts, times, spans = fish_frames(run)
    window = fish_summary(run, parameters({}))["metrics"]
    total = sum(counts.values())
    peak_frame = max(counts, key=lambda frame: (counts[frame], -frame)) if counts else None
    durations = [(last - first) / 1000 for first, last in spans.values()]
    no_frames = None if frames else "no_processed_frames"
    return {
        f"{prefix}.fish.mean_count": metric("平均可见鱼数（MeanCount）", ratio(total, frames), "fish_per_frame", reason=no_frames,
                                            numerator=total, denominator=frames, source="SCHOBERND-2014"),
        f"{prefix}.fish.peak_count": metric("画面峰值鱼数（单帧最多）", counts[peak_frame] if counts else (0 if frames else None), "fish",
                                            reason=no_frames, source="SCHOBERND-2014"),
        f"{prefix}.fish.peak_time": metric("峰值出现时间", times[peak_frame] / 1000 if counts else None, "seconds",
                                           reason="no_fish_observed" if frames else no_frames),
        f"{prefix}.fish.occupied_fraction": metric("有鱼帧比例", ratio(len(counts), frames), "fraction", reason=no_frames,
                                                   numerator=len(counts), denominator=frames),
        f"{prefix}.fish.track_count": metric("追踪 ID 数", len(spans), "count"),
        f"{prefix}.fish.track_seconds": metric("轨迹占据时长", window["track_seconds"]["value"], "track_seconds"),
        f"{prefix}.fish.median_track_duration": metric("轨迹时长中位数", statistics.median(durations) if durations else None, "seconds",
                                                       reason="no_tracks"),
        f"{prefix}.fish.tracks_over_5s": metric("持续 5 s 以上的轨迹", sum(d >= 5 for d in durations), "count"),
        f"{prefix}.fish.mean_confidence": metric("平均检测置信度", window["mean_confidence"]["value"], "fraction", reason="no_observations"),
        f"{prefix}.fish.ap50": metric("检测 AP50", None, "fraction", reason="missing_independent_ground_truth"),
        f"{prefix}.fish.idf1": metric("追踪 IDF1 / HOTA", None, "fraction", reason="missing_manual_identity_ground_truth", source="HOTA-2021"),
    }


def coral_metrics(prefix, run):
    result = coral_query.summarize(run, coral_query.window({}))
    m, series = result["metrics"], result["series"]
    shares = [row["coral_share"] for row in series if row["coral_share"] is not None]
    separated = [row for row in coral_query.frames(run) if row["background_separated"]]
    coral = sum(row["pixel_counts"]["1"] + row["pixel_counts"]["2"] for row in separated)
    bleached = sum(row["pixel_counts"]["2"] for row in separated)
    area = sum(row["width"] * row["height"] for row in separated)
    pick = lambda key: m[key]["value"]
    return {
        f"{prefix}.coral.sampled_frames": metric("采样帧", pick("sampled_frames"), "frames"),
        f"{prefix}.coral.separated_frames": metric("背景已分离的采样帧", pick("background_separated_frames"), "frames"),
        f"{prefix}.coral.coral_pixel_share": metric("珊瑚像素占画面比例", pick("coral_pixel_share"), "fraction",
                                                    reason=m["coral_pixel_share"]["reason"], numerator=coral, denominator=area, source="GCRMN-2020"),
        f"{prefix}.coral.coral_share_min": metric("单帧珊瑚占比最低", min(shares) if shares else None, "fraction", reason="no_background_separated_frames"),
        f"{prefix}.coral.coral_share_max": metric("单帧珊瑚占比最高", max(shares) if shares else None, "fraction", reason="no_background_separated_frames"),
        f"{prefix}.coral.bleached_coral_fraction": metric("珊瑚像素中的白化比例", pick("bleached_coral_fraction"), "fraction",
                                                          reason=m["bleached_coral_fraction"]["reason"], numerator=bleached, denominator=coral,
                                                          source="AGRRA-2023"),
        f"{prefix}.coral.bleached_frames": metric("出现白化像素的采样帧", sum(row["bleached_share"] > 0 for row in series), "frames"),
        f"{prefix}.coral.cover": metric("活珊瑚覆盖率", None, "fraction", reason="requires_approved_benthic_roi", source="BEIJBOM-2015"),
        f"{prefix}.coral.colony_prevalence": metric("群体白化发生率", None, "fraction", reason="requires_colony_level_survey", source="AGRRA-2023"),
        f"{prefix}.coral.bleaching_accuracy": metric("白化分割精度", None, "fraction", reason="no_local_bleached_ground_truth"),
        f"{prefix}.coral.dead_algae": metric("死亡珊瑚 / 藻覆比例", None, "fraction", reason="model_has_three_classes_only"),
    }


def pooled(kind, runs):
    """Site-level values pooled from raw numerators and denominators, not averaged across videos."""
    total = lambda name, field: sum(item[f"{prefix}.{kind}.{name}"][field] or 0 for prefix, item in runs)
    if kind == "fish":
        boxes, occupied, frames = total("mean_count", "numerator"), total("occupied_fraction", "numerator"), total("mean_count", "denominator")
        peaks = [item[f"{prefix}.fish.peak_count"]["value"] for prefix, item in runs if item[f"{prefix}.fish.peak_count"]["value"] is not None]
        return {
            "site.fish.mean_count": metric("平均可见鱼数（全部视频合并）", ratio(boxes, frames), "fish_per_frame", reason="no_processed_frames",
                                           numerator=boxes, denominator=frames, source="SCHOBERND-2014"),
            "site.fish.peak_count": metric("画面峰值鱼数（全部视频）", max(peaks) if peaks else None, "fish", reason="no_processed_frames"),
            "site.fish.occupied_fraction": metric("有鱼帧比例（全部视频合并）", ratio(occupied, frames), "fraction", reason="no_processed_frames",
                                                  numerator=occupied, denominator=frames),
        }
    coral, area, bleached = total("coral_pixel_share", "numerator"), total("coral_pixel_share", "denominator"), total("bleached_coral_fraction", "numerator")
    return {
        "site.coral.coral_pixel_share": metric("珊瑚像素占画面比例（全部视频合并）", ratio(coral, area), "fraction",
                                               reason="no_background_separated_frames", numerator=coral, denominator=area),
        "site.coral.bleached_coral_fraction": metric("珊瑚像素中的白化比例（全部视频合并）", ratio(bleached, coral), "fraction",
                                                     reason="no_coral_pixels" if area else "no_background_separated_frames",
                                                     numerator=bleached, denominator=coral, source="AGRRA-2023"),
    }


def validate_environment(raw):
    if raw is None:
        return None
    allowed = set(ENVIRONMENT_RANGES) | {"source", "product_date"}
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise ValueError("invalid_environment")
    result = {}
    for key, (low, high) in ENVIRONMENT_RANGES.items():
        value = raw.get(key)
        if value is None or value == "":
            result[key] = None
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"invalid_{key}")
        result[key] = float(value)
    source = raw.get("source") or ""
    if not isinstance(source, str) or len(source) > 200:
        raise ValueError("invalid_environment_source")
    result["source"] = source.strip()
    product_date = raw.get("product_date") or None
    if product_date is not None:
        try:
            product_date = datetime.date.fromisoformat(product_date).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid_product_date") from exc
    result["product_date"] = product_date
    return result if any(result[key] is not None for key in ENVIRONMENT_RANGES) else None


def alert_area(hotspot, dhw):
    """NOAA CRW v3.1 Bleaching Alert Area. Alert levels need both HotSpot ≥ 1 °C and DHW."""
    if hotspot is None:
        return None, "missing_hotspot", None
    if hotspot <= 0:
        return "no_stress", "无胁迫（No Stress）", None
    if hotspot < 1:
        return "watch", "白化观察（Bleaching Watch）", None
    if dhw is None:
        return None, "missing_dhw", None
    if dhw <= 0:
        return None, "inconsistent_hotspot_and_dhw", None
    for upper, code, label, impact in BAA_LEVELS:
        if dhw < upper:
            return code, label, impact


def environment_metrics(environment):
    if environment is None:
        return {}
    code, label, impact = alert_area(environment["hotspot_c"], environment["dhw_c_weeks"])
    return {
        "env.sst": metric("海表温度 SST（卫星）", environment["sst_c"], "celsius", reason="not_provided", source="CRW-BAA"),
        "env.in_situ_temp": metric("原位水温", environment["in_situ_temp_c"], "celsius", reason="not_provided"),
        "env.hotspot": metric("HotSpot", environment["hotspot_c"], "celsius", reason="not_provided", source="CRW-BAA"),
        "env.dhw": metric("Degree Heating Week", environment["dhw_c_weeks"], "c_weeks", reason="not_provided", source="CRW-BAA"),
        "env.baa_level": metric("CRW 白化警报等级", label if code else None, "text", reason=label if not code else None, source="CRW-BAA"),
        "env.baa_impact": metric("CRW 对应的潜在影响", impact, "text", reason="no_alert_level"),
    }


GENERAL_LIMITATIONS = [
    "鱼类数量是模型追踪框计数，属于相对丰度指标，不是个体数量或密度；追踪 ID 会因遮挡和断轨重复。",
    "珊瑚统计基于画面像素，不等于底栖覆盖率；白化像素比例不等于群体白化发生率。",
    "同一视频的帧相互重叠，不是独立样方；单次观测不能推断趋势或原因。",
    "坐标为画面平面，未做尺度标定；镜头运动未知时，位置与占比只描述画面。",
]


def delta_display(value, unit):
    if value is None:
        return "N/A"
    if unit == "fraction":
        return f"{value * 100:+.1f} 个百分点"
    return ("+" if value > 0 else "") + display({"value": value, "unit": unit})


def comparison(site, observed_on, current, settings):
    previous = ObservationReport.objects.filter(site=site, observed_on__lt=observed_on).order_by("-observed_on", "-created_at").first()
    if previous is None:
        return None
    before = previous.payload["facts"]
    reasons = []
    if before["settings"]["models"] != settings["models"]:
        reasons.append("model_changed")
    for kind in ("fish", "coral"):
        if kind in before["settings"]["analysis"] and kind in settings["analysis"] and before["settings"]["analysis"][kind] != settings["analysis"][kind]:
            reasons.append(f"{kind}_settings_changed")
    motions = set(before["settings"]["camera_motion"]) | set(settings["camera_motion"])
    if motions != {"fixed"}:
        reasons.append("camera_motion_not_fixed")
    rows = {}
    for key, item in current.items():
        if not key.startswith("site.") or key not in before["metrics"]:
            continue
        old = before["metrics"][key]
        delta = item["value"] - old["value"] if not reasons and item["unit"] != "text" and None not in (item["value"], old["value"]) else None
        rows[key] = {"label": item["label"], "unit": item["unit"], "previous": old["value"], "current": item["value"], "delta": delta}
    return {"previous_report_id": str(previous.pk), "previous_observed_on": previous.observed_on.isoformat(),
            "comparable": not reasons, "reasons": reasons, "rows": rows}


def build(site, observed_on, runs, environment):
    """`runs` are completed AnalysisRuns, at most one per kind per video, in request order.

    `site` may be None for an agent session on the monitoring wall that is not filed to a site yet;
    such facts have no comparison and are never saved as a report.
    """
    videos, by_task = [], {}
    for run in runs:
        if run.task_id not in by_task:
            by_task[run.task_id] = {"task": run.task, "runs": {}}
            videos.append(by_task[run.task_id])
        kind = run.model.kind
        if kind in by_task[run.task_id]["runs"]:
            raise ValueError("duplicate_run_kind_for_video")
        by_task[run.task_id]["runs"][kind] = run
    metrics = {"site.name": metric("观测站点", site.name if site else "未归档", "text"), "site.observed_on": metric("观测日期", observed_on.isoformat(), "text"),
               "site.depth": metric("站点水深", site.depth_m if site else None, "meters", reason="not_provided")}
    pools = {"fish": [], "coral": []}
    settings = {"models": {}, "analysis": {}, "camera_motion": []}
    video_facts = []
    for index, video in enumerate(videos, start=1):
        prefix = f"v{index}"
        any_run = next(iter(video["runs"].values()))
        summary = any_run.summary
        fps = summary.get("fps")
        metrics[f"{prefix}.label"] = metric("视频", f"视频 {index}", "text")
        metrics[f"{prefix}.duration"] = metric("视频时长", summary["frame_count"] / fps if fps and summary.get("frame_count") else None, "seconds",
                                               reason="unknown_frame_rate")
        entry = {"index": index, "label": f"视频 {index}", "task_id": video["task"].pk, "filename": video["task"].original_filename,
                 "width": summary.get("width"), "height": summary.get("height"), "fps": fps, "runs": {}}
        for kind, run in sorted(video["runs"].items()):
            built = fish_metrics(prefix, run) if kind == "fish" else coral_metrics(prefix, run)
            metrics.update(built)
            pools[kind].append((prefix, built))
            config = run.config_snapshot["settings"]
            settings["models"].setdefault(kind, set()).add(run.model_id)
            settings["analysis"].setdefault(kind, set()).add(tuple(sorted((k, str(v)) for k, v in config.items() if k != "camera_motion")))
            settings["camera_motion"].append(config["camera_motion"])
            entry["runs"][kind] = {"run_id": str(run.pk), "model_id": run.model_id, "model_sha256": run.config_snapshot["model_sha256"],
                                   "camera_motion": config["camera_motion"], "settings": config}
        video_facts.append(entry)
    for kind in ("fish", "coral"):
        if pools[kind]:
            metrics.update(pooled(kind, pools[kind]))
    settings = {"models": {k: sorted(v) for k, v in settings["models"].items()},
                "analysis": {k: sorted("&".join(f"{a}={b}" for a, b in item) for item in v) for k, v in settings["analysis"].items()},
                "camera_motion": sorted(set(settings["camera_motion"]))}
    metrics.update(environment_metrics(environment))
    for item in metrics.values():
        item["display"] = display(item)
        item["reason_text"] = REASONS.get(item["reason"], item["reason"])
    compared = comparison(site, observed_on, metrics, settings) if site else None
    for key, row in (compared or {"rows": {}})["rows"].items():
        metrics[f"prev.{key}"] = metric(f"上次观测 · {row['label']}", row["previous"], row["unit"], reason="not_recorded") | \
            {"display": display({"value": row["previous"], "unit": row["unit"]}), "reason_text": None}
        if compared["comparable"]:
            metrics[f"delta.{key}"] = metric(f"变化 · {row['label']}", row["delta"], f"delta_{row['unit']}", reason="not_computable") | \
                {"display": delta_display(row["delta"], row["unit"]), "reason_text": None}
    limitations = list(GENERAL_LIMITATIONS)
    if pools["coral"]:
        limitations += [item for item in coral_query.LIMITATIONS if item not in limitations]
    model_ids = sorted({run.model_id for run in runs})
    evaluated = set(EvaluationRun.objects.filter(model_id__in=model_ids).values_list("model_id", flat=True))
    return {
        "schema": SCHEMA, "site": {"id": str(site.pk), "name": site.name, "depth_m": site.depth_m} if site else None,
        "observed_on": observed_on.isoformat(), "videos": video_facts, "settings": settings, "environment": environment,
        "metrics": metrics, "comparison": compared, "limitations": limitations,
        "model_quality": [{"model_id": model_id, "independent_evaluation": model_id in evaluated} for model_id in model_ids],
    }
