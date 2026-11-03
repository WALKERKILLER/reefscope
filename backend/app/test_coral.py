"""Coral checkpoint registration, Run kinds, published masks and pooled window statistics."""
import json
import struct
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from app.analysis.coral_query import summarize, window
from app.analysis.queue import claim_run
from app.analysis.storage import file_hash, write_json
from app.analysis.video import FrameClock
from app.models import AnalysisRun, ModelVersion
from app.test_analysis import RunFixture

LABELS = {"0": "background", "1": "non_bleached", "2": "bleached"}


def checkpoint(path, **changes):
    config = {"format": "reef-coral-final/v1", "labels": LABELS, "predicts_ignore": False, "architecture": "test",
              "source_model_license": "Apache-2.0", "training": {"epoch": 12},
              "inference": {"crop": 768, "threshold": 0.5, "precision": "bf16", "guard_threshold": -0.01},
              "source_model_config": {"source_model": "upstream/model", "source_revision": "abc", "bleached_source_ids": [3],
                                      "aggregation": "group_max", "scope": "two states", "id2label": {"0": "non_bleached", "1": "bleached"},
                                      "source_config": {"id2label": {"0": "unlabeled", "3": "acropora bleached"}}}} | changes
    tensors = {name: {"dtype": "F32", "shape": [1], "data_offsets": [4 * i, 4 * i + 4]}
               for i, name in enumerate(["base.w", "head.w", "guard.local_reference", "guard.official_reference"])}
    header = json.dumps({"__metadata__": {"coral_final": json.dumps(config)}, **tensors}).encode()
    path.write_bytes(struct.pack("<Q", len(header)) + header + bytes(16))
    return path


