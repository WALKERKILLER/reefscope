import hashlib
import io
import json
import tempfile
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase

from app.analysis.coral_reports import SECTION_NAMES, TEMPLATE_VERSION
from app.analysis.coral_training import ingest
from app.models import ModelVersion, TrainingReport

WEIGHT, ADAPTER, SOURCE, BASE = "a" * 64, "b" * 64, "c" * 64, "d" * 64
PRIVATE = "/PRIVATE-RUN/coral"


def scores(iou, precision=0.8, recall=0.8, support=100):
    return {"tp": 1, "fp": 1, "fn": 1, "support_pixels": support, "iou": iou, "precision": precision, "recall": recall, "f1": None if iou is None else 2 * iou / (1 + iou)}


def candidates(best_threshold, best_iou):
    return [{"threshold": t, "non_bleached": scores(best_iou if t == best_threshold else best_iou - 0.05),
             "groups": [{"group": "reef-a", "baseline": scores(0.1), "adapted": scores(0.4)}]} for t in (0.3, 0.4, 0.5)]


def domain(images, changed, base_iou, adapted_iou):
    full = {"baseline": {"0": scores(0.0), "1": scores(base_iou, 0.2, 0.9), "2": scores(None, 0.0, None, 0)},
            "adapted": {"0": scores(0.5), "1": scores(adapted_iou, 0.5, 0.7), "2": scores(None, 0.0, None, 0)}}
    return {"images": images, "guard_active_images": images // 2, "changed_pixels": changed, "bleached_changed_pixels": 0, "metrics": {"full_image": full}}


def build(root):
    guard = {"threshold": -0.01, "official_train_max_score": -0.02, "official_max_validation_score": -0.03, "fixed_safety_margin": 0.01,
             "official_training_images": 10, "official_training_active": 0, "official_validation_images": 4, "official_validation_active": 0,
             "local_validation_images": 3, "local_validation_active": 3, "local_validation_score_range": [0.04, 0.08],
             "test_used_for_calibration": False, "segmentation_head_and_threshold_unchanged": True, "development_history": PRIVATE,
             "source_checkpoint_sha256": SOURCE, "checkpoint_sha256": ADAPTER}
    files = {
        "raw/training/history.json": [{"epoch": 1, "loss": 0.6, "validation": {"candidates": candidates(0.5, 0.5)}, "elapsed_seconds": 10.0},
                                      {"epoch": 2, "loss": 0.4, "validation": {"candidates": candidates(0.4, 0.6)}, "elapsed_seconds": 20.0},
                                      {"epoch": 3, "loss": 0.3, "validation": {"candidates": candidates(0.5, 0.55)}, "elapsed_seconds": 30.0}],
        "raw/training/best_validation_v2.json": {"epoch": 2, "selected": {"threshold": 0.4, "non_bleached": scores(0.6),
                                                 "groups": [{"group": "reef-a", "baseline": scores(0.1), "adapted": scores(0.4)}, {"group": PRIVATE, "baseline": scores(0.1), "adapted": scores(0.4)}]},
                                                 "baseline": scores(0.17, 0.17, 1.0), "official_validation_all_pixels_unchanged": True, "official_validation_images": 4,
                                                 "guard_active_local_validation": 3, "local_validation_images": 3, "selection_note": PRIVATE},
        "raw/training/training_provenance_v2.json": {"args": {"command": "train", "root": PRIVATE, "epochs": 3, "steps": 5, "batch": 4, "crop": 768, "lr": 0.0001, "seed": 19, "out": PRIVATE, "device": "cuda"},
                                                     "base_unchanged": True, "base_sha256": BASE, "gpu": "PRIVATE-GPU", "elapsed_seconds": 31.5, "official_replay_images": 6,
                                                     "local_training_images": 8, "post_training_guard_calibration": guard, "actual_head_training_run": PRIVATE},
        "raw/calibration/guard-validation-v2.json": guard,
        "raw/evaluation/v2-assessment.json": {"local_test_per_image_iou_change": {"improved": 2, "unchanged": 1, "worse": 0}, "local_test_bleached_truth_pixels": 0, "fresh_untouched_generalization_evidence": False},
        "raw/evaluation/v2-test-report.json": {"checkpoint_sha256": ADAPTER, "domains": {"local": domain(3, 50, 0.24, 0.38), "official": domain(4, 0, 0.13, 0.13)}},
        "raw/evaluation/v2-official-train-audit.json": {"checkpoint_sha256": ADAPTER, "images": 10, "guard_active_images": 0, "changed_pixels": 0},
        "raw/export/export-verification.json": {"sha256": WEIGHT, "bytes": 1000, "tensor_count": 3, "base_tensors": 2, "trained_head_tensors": 1, "all_tensor_values_equal_to_verified_v2": True,
                                                "requires_other_weight_files": False, "source_adapter_sha256": ADAPTER, "source_api_reference": PRIVATE},
        "raw/export/single-file-equivalence.json": {"sha256": WEIGHT, "python": "3.13.9", "torch": "2.14.1+cu126", "transformers": PRIVATE, "gpu": "PRIVATE-GPU", "actual_images_compared": 2,
                                                    "all_predictions_pixel_identical_to_verified_v2": True, "both_guard_branches_exercised": True, "cli_prediction_pixel_identical_to_verified_v2": True},
        "raw/data/local-data-audit.json": {"split_frames": {"train": 8, "val": 3, "test": 3}, "split_groups": {"train": 1, "val": 1, "test": 1},
                                           "group_assignment": {"reef-a": "val", "reef-b": "train", "reef-c": "test"}, "grouping_basis": PRIVATE},
        "raw/data/official-data-provenance.json": {"source": PRIVATE, "revision": "e" * 40, "license": "Apache-2.0", "split_counts": {"train": 6, "val": 4, "test": 4}},
        "VERIFICATION.json": {"raw_terminal_stdout_stderr_available": False},
    }
    checksums = {}
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / "CHECKSUMS.sha256.json").write_text(json.dumps(checksums))
    return files


