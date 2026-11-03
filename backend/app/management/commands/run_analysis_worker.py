"""Independent bounded-concurrency analysis Worker."""
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from app.analysis.queue import claim_run, fail, finish, heartbeat
from app.analysis.storage import attempt_directory, verify_artifacts


class Command(BaseCommand):
    help = "Process queued analysis Runs independently of the Web server."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        # Separate processes keep each adapter's torch settings and model cache apart.
        parser.add_argument("--kind", choices=("fish", "coral"))

    def handle(self, *args, **options):
        from app.analysis import coral, fish
        adapters = {"fish": fish, "coral": coral}
        while True:
            close_old_connections()
            run = claim_run(options["kind"])
            if run:
                try:
                    output = attempt_directory(run)
                    heartbeat(run, 0)
                    adapters[run.model.kind].analyze(run, output, lambda value: heartbeat(run, value))
                    summary = verify_artifacts(output, run)
                    finish(run, summary)
                except Exception as exc:
                    safe_codes = {"model_hash_mismatch", "video_decode_failed", "invalid_video_dimensions", "video_time_reversed",
                                  "video_time_unavailable", "video_time_invalid", "video_incomplete", "invalid_model_output", "invalid_video", "invalid_artifacts", "input_changed", "too_many_samples"}
                    fail(run, str(exc) if isinstance(exc, ValueError) and str(exc) in safe_codes else "analysis_failed")
            if options["once"]:
                return
            if run is None:
                time.sleep(1)
