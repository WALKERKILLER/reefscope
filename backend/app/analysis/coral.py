"""Sampled-frame coral bleaching masks from a registered reef-coral-final/v1 checkpoint.

Inference runs the delivered loader in vendor/coral_model.py unchanged. Masks hold 0 background,
1 non-bleached and 2 bleached. The checkpoint's image guard decides per frame whether background is
separated; without it the frame has no class 0 and class 1 covers every pixel that is not bleached.
"""
import json
import math
from functools import lru_cache
from pathlib import Path
from time import monotonic

from .storage import file_hash, input_video, write_json
from .video import FrameClock, open_video

MAX_SAMPLES = 1800
LIMITATIONS = [
    "Three classes only: background, non-bleached and bleached; no reviewed six-class health mapping",
    "Frames without background separation count background as non-bleached",
    "Bleached predictions are not validated on local data",
    "Sampled video frames overlap and are not independent quadrats",
    "Image-plane pixel shares, not benthic cover",
]


@lru_cache(maxsize=1)
def load_model(path, digest, device):
    from .vendor.coral_model import CoralModel
    return CoralModel(path, device=device)


def runtime():
    """The delivery verified CUDA BF16; other devices run FP32 and the summary says so."""
    import torch
    if torch.cuda.is_available():
        with torch.cuda.device("cuda:0"):
            return "cuda:0", "bf16" if torch.cuda.is_bf16_supported() else "fp32"
    return "cpu", "fp32"


def analyze(run, output, progress):
    import cv2
    import numpy as np
    import torch
    import transformers
    from PIL import Image

    weight = Path(run.model.weight_path)
    if not weight.is_file() or file_hash(weight) != run.config_snapshot["model_sha256"]:
        raise ValueError("model_hash_mismatch")
    device, precision = runtime()
    model = load_model(str(weight), run.model.sha256, device)
    model.record["precision"] = precision
    config = run.config_snapshot["settings"]
    interval_ms = config["sample_every_seconds"] * 1000
    source = input_video(run.task)
    source_hash = file_hash(source)
    cap, fps, total, width, height = open_video(source)
    clock = FrameClock(fps)
    (output / "masks").mkdir(exist_ok=True)
    frame_index, samples, separated, next_ms = 0, 0, 0, 0
    pixels = [0, 0, 0]
    started = monotonic()
    try:
        with (output / "frames.jsonl").open("w", encoding="utf-8") as stream:
            # grab() advances without colour conversion; only sampled frames are retrieved.
            while cap.grab():
                timestamp = clock.stamp(frame_index, cap.get(cv2.CAP_PROP_POS_MSEC))
                if timestamp >= next_ms:
                    ok, frame = cap.retrieve()
                    if not ok:
                        raise ValueError("video_decode_failed")
                    samples += 1
                    if samples > MAX_SAMPLES:
                        raise ValueError("too_many_samples")
                    mask, baseline, detail = model.predict_with_details(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                    active = bool(detail["guard_active"])
                    counts = np.bincount(mask.ravel(), minlength=3).tolist() if mask.size else []
                    if (mask.dtype != np.uint8 or mask.shape != (height, width) or len(counts) != 3
                            or not np.array_equal(mask == 2, baseline == 2) or (not active and counts[0])):
                        raise ValueError("invalid_model_output")
                    name = f"masks/{frame_index:08d}.png"
                    Image.fromarray(mask).save(output / name)
                    record = {"schema": "coral-frames/v1", "run_id": str(run.pk), "frame": frame_index, "timestamp_ms": timestamp,
                              "width": width, "height": height, "background_separated": active,
                              "guard_score": float(detail["guard_score"]), "pixel_counts": {str(k): v for k, v in enumerate(counts)},
                              "mask": name, "mask_sha256": file_hash(output / name)}
                    stream.write(json.dumps(record, allow_nan=False) + "\n")
                    separated += active
                    pixels = [a + b for a, b in zip(pixels, counts)]
                    next_ms = (math.floor(timestamp / interval_ms) + 1) * interval_ms
                    progress(min(95, frame_index * 95 / max(1, total)))
                frame_index += 1
                if frame_index % 30 == 0:
                    progress(min(95, frame_index * 95 / max(1, total)))
        if not samples or (total > 0 and frame_index < total):
            raise ValueError("video_incomplete")
        if file_hash(source) != source_hash:
            raise ValueError("input_changed")
        elapsed = monotonic() - started
        summary = {"schema": "coral-summary/v1", "frame_count": frame_index, "width": width, "height": height,
                   "fps": fps if math.isfinite(fps) and fps > 0 else None, "sample_every_seconds": config["sample_every_seconds"],
                   "sampled_frames": samples, "background_separated_frames": separated,
                   "pixel_counts": {str(k): v for k, v in enumerate(pixels)}, "labels": run.model.labels,
                   "timestamp_fallback_frames": clock.fallbacks, "device": device, "precision": precision,
                   "elapsed_seconds": elapsed, "seconds_per_sample": elapsed / samples,
                   "framework": {"torch": torch.__version__, "transformers": transformers.__version__},
                   "camera_motion": config["camera_motion"], "model_id": run.model_id, "limitations": LIMITATIONS}
        write_json(output / "summary.json", summary)
        masks = sorted(path.relative_to(output).as_posix() for path in (output / "masks").glob("*.png"))
        write_json(output / "manifest.json", {"schema": "analysis-run/v1", "kind": "coral", "run_id": str(run.id), "attempt": run.attempt,
                   "model_id": run.model_id, "model_sha256": run.model.sha256, "input_sha256": source_hash,
                   "config_snapshot": run.config_snapshot, "framework_version": transformers.__version__,
                   "artifacts": {name: file_hash(output / name) for name in ("frames.jsonl", "summary.json", *masks)}})
        return summary
    finally:
        cap.release()
