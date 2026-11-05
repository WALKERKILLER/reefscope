"""Register a delivered reef-coral-final/v1 checkpoint without exposing its path.

Safetensors headers are JSON, so validation reads no pickle. The loader check then builds the
model once with the vendored inference code, which also verifies the frozen base fingerprint.
"""
import json
import re
import struct
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from app.analysis.storage import file_hash
from app.models import ModelVersion

FORMAT = "reef-coral-final/v1"
LABELS = {"0": "background", "1": "non_bleached", "2": "bleached"}
GUARD = {"guard.local_reference", "guard.official_reference"}


def read_header(path):
    with path.open("rb") as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise CommandError("invalid_checkpoint")
        size = struct.unpack("<Q", prefix)[0]
        if not 2 <= size <= 100 * 1024 * 1024:
            raise CommandError("invalid_checkpoint")
        try:
            header = json.loads(stream.read(size))
            config = json.loads(header.pop("__metadata__")["coral_final"])
        except (ValueError, KeyError, TypeError) as exc:
            raise CommandError("not_a_coral_checkpoint") from exc
    data = path.stat().st_size - 8 - size
    if any(not isinstance(item, dict) or not 0 <= item["data_offsets"][0] <= item["data_offsets"][1] <= data for item in header.values()):
        raise CommandError("invalid_checkpoint")
    names = set(header)
    if (config.get("format") != FORMAT or config.get("labels") != LABELS or config.get("predicts_ignore") is not False
            or not GUARD <= names or not any(n.startswith("base.") for n in names) or not any(n.startswith("head.") for n in names)
            or names - GUARD - {n for n in names if n.startswith(("base.", "head."))}):
        raise CommandError("unsupported_coral_checkpoint")
    return config


def load_check(path):
    """Builds the model on CPU; raises if tensors, fingerprint or the installed Transformers do not fit."""
    import transformers
    from app.analysis.vendor.coral_model import CoralModel
    CoralModel(str(path), device="cpu")
    return transformers.__version__


def describe(config):
    source, inference = config["source_model_config"], config["inference"]
    labels = source["source_config"]["id2label"]
    return {"format": config["format"], "architecture": config["architecture"], "source_model": source["source_model"],
            "source_revision": source["source_revision"], "source_model_license": config["source_model_license"],
            "source_aggregation": source["aggregation"], "source_scope": source["scope"],
            "bleached_source_labels": [labels[str(i)] for i in source["bleached_source_ids"]],
            "inference": {key: inference[key] for key in ("crop", "threshold", "precision", "guard_threshold")},
            "training": config["training"]}


def delivery_evidence(directory):
    """Declared delivery numbers only; they describe a regression recheck on previously inspected test sets."""
    files = {name: directory / name for name in ("assessment.json", "test-report.json")}
    if any(path.is_symlink() or not path.is_file() for path in files.values()):
        raise CommandError("evidence_files_missing")
    assessment, report = (json.loads(files[name].read_text(encoding="utf-8")) for name in ("assessment.json", "test-report.json"))
    keys = ("iou", "f1", "precision", "recall", "support_pixels")
    domains = {}
    for name, domain in report["domains"].items():
        metrics = domain["metrics"]["full_image"]
        domains[name] = {"images": domain["images"], "guard_active_images": domain["guard_active_images"], "changed_pixels": domain["changed_pixels"],
                         "full_image": {model: {cls: {key: metrics[model][cls][key] for key in keys} for cls in ("1", "2")} for model in ("baseline", "adapted")}}
    return {"evaluation_context": report["evaluation_context"], "split": report["split"],
            "fresh_untouched_generalization_evidence": assessment["fresh_untouched_generalization_evidence"],
            "local_test_bleached_truth_pixels": assessment["local_test_bleached_truth_pixels"], "domains": domains,
            "source_sha256": {name: file_hash(path) for name, path in files.items()}}


class Command(BaseCommand):
    help = "Register an authorized local coral checkpoint; IDs cannot be overwritten."

    def add_arguments(self, parser):
        parser.add_argument("model_id")
        parser.add_argument("weight")
        parser.add_argument("--evidence", help="Delivery evidence directory with assessment.json and test-report.json")

    def handle(self, *args, **options):
        model_id = options["model_id"]
        root = Path(settings.CORAL_MODEL_ROOT).resolve()
        path = Path(options["weight"]).resolve()
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9:._-]{0,79}", model_id):
            raise CommandError("invalid_model_id")
        if not path.is_relative_to(root) or not path.is_file() or path.suffix != ".safetensors":
            raise CommandError("weight_outside_trusted_root")
        if ModelVersion.objects.filter(pk=model_id).exists():
            raise CommandError("model_id_already_registered")
        before = file_hash(path)
        metadata = describe(read_header(path))
        try:
            if options["evidence"]:
                metadata["delivery_evidence"] = delivery_evidence(Path(options["evidence"]).resolve())
        except (ValueError, KeyError, TypeError) as exc:
            raise CommandError("invalid_evidence") from exc
        version = load_check(path)
        if before != file_hash(path):
            raise CommandError("weight_changed_during_registration")
        try:
            ModelVersion.objects.create(id=model_id, kind="coral", weight_path=str(path), sha256=before, labels=LABELS,
                                        framework_version=version, metadata=metadata)
        except IntegrityError as exc:
            raise CommandError("model_id_already_registered") from exc
        self.stdout.write(f"Registered {model_id}")
