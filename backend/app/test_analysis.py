"""Run ownership, retries, public boundaries and migration-backed persistence."""
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from app.analysis.contracts import validate_settings
from app.analysis.queue import claim_run, expire_runs, finish, heartbeat, retry
from app.analysis.storage import artifact, attempt_directory, input_video, file_hash, write_json
from app.models import AnalysisRun, ModelVersion, Task


class RunFixture:
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.settings_context = override_settings(ANALYSIS_ROOT=self.root / "analysis", MEDIA_ROOT=self.root / "media")
        self.settings_context.enable()
        self.addCleanup(self.settings_context.disable)
        self.task = Task.objects.create(original_filename="fish.mp4", uploaded_video_path="/media/uploads/fish.mp4")
        self.model = ModelVersion.objects.create(id="fish:test", weight_path="private.pt", sha256="a"*64, labels={"0":"fish"}, framework_version="test")
        self.payload = {"kind":"fish", "models":{"fish":self.model.pk}, "settings":{}}

    def enqueue(self):
        response = self.client.post(f"/api/v1/tasks/{self.task.pk}/analysis-runs", self.payload, content_type="application/json")
        self.assertEqual(response.status_code, 202)
        return AnalysisRun.objects.get(pk=response.json()["run_id"])


class RunTests(RunFixture, TestCase):
    def test_independent_runs_and_snapshots(self):
        first, second = self.enqueue(), self.enqueue()
        self.assertNotEqual(first.pk, second.pk)
        claimed = claim_run()
        directory = attempt_directory(claimed)
        other = claim_run()
        self.assertNotEqual(directory, attempt_directory(other))
        self.assertIsNone(claim_run())
        self.assertEqual(first.config_snapshot["model_sha256"], self.model.sha256)
        self.assertEqual(self.client.get(f"/api/v1/tasks/{self.task.pk}/analysis-runs").json()["items"][0]["status"], "running")

    def test_expiry_retry_fences_old_worker_and_limits_attempts(self):
        run = self.enqueue()
        first = claim_run()
        AnalysisRun.objects.filter(pk=run.pk).update(lease_expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(expire_runs(), 1)
        self.assertEqual(retry(run.pk), 1)
        self.assertEqual(retry(run.pk), 0)
        second = claim_run()
        with self.assertRaisesMessage(ValueError, "worker_lease_lost"):
            finish(first, {"wrong": True})
        heartbeat(second, 50)
        for attempt in (2, 3):
            AnalysisRun.objects.filter(pk=run.pk).update(status="failed")
            if attempt == 2:
                self.assertEqual(retry(run.pk), 1)
                self.assertEqual(claim_run().attempt, 3)
        self.assertEqual(retry(run.pk), 0)
        self.assertEqual(self.client.post(f"/api/v1/analysis-runs/{run.pk}/retry").status_code, 409)

    def test_public_input_validation_and_private_model_paths(self):
        for update in ({"kind":"joint"}, {"models":{"fish":"/etc/passwd"}}, {"settings":{"imgsz":True}}, {"settings":{"imgsz":999999}}, {"settings":{"device":"cpu"}}, {"settings":{"tracking_frame_stride":2}}):
            response = self.client.post(f"/api/v1/tasks/{self.task.pk}/analysis-runs", self.payload | update, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        for number in (float("nan"), float("inf"), True, -1):
            with self.assertRaises(ValueError):
                validate_settings({"confidence_threshold":number})
        self.assertNotIn("private.pt", self.client.get("/api/v1/models").content.decode())

    def test_source_and_artifact_boundaries(self):
        run = self.enqueue()
        self.task.uploaded_video_path = "/media/uploads/../../outside.mp4"
        with self.assertRaises(ValueError):
            input_video(self.task)
        run = claim_run()
        output = attempt_directory(run)
        with self.assertRaises(ValueError):
            artifact(run, "tracks.jsonl")
        finish(run, {})
        run.refresh_from_db()
        (output / "tracks.jsonl").symlink_to(self.root / "outside")
        with self.assertRaises(ValueError):
            artifact(run, "tracks.jsonl")
        self.assertEqual(self.client.delete(f"/api/task/{self.task.pk}").status_code, 409)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_worker_persists_completion_and_sanitizes_errors(self):
        self.enqueue()
        def adapter(run, output, progress):
            (output / "tracks.jsonl").write_text("")
            write_json(output / "summary.json", {"frame_count":3})
            write_json(output / "manifest.json", {"run_id":str(run.pk), "attempt":run.attempt,
                       "artifacts": {name:file_hash(output/name) for name in ("tracks.jsonl", "summary.json")}})
        with patch("app.analysis.fish.analyze", side_effect=adapter):
            call_command("run_analysis_worker", once=True)
        run = AnalysisRun.objects.get()
        self.assertEqual((run.status, run.progress), ("completed",100))
        self.assertEqual(run.summary, {"frame_count":3})
        second = self.enqueue()
        with patch("app.analysis.fish.analyze", side_effect=RuntimeError("secret local path")):
            call_command("run_analysis_worker", once=True)
        second.refresh_from_db()
        self.assertEqual(second.error_code, "analysis_failed")
        response = self.client.get(f"/api/v1/analysis-runs/{second.pk}")
        self.assertNotIn("secret", response.content.decode())

    def test_legacy_list_and_process_not_dispatched_by_new_api(self):
        with patch("app.views.start_processing") as start:
            self.enqueue()
            start.assert_not_called()
        response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()[0]["task_id"], self.task.pk)

    def test_worker_cannot_publish_missing_artifacts(self):
        self.enqueue()
        with patch("app.analysis.fish.analyze", return_value={}):
            call_command("run_analysis_worker", once=True)
        run = AnalysisRun.objects.get()
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.error_code, "invalid_artifacts")


class ProcessOwnershipTests(TestCase):
    def test_two_independent_processes_only_claim_once(self):
        import os
        import subprocess
        import sys
        import textwrap

        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / "queue.sqlite3")
            gate = Path(directory) / "start"
            setup = textwrap.dedent('''
                import os, sys, time
                os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
                from django.conf import settings
                settings.DATABASES['default']['NAME'] = sys.argv[1]
                import django
                django.setup()
            ''')
            bootstrap = setup + textwrap.dedent('''
                from django.core.management import call_command
                call_command('migrate', verbosity=0)
                from app.models import Task, ModelVersion, AnalysisRun
                task = Task.objects.create(original_filename='synthetic.mp4', uploaded_video_path='/media/uploads/synthetic.mp4')
                model = ModelVersion.objects.create(id='test', weight_path='unused', sha256='a'*64, labels={}, framework_version='test')
                AnalysisRun.objects.create(task=task, model=model, config_snapshot={})
            ''')
            cwd = str(Path(__file__).resolve().parents[1])
            subprocess.run([sys.executable, "-c", bootstrap, database], cwd=cwd, check=True, capture_output=True, timeout=30)
            claimant = setup + textwrap.dedent('''
                from pathlib import Path
                from app.analysis.queue import claim_run
                deadline = time.monotonic() + 10
                while not Path(sys.argv[2]).exists():
                    if time.monotonic() > deadline:
                        raise RuntimeError('test_start_timeout')
                    time.sleep(0.01)
                print(int(claim_run() is not None))
            ''')
            processes = [subprocess.Popen([sys.executable, "-c", claimant, database, str(gate)], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
            try:
                gate.touch()
                results = [process.communicate(timeout=30) for process in processes]
                self.assertTrue(all(process.returncode == 0 for process in processes))
                self.assertEqual(sum(int(stdout.strip()) for stdout, _ in results), 1)
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
