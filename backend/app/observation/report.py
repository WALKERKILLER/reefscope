"""Deterministic observation report; the optional agent narrative is a separate, audited section."""
from app.analysis.reports import render_html, render_markdown
from .facts import REASONS
from .sources import SOURCES

TEMPLATE_VERSION = "reefscope-observation-report/v1"
MOTION = {"fixed": "固定机位", "moving": "移动", "unknown": "未知"}
ROLES = {"observations": "观察", "interpretation": "解释", "limitations": "限制", "next_steps": "建议"}


def rows(metrics, keys):
    return [[metrics[key]["label"], metrics[key]["display"] if metrics[key]["value"] is not None else f"N/A（{metrics[key]['reason_text']}）"]
            for key in keys if key in metrics]


def per_video(facts, kind, names):
    result = []
    for video in facts["videos"]:
        if kind in video["runs"]:
            for name in names:
                item = facts["metrics"].get(f"v{video['index']}.{kind}.{name}")
                if item and item["value"] is not None:
                    result.append([f"{video['label']} · {item['label']}", item["display"]])
    return result


def text(parts):
    return "".join(part["text"] + ("（未核对）" if part.get("unverified") else "") for part in parts)


def sections(facts, agent):
    m = facts["metrics"]
    kinds = {kind for video in facts["videos"] for kind in video["runs"]}
    # Pooled site rows only add information when several videos contribute.
    pooled = lambda kind, keys: rows(m, keys) if sum(kind in video["runs"] for video in facts["videos"]) > 1 else []
    overview = rows(m, ["site.name", "site.observed_on", "site.depth"])
    for video in facts["videos"]:
        names = {"fish": "鱼类", "coral": "珊瑚"}
        duration = m[f"v{video['index']}.duration"]["display"]
        motion = "、".join(sorted({MOTION.get(run["camera_motion"], run["camera_motion"]) for run in video["runs"].values()}))
        overview.append([video["label"], f"时长 {duration} · {video['width']}×{video['height']} · 分析：{'、'.join(names[k] for k in sorted(video['runs']))} · 镜头：{motion}"])
    for model in facts["model_quality"]:
        overview.append([f"模型 {model['model_id']}", "已有独立评估" if model["independent_evaluation"] else "没有独立评估"])
    result = [{"key": "overview", "title": "观测概况", "rows": overview, "evidence": None, "paragraphs": [
        "本报告由平台根据所选视频的分析结果生成，全部数值来自确定性计算。AI 解读（如有）只解释这些数值，需要人工审阅。"]}]
    if "fish" in kinds:
        result.append({"key": "fish", "title": "鱼类活动", "evidence": None,
                       "rows": pooled("fish", ["site.fish.mean_count", "site.fish.peak_count", "site.fish.occupied_fraction"]) +
                       per_video(facts, "fish", ["mean_count", "peak_count", "peak_time", "occupied_fraction", "track_count", "track_seconds",
                                                 "median_track_duration", "tracks_over_5s", "mean_confidence"]),
                       "paragraphs": ["平均可见鱼数（MeanCount）= 追踪框总数 ÷ 处理帧数。每一帧都参与计算，没有鱼的帧计为 0。MeanCount 与真实丰度近似线性，单帧峰值（类似 MaxN）在鱼多时偏低 [SCHOBERND-2014]。",
                                      "两者都是相对丰度指标，不是个体数量或密度。追踪 ID 会因遮挡和断轨重复，ID 数不等于鱼的个体数。"]})
    if "coral" in kinds:
        result.append({"key": "coral", "title": "珊瑚画面", "evidence": None,
                       "rows": pooled("coral", ["site.coral.coral_pixel_share", "site.coral.bleached_coral_fraction"]) +
                       per_video(facts, "coral", ["sampled_frames", "separated_frames", "coral_pixel_share", "coral_share_min", "coral_share_max",
                                                  "bleached_coral_fraction", "bleached_frames"]),
                       "paragraphs": ["珊瑚像素占比按背景已分离的采样帧合并计算，是画面平面统计，不等于活珊瑚覆盖率 [GCRMN-2020]。",
                                      "白化比例的分母是珊瑚像素。现场调查中的白化发生率按群体计算，严重度按受影响表面计算，两者都不能用像素比例代替 [AGRRA-2023]。"]})
    if facts["environment"]:
        env = facts["environment"]
        source = "、".join(item for item in (env["source"], env["product_date"] and f"产品日期 {env['product_date']}") if item)
        result.append({"key": "environment", "title": "环境背景", "evidence": None,
                       "rows": rows(m, ["env.sst", "env.in_situ_temp", "env.hotspot", "env.dhw", "env.baa_level", "env.baa_impact"]),
                       "paragraphs": [f"环境数据由用户录入{f'（{source}）' if source else ''}，平台未核对来源。",
                                      "DHW 为 84 天内 HotSpot ≥ 1 °C 的累积热胁迫；警报等级按 NOAA Coral Reef Watch v3.1 的 HotSpot 与 DHW 共同判定 [CRW-BAA]。卫星产品描述约 5 km 网格的海表状况，只作背景。"]})
    else:
        result.append({"key": "environment", "title": "环境背景", "evidence": None, "rows": [],
                       "paragraphs": ["未录入环境数据。CRW 白化警报等级需要 HotSpot；HotSpot ≥ 1 °C 时还需要 DHW [CRW-BAA]。"]})
    compared = facts["comparison"]
    if compared:
        lines = [[row["label"], f"上次 {m[f'prev.{key}']['display']} → 本次 {m[key]['display']}" +
                  (f"（{m[f'delta.{key}']['display']}）" if f"delta.{key}" in m else "")] for key, row in compared["rows"].items()]
        why = "、".join(REASONS.get(r, r) for r in compared["reasons"])
        result.append({"key": "comparison", "title": "与上次观测比较", "rows": lines, "evidence": None, "paragraphs": [
            f"上次观测日期 {compared['previous_observed_on']}。" + ("两次的模型、参数与机位一致，列出变化量。" if compared["comparable"] else
                                                               f"两次观测不可比（{why}），只并列数值，不计算变化。")]})
    result.append(agent_section(agent))
    # Videos share the same unavailable metrics; list each label and reason once.
    missing = {(item["label"], item["reason_text"]) for key, item in m.items() if item["value"] is None and not key.startswith(("prev.", "delta."))}
    result.append({"key": "missing", "title": "缺失指标与局限", "rows": [list(row) for row in sorted(missing)], "evidence": None, "paragraphs": facts["limitations"]})
    result.append({"key": "references", "title": "参考资料", "evidence": None, "paragraphs": [],
                   "rows": [[f"[{item['id']}] {item['authors']} ({item['year']})", f"{item['title']} {item['url']}"] for item in references(facts, agent)]})
    return result


