"""Operator-only coral training-log ingest; never accepts paths from HTTP."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.analysis.coral_reports import make_coral_report
from app.analysis.coral_training import ingest
from app.models import ModelVersion, TrainingRun, TrainingReport


class Command(BaseCommand):
    help = "Import a verified coral training-log package and generate a seven-part report."

    def add_arguments(self, parser):
        parser.add_argument("model_id")
        parser.add_argument("directory")

    def handle(self, *args, **options):
        try:
            model = ModelVersion.objects.get(pk=options["model_id"], kind="coral")
            snapshot, hashes = ingest(options["directory"], model)
            with transaction.atomic():
                training = TrainingRun.objects.create(model=model, snapshot=snapshot, source_hashes=hashes)
                payload, markdown, html = make_coral_report(model, training)
                report = TrainingReport.objects.create(model=model, training_run=training, payload=payload, markdown=markdown, html=html)
        except (ModelVersion.DoesNotExist, OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
            reason = f":{exc}" if type(exc) is ValueError else ""
            raise CommandError(f"coral_training_import_failed{reason}; check registered coral model, package checksums and weight lineage") from exc
        self.stdout.write(str(report.pk))