class CoralTrainingTests(TestCase):
    def setUp(self):
        self.model = ModelVersion.objects.create(id="coral:report", kind="coral", weight_path="private/coral.safetensors", sha256=WEIGHT,
                                                 labels={"0": "background", "1": "non_bleached", "2": "bleached"}, framework_version="4.57.1",
                                                 metadata={"training": {"epoch": 2, "seed": 19}, "inference": {"threshold": 0.4, "guard_threshold": -0.01}})
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.files = build(self.root)

    def rewrite(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        checksums = json.loads((self.root / "CHECKSUMS.sha256.json").read_text())
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root / "CHECKSUMS.sha256.json").write_text(json.dumps(checksums))

    def test_epochs_are_recomputed_from_raw_history_and_paths_dropped(self):
        snapshot, hashes = ingest(self.root, self.model)
        self.assertEqual([row["val/threshold"] for row in snapshot["epochs"]], [0.5, 0.4, 0.5])
        self.assertEqual([row["new_best"] for row in snapshot["epochs"]], [True, True, False])
        self.assertEqual(snapshot["epochs"][0]["val/iou@0.5"], 0.5)
        self.assertEqual(snapshot["selection"]["best_epoch"], 2)
        self.assertEqual(snapshot["arguments"], {"epochs": 3, "steps": 5, "batch": 4, "crop": 768, "seed": 19, "lr": 0.0001, "threshold_candidates": [0.3, 0.4, 0.5]})
        self.assertEqual([g["group"] for g in snapshot["validation"]["groups"]], ["reef-a"])
        self.assertEqual(snapshot["export"]["runtime"], {"python": "3.13.9", "torch": "2.14.1+cu126"})
        self.assertIn("validation_loss", snapshot["missing_inputs"])
        self.assertIn("raw_terminal_logs", snapshot["missing_inputs"])
        self.assertIn("raw/training/history.json", hashes)
        text = json.dumps(snapshot)
        self.assertNotIn("PRIVATE", text)
        self.assertNotIn("cuda", text)

    def test_lineage_checksums_and_selection_must_agree(self):
        cases = [("raw/export/export-verification.json", {**self.files["raw/export/export-verification.json"], "sha256": "f" * 64}, "training_weight_mismatch"),
                 ("raw/evaluation/v2-test-report.json", {**self.files["raw/evaluation/v2-test-report.json"], "checkpoint_sha256": "f" * 64}, "adapter_lineage_mismatch"),
                 ("raw/training/best_validation_v2.json", {**self.files["raw/training/best_validation_v2.json"], "epoch": 3}, "selected_epoch_mismatch")]
        for name, value, code in cases:
            original = self.files[name]
            self.rewrite(name, value)
            with self.assertRaisesMessage(ValueError, code):
                ingest(self.root, self.model)
            self.rewrite(name, original)
        (self.root / "raw/training/history.json").write_text("[]")
        with self.assertRaisesMessage(ValueError, "checksum_mismatch"):
            ingest(self.root, self.model)

    def test_registered_training_metadata_must_match(self):
        ModelVersion.objects.filter(pk=self.model.pk).update(metadata={"training": {"epoch": 12, "seed": 19}})
        self.model.refresh_from_db()
        with self.assertRaisesMessage(ValueError, "training_metadata_mismatch"):
            ingest(self.root, self.model)

    def test_cli_creates_coral_report_without_raw_strings(self):
        output = io.StringIO()
        call_command("import_coral_training", self.model.pk, str(self.root), stdout=output)
        report = TrainingReport.objects.get(pk=output.getvalue().strip())
        self.assertEqual(report.payload["template_version"], TEMPLATE_VERSION)
        self.assertEqual(report.payload["model_kind"], "coral")
        self.assertEqual([s["title"] for s in report.payload["sections"]], list(SECTION_NAMES))
        detail = self.client.get(f"/api/v1/reports/{report.pk}").json()
        self.assertEqual(detail["checkpoint_selection"]["best_epoch"], 2)
        for export in ("markdown", "html"):
            body = self.client.get(f"/api/v1/reports/{report.pk}/export", {"export": export}).content.decode()
            self.assertIn("珊瑚模型质量报告", body)
            self.assertIn("24.00% → 38.00%", body)
            self.assertIn("回归复核", body)
            for secret in ("PRIVATE", "private/coral", "cuda"):
                self.assertNotIn(secret, body)
        history = self.client.get(f"/api/v1/model-versions/{self.model.pk}/history").json()
        self.assertEqual(history["training_runs"][0]["selection"]["best_epoch"], 2)

    def test_cli_rejects_fish_models(self):
        fish = ModelVersion.objects.create(id="fish:other", weight_path="private/fish.pt", sha256=WEIGHT, labels={"0": "fish"}, framework_version="8.4.46")
        with self.assertRaises(CommandError):
            call_command("import_coral_training", fish.pk, str(self.root), stdout=io.StringIO())
