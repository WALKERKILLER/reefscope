"""Midpoint integration of observed image-plane track segments.

Contract: docs/mvp/08-video-heatmap-and-datamining.md. No playback state
participates in this calculation; display normalization never changes raw mass.
"""
import math

ALGORITHM_VERSION = "midpoint-track-seconds/v1"
LIMITATION = "画面相对占据度，非海底地理坐标；轨迹 ID 不是去重生物个体。"


def inside_roi(x, y, roi):
    if roi is None:
        return True
    inside = False
    for (ax, ay), (bx, by) in zip(roi, roi[1:] + roi[:1]):
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross) < 1e-12 and min(ax,bx) <= x <= max(ax,bx) and min(ay,by) <= y <= max(ay,by):
            return True
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def integrate(records, *, start_ms=0, end_ms=None, width=64, height=36, allowed_gap_seconds=0.5,
              steps=16, track_id=None, class_id=None, roi=None, camera_motion="unknown"):
    if type(width) is not int or type(height) is not int or not 1 <= width <= 256 or not 1 <= height <= 144:
        raise ValueError("invalid_grid")
    if type(steps) is not int or not 1 <= steps <= 128:
        raise ValueError("invalid_steps")
    for value in (start_ms, allowed_gap_seconds):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid_time_window")
    if allowed_gap_seconds <= 0 or allowed_gap_seconds > 10:
        raise ValueError("invalid_gap")
    if end_ms is not None and (type(end_ms) not in (int,float) or not math.isfinite(end_ms) or end_ms <= start_ms):
        raise ValueError("invalid_time_window")
    if roi is not None and (not isinstance(roi, list) or not 3 <= len(roi) <= 64 or any(
        not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p) for p in roi)):
        raise ValueError("invalid_roi")
    raw = [[0.0] * width for _ in range(height)]
    last = {}
    minimum, maximum = None, None
    for point in records:
        if point.get("observed") is not True:
            continue
        identity, timestamp, frame = point.get("track_id"), point.get("timestamp_ms"), point.get("frame")
        center = point.get("center_xyn")
        if type(identity) is not int or identity < 0 or type(frame) is not int or frame < 0 or type(timestamp) not in (int,float) or not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("invalid_track_record")
        if not isinstance(center, list) or len(center) != 2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in center):
            raise ValueError("invalid_track_coordinate")
        previous = last.get(identity)
        if previous and frame == previous["frame"] and timestamp == previous["timestamp_ms"]:
            if center != previous["center_xyn"]:
                raise ValueError("conflicting_duplicate")
            continue
        if previous and (timestamp <= previous["timestamp_ms"] or frame <= previous["frame"]):
            raise ValueError("nonmonotonic_track")
        last[identity] = point
        if (track_id is not None and identity != track_id) or (class_id is not None and point.get("class_id") != class_id):
            last.pop(identity, None)
            continue
        minimum = timestamp if minimum is None else min(minimum, timestamp)
        maximum = timestamp if maximum is None else max(maximum, timestamp)
        if previous is None:
            continue
        delta = (timestamp-previous["timestamp_ms"])/1000
        if delta > allowed_gap_seconds:
            continue
        left, right = max(start_ms, previous["timestamp_ms"]), timestamp if end_ms is None else min(end_ms, timestamp)
        if right <= left:
            continue
        px, py = previous["center_xyn"]
        for sample in range(steps):
            moment = left + (sample+0.5)*(right-left)/steps
            fraction = (moment-previous["timestamp_ms"])/(timestamp-previous["timestamp_ms"])
            x, y = px+(center[0]-px)*fraction, py+(center[1]-py)*fraction
            if inside_roi(x,y,roi):
                raw[min(height-1,int(y*height))][min(width-1,int(x*width))] += (right-left)/(1000*steps)
    peak = max((max(row) for row in raw), default=0)
    return {"schema":"fish-heatmap/v1", "algorithm_version":ALGORITHM_VERSION, "coordinate_space":"image_plane",
            "camera_motion":camera_motion, "width":width, "height":height, "values_raw":raw,
            "values_display":[[v/peak if peak else 0 for v in row] for row in raw],
            "value_unit":"track_seconds", "weighting":"dwell_seconds", "normalization":"max",
            "track_seconds_total":math.fsum(math.fsum(row) for row in raw),
            "sampled_duration_seconds":0 if minimum is None else max(0, (min(maximum,end_ms) if end_ms is not None else maximum)-max(minimum,start_ms))/1000,
            "start_ms":start_ms, "end_ms":end_ms, "track_filter":track_id if track_id is not None else "all",
            "class_id":class_id, "roi":roi, "integration_steps":steps, "allowed_gap_seconds":allowed_gap_seconds,
            "interpretation":LIMITATION}
