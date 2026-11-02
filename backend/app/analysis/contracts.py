"""Validated fish Run settings; public APIs never accept model paths."""
import math

DEFAULTS = {
    "confidence_threshold": 0.25,
    "iou_threshold": 0.45,
    "tracking_frame_stride": 1,
    "imgsz": 640,
    "allowed_gap_seconds": 0.5,
    "camera_motion": "unknown",
    "scene_cut_frames": [],
}


def validate_settings(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValueError("invalid_settings")
    result = DEFAULTS | value
    for key in ("confidence_threshold", "iou_threshold", "allowed_gap_seconds"):
        number = result[key]
        upper = 10 if key == "allowed_gap_seconds" else 1
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 < number <= upper:
            raise ValueError("invalid_settings")
    if type(result["tracking_frame_stride"]) is not int or result["tracking_frame_stride"] != 1:
        raise ValueError("tracking_requires_consecutive_frames")
    if type(result["imgsz"]) is not int or not 160 <= result["imgsz"] <= 1280 or result["imgsz"] % 32:
        raise ValueError("invalid_imgsz")
    if result["camera_motion"] not in ("fixed", "moving", "unknown"):
        raise ValueError("invalid_camera_motion")
    cuts = result["scene_cut_frames"]
    if not isinstance(cuts, list) or len(cuts) > 10000 or any(type(v) is not int or v < 1 for v in cuts) or cuts != sorted(set(cuts)):
        raise ValueError("invalid_scene_cuts")
    return result
