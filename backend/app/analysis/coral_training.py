"""Coral training-log ingest: whitelisted numbers, enumerations and hashes only.

The delivered log package keeps historical run directories in raw/ files; none of those
strings are copied. Epoch rows are recomputed from raw/training/history.json, not from the
package's derived table, and every file read must match CHECKSUMS.sha256.json.
"""
import json
import re
from pathlib import Path

from app.analysis.training import bounded_text, finite_number

FILES = {
    "history": "raw/training/history.json",
    "best": "raw/training/best_validation_v2.json",
    "provenance": "raw/training/training_provenance_v2.json",
    "guard": "raw/calibration/guard-validation-v2.json",
    "assessment": "raw/evaluation/v2-assessment.json",
    "test": "raw/evaluation/v2-test-report.json",
    "train_audit": "raw/evaluation/v2-official-train-audit.json",
    "export": "raw/export/export-verification.json",
    "equivalence": "raw/export/single-file-equivalence.json",
    "local_data": "raw/data/local-data-audit.json",
    "official_data": "raw/data/official-data-provenance.json",
    "verification": "VERIFICATION.json",
}
SHA = re.compile(r"[0-9a-f]{64}")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
VERSION = re.compile(r"[0-9][0-9A-Za-z.+-]{0,31}")
SCORES = ("iou", "f1", "precision", "recall")
GUARD = ("threshold", "official_train_max_score", "official_max_validation_score", "fixed_safety_margin")
GUARD_COUNTS = ("official_training_images", "official_training_active", "official_validation_images", "official_validation_active", "local_validation_images", "local_validation_active")


def sha(value, name):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError(f"invalid_digest:{name}")
    return value


def count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"invalid_count:{name}")
    return value


def flag(value, name):
    if type(value) is not bool:
        raise ValueError(f"invalid_flag:{name}")
    return value


def score(source, name):
    """IoU/F1/P/R as fractions; None stays None where the class has no support."""
    return {key: None if source.get(key) is None else finite_number(source[key], f"{name}.{key}", True) for key in SCORES}


def signed(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"invalid_numeric_field:{name}")
    return float(value)


def read_package(root):
    root = Path(root).resolve()
    text, digest = bounded_text(root / "CHECKSUMS.sha256.json", 1_000_000)
    checksums = json.loads(text)
    if not isinstance(checksums, dict):
        raise ValueError("invalid_checksums")
    data, hashes = {}, {"CHECKSUMS.sha256.json": digest}
    for key, relative in FILES.items():
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("source_outside_package")
        text, digest = bounded_text(path)
        if checksums.get(relative) != digest:
            raise ValueError("checksum_mismatch")
        data[key], hashes[relative] = json.loads(text), digest
    return data, hashes


def epoch_rows(history):
    if not isinstance(history, list) or not 1 <= len(history) <= 1000:
        raise ValueError("invalid_training_history")
    rows, best = [], None
    for index, record in enumerate(history, 1):
        if record.get("epoch") != index:
            raise ValueError("epochs_not_strictly_increasing")
        candidates = record["validation"]["candidates"]
        sweep = [(finite_number(c["threshold"], "threshold", True), score(c["non_bleached"], "validation")) for c in candidates]
        if not sweep or len({t for t, _ in sweep}) != len(sweep) or any(s["iou"] is None for _, s in sweep):
            raise ValueError("invalid_threshold_sweep")
        threshold, chosen = max(sweep, key=lambda item: item[1]["iou"])
        fixed = next((s for t, s in sweep if t == 0.5), None)
        improved = best is None or chosen["iou"] > best
        best = max(best or 0, chosen["iou"])
        rows.append({"epoch": index, "train/loss": finite_number(record["loss"], "loss"),
                     "val/iou": chosen["iou"], "val/f1": chosen["f1"], "val/precision": chosen["precision"], "val/recall": chosen["recall"],
                     "val/threshold": threshold, "val/iou@0.5": fixed["iou"] if fixed else None,
                     "time": finite_number(record["elapsed_seconds"], "elapsed_seconds"), "new_best": improved})
    return rows, [t for t, _ in sweep]


