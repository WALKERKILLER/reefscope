"""Register an explicitly trusted local checkpoint without exposing its path."""
import re
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from app.analysis.storage import file_hash
from app.models import ModelVersion


class Command(BaseCommand):
    help = "Register an authorized local fish checkpoint; IDs cannot be overwritten."

    def add_arguments(self, parser):
        parser.add_argument("model_id")
        parser.add_argument("weight")

    def handle(self, *args, **options):
        model_id = options["model_id"]
        root = Path(settings.YOLO_MODEL_ROOT).resolve()
        path = Path(options["weight"]).resolve()
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9:._-]{0,79}", model_id):
            raise CommandError("invalid_model_id")
        if not path.is_relative_to(root) or not path.is_file() or path.suffix != ".pt":
            raise CommandError("weight_outside_trusted_root")
        if ModelVersion.objects.filter(pk=model_id).exists():
            raise CommandError("model_id_already_registered")
        # Loading pickle checkpoints is allowed only in this trusted operator command.
        os.environ["YOLO_AUTOINSTALL"] = "false"
        from ultralytics import YOLO, __version__
        before = file_hash(path)
        model = YOLO(str(path))
        if model.task != "detect":
            raise CommandError("detection_model_required")
        labels = {str(k): str(v) for k, v in model.names.items()}
        if before != file_hash(path):
            raise CommandError("weight_changed_during_registration")
        try:
            ModelVersion.objects.create(id=model_id, weight_path=str(path), sha256=before, labels=labels, framework_version=__version__)
        except IntegrityError as exc:
            raise CommandError("model_id_already_registered") from exc
        self.stdout.write(f"Registered {model_id}")
