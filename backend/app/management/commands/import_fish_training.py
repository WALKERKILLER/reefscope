"""Operator-only numeric training ingest; never accepts paths from HTTP."""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.analysis.storage import file_hash
from app.analysis.training import ingest
from app.analysis.reports import make_report
from app.models import ModelVersion, TrainingRun, EvaluationRun, TrainingReport


class Command(BaseCommand):
    help = "Import sanitized numeric training evidence and generate a seven-part report."

    def add_arguments(self, parser):
        parser.add_argument("model_id")
        parser.add_argument("directory")
        parser.add_argument("--evaluation")
        parser.add_argument("--baseline")

    def handle(self, *args, **options):
        try:
            model = ModelVersion.objects.get(pk=options["model_id"])
            snapshot, hashes = ingest(options["directory"])
            checkpoint = Path(options["directory"]) / "weights" / "best.pt"
            if checkpoint.exists():
                hashes["best.pt"] = file_hash(checkpoint)
                if hashes["best.pt"] != model.sha256:
                    raise ValueError("training_checkpoint_model_mismatch")
            else:
                snapshot["missing_inputs"].append("training_checkpoint")
            last = Path(options["directory"]) / "weights" / "last.pt"
            if last.exists():
                hashes["last.pt"] = file_hash(last)
            evaluation = EvaluationRun.objects.get(pk=options["evaluation"]) if options["evaluation"] else None
            baseline = EvaluationRun.objects.get(pk=options["baseline"]) if options["baseline"] else None
            with transaction.atomic():
                training = TrainingRun.objects.create(model=model,snapshot=snapshot,source_hashes=hashes)
                payload, markdown, html = make_report(model,training,evaluation,baseline)
                report = TrainingReport.objects.create(model=model,training_run=training,evaluation_run=evaluation,payload=payload,markdown=markdown,html=html)
        except (ModelVersion.DoesNotExist, EvaluationRun.DoesNotExist, OSError, ValueError) as exc:
            raise CommandError("training_import_failed; check registered model, numeric sources and comparison eligibility") from exc
        self.stdout.write(str(report.pk))
