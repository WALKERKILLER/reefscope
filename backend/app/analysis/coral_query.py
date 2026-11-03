"""Coral frame index, masks and window statistics; reads published artifacts only, no model imports."""
import json
import math

from .storage import artifact

LIMITATIONS = [
    "只有背景、未白化、白化三类，尚无经评审的六类健康映射。",
    "未分离背景的采样帧把背景计入未白化，这些帧不进入珊瑚像素占比。",
    "白化预测没有本地真值验证。",
    "采样帧来自同一段视频，相互重叠，不是独立样方。",
    "像素占比基于画面平面，不等于底栖覆盖率。",
    "比例按采样帧像素合并计算，不是逐帧比例的平均。",
]


def frames(run):
    with artifact(run, "frames.jsonl").open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def mask(run, frame):
    record = next((item for item in frames(run) if item["frame"] == frame), None)
    if record is None:
        raise LookupError("unknown_frame")
    return artifact(run, record["mask"]), record


def window(query):
    if set(query) - {"start_ms", "end_ms", "export"}:
        raise ValueError("unknown_parameter")
    try:
        start = float(query.get("start_ms", 0))
        end = float(query["end_ms"]) if "end_ms" in query else None
    except ValueError as exc:
        raise ValueError("invalid_query") from exc
    if not math.isfinite(start) or start < 0 or (end is not None and (not math.isfinite(end) or end <= start)):
        raise ValueError("invalid_time_window")
    return {"start_ms": start, "end_ms": end}


def metric(value, unit, denominator, reason=None):
    return {"value": value, "unit": unit, "denominator": denominator, "status": "available" if value is not None else "unavailable",
            "metric_source": "coral_masks/v1", "reason": reason}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize(run, options):
    rows = [row for row in frames(run) if row["timestamp_ms"] >= options["start_ms"] and (options["end_ms"] is None or row["timestamp_ms"] < options["end_ms"])]
    separated = [row for row in rows if row["background_separated"]]
    count = lambda items, key: sum(row["pixel_counts"][key] for row in items)
    area = lambda items: sum(row["width"] * row["height"] for row in items)
    coral = count(separated, "1") + count(separated, "2")
    if not rows:
        shares_reason = "no_sampled_frames"
    elif not separated:
        shares_reason = "no_background_separated_frames"
    else:
        shares_reason = None
    series = [{"frame": row["frame"], "timestamp_ms": row["timestamp_ms"], "background_separated": row["background_separated"],
               "bleached_share": row["pixel_counts"]["2"] / (row["width"] * row["height"]),
               "coral_share": (row["pixel_counts"]["1"] + row["pixel_counts"]["2"]) / (row["width"] * row["height"]) if row["background_separated"] else None,
               "bleached_coral_fraction": ratio(row["pixel_counts"]["2"], row["pixel_counts"]["1"] + row["pixel_counts"]["2"]) if row["background_separated"] else None}
              for row in rows]
    config = run.config_snapshot["settings"]
    return {"schema": "coral-window-summary/v1", "analysis_run_id": str(run.pk), "model_id": run.model_id,
            "model_sha256": run.config_snapshot["model_sha256"], "query": options, "camera_motion": config["camera_motion"],
            "sample_every_seconds": config["sample_every_seconds"],
            "metrics": {
                "sampled_frames": metric(len(rows), "frames", "sampled frames in the window"),
                "background_separated_frames": metric(len(separated), "frames", "sampled frames whose guard separated background"),
                "bleached_pixel_share": metric(ratio(count(rows, "2"), area(rows)), "fraction", "all pixels of sampled frames", None if rows else "no_sampled_frames"),
                "coral_pixel_share": metric(ratio(coral, area(separated)), "fraction", "all pixels of background-separated frames", shares_reason),
                "bleached_coral_fraction": metric(ratio(count(separated, "2"), coral), "fraction", "coral pixels of background-separated frames",
                                                  shares_reason or (None if coral else "no_coral_pixels")),
                "coral_cover": metric(None, "fraction", None, "requires_approved_benthic_roi"),
                "bleaching_accuracy": metric(None, "fraction", None, "no_local_bleached_ground_truth")},
            "series": series,
            "limitations": LIMITATIONS}