class CoralRunTests(RunFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.coral = ModelVersion.objects.create(id="coral:test", kind="coral", weight_path="private.safetensors", sha256="b" * 64,
                                                 labels=LABELS, framework_version="test")
        self.payload = {"kind": "coral", "models": {"coral": self.coral.pk}, "settings": {"sample_every_seconds": 1}}

    def publish(self, rows, extra_mask=False):
        """Fake adapter: writes the coral artifact layout the real adapter produces."""
        def adapter(run, output, progress):
            (output / "masks").mkdir()
            with (output / "frames.jsonl").open("w") as stream:
                for row in rows:
                    name = f"masks/{row['frame']:08d}.png"
                    (output / name).write_bytes(b"png-" + bytes([row["frame"]]))
                    stream.write(json.dumps(row | {"mask": name, "mask_sha256": file_hash(output / name), "width": 10, "height": 10}) + "\n")
            if extra_mask:
                (output / "masks/00000099.png").write_bytes(b"unindexed")
            write_json(output / "summary.json", {"schema": "coral-summary/v1", "limitations": ["Image-plane pixel shares, not benthic cover"]})
            names = ["frames.jsonl", "summary.json", *sorted(p.relative_to(output).as_posix() for p in (output / "masks").glob("*.png"))]
            write_json(output / "manifest.json", {"run_id": str(run.pk), "attempt": run.attempt, "artifacts": {n: file_hash(output / n) for n in names}})
        with patch("app.analysis.coral.analyze", side_effect=adapter):
            call_command("run_analysis_worker", once=True, kind="coral")

    def frame(self, frame, ms, separated, counts):
        return {"schema": "coral-frames/v1", "frame": frame, "timestamp_ms": ms, "background_separated": separated, "guard_score": 0.1,
                "pixel_counts": dict(zip("012", counts))}

    def test_kind_follows_model_and_settings_are_validated(self):
        run = self.enqueue()
        self.assertEqual(self.client.get(f"/api/v1/analysis-runs/{run.pk}").json()["kind"], "coral")
        self.assertEqual(run.config_snapshot["settings"], {"sample_every_seconds": 1, "camera_motion": "unknown"})
        url = f"/api/v1/tasks/{self.task.pk}/analysis-runs"
        for body in ({"kind": "fish", "models": {"fish": self.coral.pk}}, {"kind": "coral", "models": {"coral": self.model.pk}}):
            self.assertEqual(self.client.post(url, body, content_type="application/json").json()["error"]["code"], "model_kind_mismatch")
        for settings in ({"sample_every_seconds": 0.1}, {"sample_every_seconds": True}, {"sample_every_seconds": float("nan")}, {"imgsz": 640}):
            self.assertEqual(self.client.post(url, self.payload | {"settings": settings}, content_type="application/json").status_code, 400)

    def test_worker_kind_filter_and_fish_endpoints_reject_coral(self):
        self.enqueue()
        fish = AnalysisRun.objects.create(task=self.task, model=self.model, config_snapshot={})
        self.assertEqual(claim_run("fish").pk, fish.pk)
        self.assertIsNone(claim_run("fish"))
        self.publish([self.frame(0, 0, True, (60, 30, 10))])
        run = AnalysisRun.objects.get(model=self.coral)
        self.assertEqual(run.status, "completed")
        for resource in ("tracks", "heatmap"):
            self.assertEqual(self.client.get(f"/api/v1/analysis-runs/{run.pk}/{resource}").json()["error"]["code"], "run_kind_not_supported")
        self.assertEqual(self.client.get(f"/api/v1/analysis-runs/{fish.pk}/masks").status_code, 400)

    def test_masks_index_and_png_come_from_published_artifacts(self):
        run = self.enqueue()
        self.assertEqual(self.client.get(f"/api/v1/analysis-runs/{run.pk}/masks").status_code, 409)
        self.publish([self.frame(0, 0, True, (60, 30, 10)), self.frame(60, 2000, False, (0, 100, 0))])
        index = self.client.get(f"/api/v1/analysis-runs/{run.pk}/masks").json()
        self.assertEqual([item["frame"] for item in index["items"]], [0, 60])
        self.assertNotIn("mask", index["items"][0])
        image = self.client.get(f"/api/v1/analysis-runs/{run.pk}/masks", {"frame": 60})
        self.assertEqual((image["Content-Type"], b"".join(image.streaming_content)), ("image/png", b"png-<"))
        self.assertIn("immutable", image["Cache-Control"])
        self.assertEqual(self.client.get(f"/api/v1/analysis-runs/{run.pk}/masks", {"frame": 1}).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/analysis-runs/{run.pk}/masks", {"frame": "../x"}).status_code, 400)

    def test_unindexed_mask_blocks_completion(self):
        self.enqueue()
        self.publish([self.frame(0, 0, True, (60, 30, 10))], extra_mask=True)
        run = AnalysisRun.objects.get(model=self.coral)
        self.assertEqual((run.status, run.error_code), ("failed", "invalid_artifacts"))

    def test_shares_pool_pixels_and_exclude_frames_without_background(self):
        run = self.enqueue()
        self.publish([self.frame(0, 0, True, (60, 30, 10)), self.frame(30, 1000, True, (100, 0, 0)), self.frame(60, 2000, False, (0, 80, 20))])
        run.refresh_from_db()
        metrics = summarize(run, window({}))["metrics"]
        self.assertAlmostEqual(metrics["bleached_pixel_share"]["value"], 30 / 300)
        # Coral shares use separated frames only: 40 coral pixels of 200, 10 of them bleached.
        self.assertAlmostEqual(metrics["coral_pixel_share"]["value"], 40 / 200)
        self.assertAlmostEqual(metrics["bleached_coral_fraction"]["value"], 10 / 40)
        self.assertEqual(metrics["coral_cover"]["reason"], "requires_approved_benthic_roi")
        late = summarize(run, window({"start_ms": "1500"}))
        self.assertEqual((late["metrics"]["coral_pixel_share"]["value"], late["metrics"]["coral_pixel_share"]["reason"]), (None, "no_background_separated_frames"))
        self.assertIsNone(late["series"][0]["coral_share"])
        middle = summarize(run, window({"start_ms": "500", "end_ms": "1500"}))["metrics"]
        self.assertEqual(middle["bleached_coral_fraction"]["reason"], "no_coral_pixels")
        response = self.client.get(f"/api/v1/analysis-runs/{run.pk}/summary", {"roi": "[]"})
        self.assertEqual(response.status_code, 400)
        exported = self.client.get(f"/api/v1/analysis-runs/{run.pk}/summary", {"export": "json"})
        self.assertIn("attachment", exported["Content-Disposition"])


class CoralRegistrationTests(TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        context = override_settings(CORAL_MODEL_ROOT=self.root / "models")
        context.enable()
        self.addCleanup(context.disable)
        (self.root / "models").mkdir()
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        metrics = {model: {cls: {"iou": 0.5, "f1": 0.6, "precision": 0.7, "recall": 0.8, "support_pixels": 9} for cls in "012"} for model in ("baseline", "adapted")}
        domain = {"images": 46, "guard_active_images": 28, "changed_pixels": 5, "metrics": {"full_image": metrics}}
        (self.evidence / "test-report.json").write_text(json.dumps({"evaluation_context": "regression_recheck", "split": "test", "domains": {"local": domain}}))
        (self.evidence / "assessment.json").write_text(json.dumps({"fresh_untouched_generalization_evidence": False, "local_test_bleached_truth_pixels": 0}))

    def register(self, path, *args):
        with patch("app.management.commands.register_coral_model.load_check", return_value="4.57.1"):
            call_command("register_coral_model", "coral:v2", str(path), *args)

    def test_registers_metadata_and_scoped_evidence_without_path(self):
        self.register(checkpoint(self.root / "models" / "coral.safetensors"), "--evidence", str(self.evidence))
        model = ModelVersion.objects.get()
        self.assertEqual((model.kind, model.labels, model.framework_version), ("coral", LABELS, "4.57.1"))
        self.assertEqual(model.metadata["bleached_source_labels"], ["acropora bleached"])
        evidence = model.metadata["delivery_evidence"]
        self.assertEqual((evidence["evaluation_context"], evidence["fresh_untouched_generalization_evidence"]), ("regression_recheck", False))
        self.assertNotIn("0", evidence["domains"]["local"]["full_image"]["adapted"])
        body = self.client.get("/api/v1/models").content.decode()
        self.assertIn('"kind":"coral"', body)
        self.assertNotIn("coral.safetensors", body)

    def test_rejects_untrusted_or_incompatible_checkpoints(self):
        outside = checkpoint(self.root / "coral.safetensors")
        cases = [(outside, "weight_outside_trusted_root"),
                 (checkpoint(self.root / "models" / "coral.pt"), "weight_outside_trusted_root"),
                 (checkpoint(self.root / "models" / "a.safetensors", format="other/v1"), "unsupported_coral_checkpoint"),
                 (checkpoint(self.root / "models" / "b.safetensors", labels={"0": "coral"}), "unsupported_coral_checkpoint")]
        truncated = self.root / "models" / "c.safetensors"
        truncated.write_bytes(checkpoint(self.root / "models" / "d.safetensors").read_bytes()[:-8])
        cases.append((truncated, "invalid_checkpoint"))
        for path, code in cases:
            with self.assertRaisesMessage(CommandError, code):
                self.register(path)
        self.assertFalse(ModelVersion.objects.exists())


class FrameClockTests(TestCase):
    def test_pts_first_with_counted_fallback_and_reversal_guard(self):
        clock = FrameClock(25)
        self.assertEqual([clock.stamp(0, 0), clock.stamp(1, 40), clock.stamp(2, float("nan"))], [0, 40, 80])
        self.assertEqual(clock.fallbacks, 1)
        with self.assertRaisesMessage(ValueError, "video_time_reversed"):
            clock.stamp(3, 10)
        with self.assertRaisesMessage(ValueError, "video_time_unavailable"):
            FrameClock(float("nan")).stamp(1, -1)