def references(facts, agent):
    cited = {item["source"] for item in facts["metrics"].values() if item.get("source")} | set((agent.get("audit") or {}).get("citations", [])) | {"CRW-BAA"}
    return [{"id": key, **{name: SOURCES[key][name] for name in ("authors", "year", "title", "url")}} for key in sorted(cited) if key in SOURCES]


def agent_section(agent):
    if agent["status"] == "disabled":
        return {"key": "agent", "title": "AI 解读", "rows": [], "evidence": None, "paragraphs": ["本次未使用 AI 解读。"]}
    meta = [["接口格式", agent["api_format"]], ["模型", agent["model"]], ["服务地址", agent["host"]], ["提示词版本", agent["prompt_version"]]]
    if agent["status"] != "generated":
        return {"key": "agent", "title": "AI 解读", "rows": meta, "evidence": None,
                "paragraphs": [f"AI 解读未生成：{agent.get('error_text') or agent['error_code']}上文的确定性结果不受影响。"]}
    narrative, audit = agent["narrative"], agent["audit"]
    paragraphs = ["以下内容由语言模型撰写，待人工审阅。数值由平台按指标 ID 填入；标注“未核对”的数字是模型自行写出的，没有经过核对。", text(narrative["summary"])]
    for name, role in ROLES.items():
        paragraphs.extend(f"{role}：{text(entry)}" for entry in narrative[name])
    if audit["unknown_metrics"] or audit["unknown_citations"]:
        paragraphs.append(f"模型引用了不存在的指标或资料，已移除：{', '.join(audit['unknown_metrics'] + audit['unknown_citations'])}。")
    return {"key": "agent", "title": "AI 解读", "rows": meta, "evidence": None, "paragraphs": paragraphs}


def make(facts, agent):
    title = f"观测报告 · {facts['site']['name']} · {facts['observed_on']}"
    body = sections(facts, agent)
    payload = {"schema": "observation-report/v1", "template_version": TEMPLATE_VERSION, "title": title, "facts": facts, "agent": agent,
               "sections": body, "references": references(facts, agent), "human_review_status": "pending"}
    return payload, render_markdown(body, title), render_html(body, title)
