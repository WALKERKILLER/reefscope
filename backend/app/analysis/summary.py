"""Window statistics share the heatmap's scientific filtering contract."""
import math

from .heatmap import integrate, inside_roi
from .query import records


def metric(value, unit, denominator, reason=None):
    return {"value":value, "unit":unit, "denominator":denominator, "status":"available" if value is not None else "unavailable",
            "metric_source":"observed_fish_tracks/v1", "reason":reason}


def summarize(run, options):
    config = run.config_snapshot["settings"]
    heat = integrate(records(run), **options, allowed_gap_seconds=config["allowed_gap_seconds"], camera_motion=config["camera_motion"])
    identities, labels = set(), {}
    # A frame-local set removes duplicate observations without retaining all frames.
    previous_frame, frame_ids = None, set()
    confidence_total, observation_count = 0.0, 0
    for point in records(run):
        if point.get("observed") is not True:
            continue
        timestamp = point["timestamp_ms"]
        if timestamp < options["start_ms"] or (options["end_ms"] is not None and timestamp >= options["end_ms"]):
            continue
        if any(options[key] is not None and options[key] != point[key] for key in ("track_id","class_id")):
            continue
        if not inside_roi(*point["center_xyn"],options["roi"]):
            continue
        if previous_frame != point["frame"]:
            previous_frame, frame_ids = point["frame"], set()
        if point["track_id"] in frame_ids:
            continue
        frame_ids.add(point["track_id"])
        score = point.get("confidence")
        if type(score) not in (int,float) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("invalid_confidence")
        observation_count += 1
        confidence_total += score
        identities.add(point["track_id"])
        label = str(point["class_id"])
        labels[label] = labels.get(label,0)+1
    return {"schema":"fish-window-summary/v1", "analysis_run_id":str(run.pk), "model_id":run.model_id,
            "model_sha256":run.config_snapshot["model_sha256"], "query":options, "camera_motion":config["camera_motion"],
            "metrics":{
                "observed_track_count":metric(len(identities),"track_ids","distinct IDs with real observations in the window"),
                "tracked_observation_count":metric(observation_count,"observations","deduplicated tracked boxes in the window"),
                "track_seconds":metric(heat["track_seconds_total"],"track_seconds","valid clipped segments after gap and ROI filtering"),
                "mean_confidence":metric(confidence_total/observation_count if observation_count else None,"fraction",observation_count,None if observation_count else "no_observations"),
                "ap50":metric(None,"fraction",None,"missing_independent_ground_truth"),
                "idf1":metric(None,"fraction",None,"missing_manual_identity_ground_truth"),
                "coral_cover":metric(None,"fraction",None,"no_coral_model_or_benthic_roi")},
            "class_observation_counts":labels,
            "heatmap":{key:value for key,value in heat.items() if key not in ("values_raw","values_display")},
            "limitations":[heat["interpretation"],"观测 ID 数仅统计窗口内真实观测，裁剪积分可包含窗外支撑点。", "置信度不代表独立测试精度。", "无 ID 的检测不计入追踪观测。"]}