def domain_metrics(domain, name):
    full = domain["metrics"]["full_image"]
    return {"images": count(domain["images"], f"{name}.images"), "guard_active_images": count(domain["guard_active_images"], f"{name}.guard"),
            "changed_pixels": count(domain["changed_pixels"], f"{name}.changed"), "bleached_changed_pixels": count(domain["bleached_changed_pixels"], f"{name}.bleached_changed"),
            "full_image": {model: {cls: {**score(full[model][cls], f"{name}.{model}.{cls}"), "support_pixels": count(full[model][cls]["support_pixels"], f"{name}.support")}
                                   for cls in ("1", "2")} for model in ("baseline", "adapted")}}


def ingest(directory, model):
    data, hashes = read_package(directory)
    provenance, best, guard, export, test = data["provenance"], data["best"], data["guard"], data["export"], data["test"]
    args = provenance["args"]
    arguments = {key: count(args[key], key) for key in ("epochs", "steps", "batch", "crop", "seed")}
    arguments["lr"] = finite_number(args["lr"], "lr")
    rows, thresholds = epoch_rows(data["history"])
    arguments["threshold_candidates"] = thresholds
    if len(rows) != arguments["epochs"]:
        raise ValueError("epoch_count_mismatch")

    adapter = sha(guard["checkpoint_sha256"], "adapter")
    if sha(export["sha256"], "weight") != model.sha256 or sha(data["equivalence"]["sha256"], "equivalence") != model.sha256:
        raise ValueError("training_weight_mismatch")
    if {sha(export["source_adapter_sha256"], "export_adapter"), sha(test["checkpoint_sha256"], "test"), sha(data["train_audit"]["checkpoint_sha256"], "audit"),
            sha(provenance["post_training_guard_calibration"]["checkpoint_sha256"], "provenance")} != {adapter}:
        raise ValueError("adapter_lineage_mismatch")
    selected = max(rows, key=lambda row: row["val/iou"])
    if best["epoch"] != selected["epoch"] or best["selected"]["threshold"] != selected["val/threshold"]:
        raise ValueError("selected_epoch_mismatch")
    training, inference = model.metadata.get("training", {}), model.metadata.get("inference", {})
    if (training.get("epoch", best["epoch"]) != best["epoch"] or training.get("seed", arguments["seed"]) != arguments["seed"]
            or inference.get("threshold", selected["val/threshold"]) != selected["val/threshold"] or inference.get("guard_threshold", guard["threshold"]) != guard["threshold"]):
        raise ValueError("training_metadata_mismatch")

    local, official = data["local_data"], data["official_data"]
    groups = {name: split for name, split in local["group_assignment"].items() if SLUG.fullmatch(name) and split in {"train", "val", "test"}}
    if len(groups) != len(local["group_assignment"]):
        raise ValueError("invalid_scene_groups")
    if not re.fullmatch(r"[0-9a-f]{40}", official.get("revision", "")) or not re.fullmatch(r"[A-Za-z0-9.-]{1,32}", official.get("license", "")):
        raise ValueError("invalid_official_provenance")
    assessment, verification, equivalence = data["assessment"], data["verification"], data["equivalence"]
    change = assessment["local_test_per_image_iou_change"]
    snapshot = {
        "schema": "coral-training-run/v1", "epochs": rows, "arguments": arguments,
        "selection": {"best_epoch": selected["epoch"], "best_threshold": selected["val/threshold"], "last_epoch": rows[-1]["epoch"],
                      "selection_basis": "local_validation_non_bleached_iou", "framework_best_checkpoint_epoch": count(best["epoch"], "best_epoch"),
                      "test_used_for_selection": flag(guard["test_used_for_calibration"], "test_used")},
        "data": {"local_split_frames": {k: count(local["split_frames"][k], k) for k in ("train", "val", "test")},
                 "local_split_groups": {k: count(local["split_groups"][k], k) for k in ("train", "val", "test")}, "scene_groups": groups,
                 "official_split_counts": {k: count(official["split_counts"][k], k) for k in ("train", "val", "test")},
                 "official_revision": official["revision"], "official_license": official["license"],
                 "official_replay_images": count(provenance["official_replay_images"], "replay"), "local_training_images": count(provenance["local_training_images"], "local_train"),
                 "local_validation_images": count(best["local_validation_images"], "local_val"), "official_validation_images": count(best["official_validation_images"], "official_val")},
        "validation": {"baseline": score(best["baseline"], "baseline"), "selected": score(best["selected"]["non_bleached"], "selected"),
                       "official_validation_unchanged": flag(best["official_validation_all_pixels_unchanged"], "official_val_unchanged"),
                       "groups": [{"group": g["group"], "baseline": score(g["baseline"], "group"), "adapted": score(g["adapted"], "group")}
                                  for g in best["selected"]["groups"] if SLUG.fullmatch(g["group"])]},
        "guard": {**{key: signed(guard[key], key) for key in GUARD}, **{key: count(guard[key], key) for key in GUARD_COUNTS},
                  "local_validation_score_range": [signed(v, "score_range") for v in guard["local_validation_score_range"][:2]],
                  "test_used_for_calibration": flag(guard["test_used_for_calibration"], "test_used"),
                  "segmentation_head_and_threshold_unchanged": flag(guard["segmentation_head_and_threshold_unchanged"], "head_unchanged")},
        "regression_recheck": {"domains": {name: domain_metrics(test["domains"][name], name) for name in ("local", "official")},
                               "local_per_image_iou_change": {k: count(change[k], k) for k in ("improved", "unchanged", "worse")},
                               "local_test_bleached_truth_pixels": count(assessment["local_test_bleached_truth_pixels"], "bleached_truth"),
                               "official_train_audit": {k: count(data["train_audit"][k], k) for k in ("images", "guard_active_images", "changed_pixels")},
                               "fresh_untouched_generalization_evidence": flag(assessment["fresh_untouched_generalization_evidence"], "fresh")},
        "export": {"bytes": count(export["bytes"], "bytes"), "tensor_count": count(export["tensor_count"], "tensors"), "base_tensors": count(export["base_tensors"], "base_tensors"),
                   "trained_head_tensors": count(export["trained_head_tensors"], "head_tensors"),
                   "all_tensor_values_equal": flag(export["all_tensor_values_equal_to_verified_v2"], "equal"), "requires_other_weight_files": flag(export["requires_other_weight_files"], "other_files"),
                   "images_compared": count(equivalence["actual_images_compared"], "compared"), "predictions_identical": flag(equivalence["all_predictions_pixel_identical_to_verified_v2"], "identical"),
                   "both_guard_branches_exercised": flag(equivalence["both_guard_branches_exercised"], "branches"), "cli_identical": flag(equivalence["cli_prediction_pixel_identical_to_verified_v2"], "cli"),
                   "runtime": {k: equivalence[k] for k in ("python", "torch", "transformers") if isinstance(equivalence.get(k), str) and VERSION.fullmatch(equivalence[k])}},
        "lineage": {"weight_sha256": model.sha256, "adapter_sha256": adapter, "source_adapter_sha256": sha(guard["source_checkpoint_sha256"], "source_adapter"),
                    "frozen_base_sha256": sha(provenance["base_sha256"], "base"), "base_unchanged": flag(provenance["base_unchanged"], "base_unchanged")},
        "elapsed_seconds": finite_number(provenance["elapsed_seconds"], "elapsed"),
    }
    missing = ["validation_loss", "per_step_training_loss", "training_dataset_hash", "fresh_untouched_test", "hardware_benchmark"]
    if not verification.get("raw_terminal_stdout_stderr_available"):
        missing.append("raw_terminal_logs")
    if snapshot["regression_recheck"]["local_test_bleached_truth_pixels"] == 0:
        missing.append("local_bleached_ground_truth")
    snapshot["missing_inputs"] = missing
    snapshot["warnings"] = ["验证集同时用于选择 epoch 与阈值，验证数值偏乐观，不是独立测试精度。",
                            "测试数值是 v2 对 v1 已查看测试图的回归复核，不是全新独立泛化测试。"]
    return snapshot, hashes
