"""Contract smoke tests for proposed MVP example payloads (stdlib-only)."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "fixtures" / "mvp"


def load(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def check() -> None:
    run = load("analysis-run.sample.json")
    heat = load("heatmap.sample.json")
    taxonomy = load("taxonomy-v1.json")
    tracks = [
        json.loads(line)
        for line in (FIX / "tracks.sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert run["schema_version"] == "analysis-run/v1"
    assert run["kind"] in {"fish_tracking", "coral_health", "joint"}
    assert run["status"] in {"queued", "running", "completed", "failed", "cancelled"}
    assert len(tracks) > 1
    assert run["run_id"] == heat["run_id"]
    assert all(t["run_id"] == run["run_id"] for t in tracks)
    assert all(isinstance(t["track_id"], int) and t["track_id"] >= 0 for t in tracks)
    assert run["summary"]["track_count"] == len({t["track_id"] for t in tracks})
    per_id = {}
    for t in tracks:
        x, y, w, h = t["bbox_xywhn"]
        cx, cy = t["center_xyn"]
        assert all(math.isfinite(v) for v in (x, y, w, h, cx, cy))
        assert 0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0
        assert x + w <= 1 and y + h <= 1
        assert abs((x + w / 2) - cx) < 0.00001
        assert abs((y + h / 2) - cy) < 0.00001
        assert 0 <= t["confidence"] <= 1
        assert t["observed"] is True
        prev = per_id.get(t["track_id"])
        if prev:
            assert prev[0] < t["frame"] and prev[1] < t["timestamp_ms"]
        per_id[t["track_id"]] = (t["frame"], t["timestamp_ms"])
    assert heat["schema_version"] == "fish-heatmap/v1"
    assert heat["coordinate_space"] == "image_plane"
    assert heat["weighting"] == "dwell_seconds"
    assert heat["coordinate_space"] == "image_plane"
    assert heat["value_unit"] == "track_seconds"
    for key in ["values_raw", "values_display"]:
        assert len(heat[key]) == heat["height"]
        assert all(len(row) == heat["width"] for row in heat[key])
        assert all(math.isfinite(v) and v >= 0 for row in heat[key] for v in row)
    assert all(v <= 1 for row in heat["values_display"] for v in row)
    assert abs(sum(map(sum,heat["values_raw"])) - heat["track_seconds_total"]) < 1e-6

    assert taxonomy["schema_version"] == "coral-health/v1"
    assert {x["id"] for x in taxonomy["classes"]} == {0, 1, 2, 3, 4, 5, 255}
    assert taxonomy["mapping_status"] == "unreviewed_requires_expert"
    assert not taxonomy["source_to_target_mapping"]
    assert taxonomy["source_model_num_logits"] == 96
    assert taxonomy["source_void_id"] == 0
    assert taxonomy["source_void_target_ignore_id"] == 255
    assert any(m["source_id"] == 0 and m["target_id"] == 255 for m in taxonomy["mapping_examples_unreviewed_not_production"])
    ds = load("coral-dataset-manifest.sample.json")
    exp = load("coral-experiment.sample.json")
    assert ds["split_unit"] == "site/dive/parent_video"
    assert exp["num_source_logits"] == 96 and exp["target_ignore_index"] == 255
    assert exp["measured_metrics"] is None and exp["status"] == "illustrative_not_executed"
    report = load("training-report.sample.json")
    annotation = load("auto-annotation.sample.json")
    wall = load("wall-view.sample.json")
    assert report["schema_version"] == "training-report/v1-proposal"
    assert report["status"] == "illustrative_not_executed"
    assert len(report["sections"]) == 7
    assert report["evaluation_run_id"] and report["evaluation_protocol_id"]
    assert report["ai_diagnostic_enabled"] is False
    assert report["best_checkpoint_selection_basis"] != "map50_is_always_best"
    for metric in report["metrics"].values():
        assert metric["value"] is None
        assert metric["metric_source"] in {"deterministic_evaluator", "hardware_benchmark"}
        assert metric["status"] in {"missing_gt", "not_measured"}
    assert annotation["schema_version"] == "annotation-provenance/v1-proposal"
    assert annotation["status"] == "illustrative_not_executed"
    assert annotation["approved_for_training"] is False
    assert annotation["approved_for_evaluation_gt"] is False
    assert annotation["annotation_labels"] == []
    assert annotation["target_annotation_type"] == "fish_detection_bbox"
    assert wall["schema_version"] == "ocean-wall/v1-proposal"
    assert wall["coordinate_space"] == "image_plane"
    assert wall["analysis_run_id"] == run["run_id"]
    assert wall["status"] == "illustrative_not_rendered"
    assert len(wall["metrics"]) >= 3
    for card in wall["metrics"]:
        assert card["value"] is None and card["status"] != "ok"
        assert card["reason"] and card["metric_source"]
    print("PASS: AnalysisRun, tracking, heatmap, taxonomy, training report, annotation provenance and wall fixtures")


if __name__ == "__main__":
    check()
