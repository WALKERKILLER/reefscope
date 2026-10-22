"""Sequential Ultralytics ByteTrack adapter.

Tracking API: https://docs.ultralytics.com/modes/track/#persisting-tracks-loop
Only consecutive frames share tracker state; a new Run resets all trackers.
"""
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from time import monotonic

from .storage import file_hash, input_video, write_json


@lru_cache(maxsize=1)
def load_model(path, digest, device):
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    from ultralytics import YOLO
    return YOLO(path).to(device)


def reset_trackers(model):
    for tracker in getattr(getattr(model, "predictor", None), "trackers", []):
        tracker.reset()


def analyze(run, output, progress):
    import cv2
    import torch
    import ultralytics

    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    weight = Path(run.model.weight_path)
    if not weight.is_file() or file_hash(weight) != run.config_snapshot["model_sha256"]:
        raise ValueError("model_hash_mismatch")
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model = load_model(str(weight), run.model.sha256, device)
    reset_trackers(model)
    config = run.config_snapshot["settings"]
    source = input_video(run.task)
    source_hash = file_hash(source)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError("video_decode_failed")
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        cap.release()
        raise ValueError("invalid_video_dimensions")
    previous_ms = -1
    frame_index, observations, fallbacks = 0, 0, 0
    started = monotonic()
    track_ids = set()
    cuts = set(config["scene_cut_frames"])
    segment_id, id_offset, max_id = 0, 0, 0
    try:
        with (output / "tracks.jsonl").open("w", encoding="utf-8") as stream, torch.inference_mode():
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
                if not math.isfinite(timestamp) or timestamp < 0 or (frame_index and timestamp <= previous_ms):
                    if timestamp > 0 and timestamp < previous_ms:
                        raise ValueError("video_time_reversed")
                    if not math.isfinite(fps) or fps <= 0:
                        raise ValueError("video_time_unavailable")
                    timestamp = frame_index * 1000 / fps
                    fallbacks += 1
                if timestamp <= previous_ms:
                    raise ValueError("video_time_invalid")
                previous_ms = timestamp
                if frame_index in cuts:
                    reset_trackers(model)
                    segment_id += 1
                    id_offset = max_id
                result = model.track(frame, persist=True, tracker="bytetrack.yaml", device=device,
                                     half=device.startswith("cuda"), imgsz=config["imgsz"],
                                     conf=config["confidence_threshold"], iou=config["iou_threshold"], verbose=False)[0]
                boxes = result.boxes
                if boxes is not None and boxes.id is not None:
                    # Transfer the batch once, rather than synchronizing CUDA per scalar.
                    coordinates = boxes.xyxy.cpu().tolist()
                    ids, classes, scores = boxes.id.int().cpu().tolist(), boxes.cls.int().cpu().tolist(), boxes.conf.cpu().tolist()
                    for xyxy, track_id, cls, score in zip(coordinates, ids, classes, scores):
                        x1, y1, x2, y2 = xyxy
                        if not all(math.isfinite(v) for v in (*xyxy, score)) or not (0 <= x1 <= x2 <= width and 0 <= y1 <= y2 <= height):
                            raise ValueError("invalid_model_output")
                        source_id = track_id
                        track_id += id_offset
                        max_id = max(max_id, track_id)
                        record = {"schema": "fish-tracks/v1", "run_id": str(run.pk), "track_id": track_id,
                                  "tracker_track_id": source_id, "segment_id": segment_id,
                                  "frame": frame_index, "timestamp_ms": timestamp, "class_id": cls,
                                  "label": str(model.names[cls]), "confidence": score,
                                  "bbox_xywhn": [x1 / width, y1 / height, (x2-x1) / width, (y2-y1) / height],
                                  "center_xyn": [(x1+x2) / (2*width), (y1+y2) / (2*height)], "observed": True}
                        stream.write(json.dumps(record, allow_nan=False) + "\n")
                        observations += 1
                        track_ids.add(track_id)
                frame_index += 1
                if frame_index % 10 == 0:
                    progress(min(95, frame_index * 95 / max(1, total)))
        if not frame_index or (total > 0 and frame_index < total):
            raise ValueError("video_incomplete")
        if file_hash(source) != source_hash:
            raise ValueError("input_changed")
        elapsed = monotonic() - started
        summary = {"schema": "fish-summary/v1", "frame_count": frame_index, "width": width, "height": height,
                   "fps": fps if math.isfinite(fps) and fps > 0 else None,
                   "observations": observations, "track_count": len(track_ids), "timestamp_fallback_frames": fallbacks,
                   "device": device, "elapsed_seconds": elapsed, "processed_fps": frame_index / elapsed,
                   "camera_motion": config["camera_motion"], "model_id": run.model_id,
                   "limitations": ["Track IDs are not unique biological individuals", "Image-plane coordinates only", "No independent ground truth evaluation", "Undeclared scene cuts are not automatically detected"]}
        write_json(output / "summary.json", summary)
        write_json(output / "manifest.json", {"schema": "analysis-run/v1", "run_id": str(run.id), "attempt": run.attempt,
                   "model_id": run.model_id, "model_sha256": run.model.sha256, "input_sha256": source_hash, "config_snapshot": run.config_snapshot,
                   "framework_version": ultralytics.__version__, "artifacts": {name: file_hash(output / name) for name in ("tracks.jsonl", "summary.json")}})
        return summary
    finally:
        cap.release()
        reset_trackers(model)
