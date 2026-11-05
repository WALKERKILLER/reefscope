"""Private Run artifacts, outside the directly served media tree."""
import hashlib
import json
import re
from pathlib import Path

from django.conf import settings


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def attempt_directory(run):
    root = Path(settings.ANALYSIS_ROOT).resolve()
    path = root / str(run.id) / str(run.attempt_token)
    if path.is_symlink() or (root / str(run.id)).is_symlink():
        raise ValueError("invalid_artifact_path")
    path.mkdir(parents=True, exist_ok=True)
    if not path.resolve().is_relative_to(root):
        raise ValueError("invalid_artifact_path")
    return path


def input_video(task):
    root = Path(settings.MEDIA_ROOT).resolve()
    if not task.uploaded_video_path.startswith(settings.MEDIA_URL):
        raise ValueError("invalid_video")
    path = (root / task.uploaded_video_path[len(settings.MEDIA_URL):]).resolve()
    if not path.is_relative_to(root / "uploads") or not path.is_file():
        raise ValueError("invalid_video")
    return path


def write_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


REQUIRED = {"fish": {"tracks.jsonl", "summary.json"}, "coral": {"frames.jsonl", "summary.json"}}
MASK = re.compile(r"masks/\d{8}\.png")


def artifact(run, name):
    if not (name in ("tracks.jsonl", "frames.jsonl", "manifest.json", "summary.json") or MASK.fullmatch(name)) or run.status != "completed":
        raise ValueError("artifact_unavailable")
    path = attempt_directory(run) / name
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        raise ValueError("artifact_unavailable")
    return path


def verify_artifacts(output, run):
    manifest_path = output / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("invalid_artifacts")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != str(run.pk) or manifest.get("attempt") != run.attempt:
        raise ValueError("invalid_artifacts")
    expected = manifest.get("artifacts", {})
    required = REQUIRED[run.model.kind]
    masks = set(expected) - required if isinstance(expected, dict) else set()
    if not isinstance(expected, dict) or not required <= set(expected) or (masks and run.model.kind != "coral") or not all(MASK.fullmatch(name) for name in masks):
        raise ValueError("invalid_artifacts")
    if (output / "masks").is_symlink():
        raise ValueError("invalid_artifacts")
    for name, digest in expected.items():
        path = output / name
        if path.is_symlink() or not path.is_file() or file_hash(path) != digest:
            raise ValueError("invalid_artifacts")
    if run.model.kind == "coral":
        # Every published mask is indexed by exactly one frame record, and every record's mask is published.
        lines = (output / "frames.jsonl").read_text(encoding="utf-8").splitlines()
        if sorted(json.loads(line)["mask"] for line in lines) != sorted(masks) or not masks:
            raise ValueError("invalid_artifacts")
    return json.loads((output / "summary.json").read_text(encoding="utf-8"))
