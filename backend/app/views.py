import os
import shutil
import tomllib
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.utils.text import get_valid_filename
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Task
from .serializers import TaskSerializer
from .services.task_runner import clear_runtime_progress, start_processing

CONFIG_FILE_PATH = Path(settings.BASE_DIR) / "config" / "pipeline_settings.toml"
DEFAULT_PIPELINE_CONFIG = {
    "modelPath": "models/model_best.pt",
    "targetLabels": "fish",
    "confidenceThreshold": 0.25,
    "iouThreshold": 0.45,
    "frameStride": 5,
    "batchSize": 8,
    "useHalf": True,
}

TASK_MUTATION_ACTIONS = {"delete", "copy", "rerun", "rename"}


def _delete_media_file(media_url: str) -> None:
    if not media_url or not media_url.startswith(settings.MEDIA_URL):
        return

    relative_path = media_url.replace(settings.MEDIA_URL, "", 1)
    file_path = (Path(settings.MEDIA_ROOT) / relative_path).resolve()
    media_root = Path(settings.MEDIA_ROOT).resolve()

    if media_root in file_path.parents and file_path.exists():
        file_path.unlink()


def _media_url_to_absolute_path(media_url: str) -> Path | None:
    if not media_url or not media_url.startswith(settings.MEDIA_URL):
        return None

    relative_path = media_url.replace(settings.MEDIA_URL, "", 1)
    file_path = (Path(settings.MEDIA_ROOT) / relative_path).resolve()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if media_root not in file_path.parents:
        return None
    return file_path


def _build_unique_task_filename(filename: str, suffix_hint: str = "copy") -> str:
    source = Path(filename)
    stem = source.stem
    suffix = source.suffix or ".mp4"
    candidate = f"{stem} ({suffix_hint}){suffix}"
    index = 2

    while Task.objects.filter(original_filename=candidate).exists():
        candidate = f"{stem} ({suffix_hint} {index}){suffix}"
        index += 1

    return candidate


def _build_available_file_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    source = Path(filename)
    stem = source.stem
    suffix = source.suffix
    candidate = directory / source.name
    index = 2

    while candidate.exists():
        candidate = directory / f"{stem} {index}{suffix}"
        index += 1

    return candidate


def _copy_media_file(media_url: str, target_filename: str | None = None) -> str:
    source_path = _media_url_to_absolute_path(media_url)
    if source_path is None or not source_path.exists():
        return ""

    target_path = _build_available_file_path(source_path.parent, target_filename or source_path.name)
    shutil.copy2(source_path, target_path)

    relative_path = target_path.relative_to(Path(settings.MEDIA_ROOT).resolve()).as_posix()
    return f"{settings.MEDIA_URL}{relative_path}"


def _rename_media_file(media_url: str, target_filename: str) -> str:
    source_path = _media_url_to_absolute_path(media_url)
    if source_path is None or not source_path.exists():
        return media_url

    target_path = source_path.with_name(target_filename)
    if target_path != source_path:
        target_path = _build_available_file_path(source_path.parent, target_filename)
        source_path.rename(target_path)

    relative_path = target_path.relative_to(Path(settings.MEDIA_ROOT).resolve()).as_posix()
    return f"{settings.MEDIA_URL}{relative_path}"


def _serialize_task_list(tasks) -> list[dict]:
    return TaskSerializer(tasks, many=True).data


def _run_task_action(task: Task, action: str, payload: dict | None = None) -> dict | None:
    action = str(action or "").strip().lower()
    payload = payload or {}

    if action == "delete":
        _delete_media_file(task.uploaded_video_path)
        _delete_media_file(task.result_video_path)
        clear_runtime_progress(task.id)
        task.delete()
        return None

    if action == "copy":
        copied_name = _build_unique_task_filename(task.original_filename, "copy")
        duplicated_video_path = _copy_media_file(task.uploaded_video_path, copied_name)
        result_copy_name = f"result_{Path(copied_name).stem}.mp4"
        duplicated_result_path = _copy_media_file(task.result_video_path, result_copy_name)
        copied_task = Task.objects.create(
            original_filename=copied_name,
            uploaded_video_path=duplicated_video_path,
            result_video_path=duplicated_result_path,
            detections=task.detections,
            progress=task.progress if task.status == Task.Status.COMPLETED else 0,
            status=task.status if task.status == Task.Status.COMPLETED else Task.Status.PENDING,
        )
        return TaskSerializer(copied_task).data

    if action == "rerun":
        process_options = _parse_process_options(payload)
        Task.objects.filter(pk=task.pk).update(
            result_video_path="",
            detections=[],
            progress=0,
            status=Task.Status.PENDING,
        )
        start_processing(task.id, process_options)
        task.refresh_from_db()
        return TaskSerializer(task).data

    if action == "rename":
        new_name = str(payload.get("name") or "").strip()
        if not new_name:
            raise ValueError("重命名不能为空。")
        if not new_name.lower().endswith(".mp4"):
            new_name = f"{new_name}.mp4"
        safe_name = get_valid_filename(new_name)
        task.original_filename = safe_name
        task.uploaded_video_path = _rename_media_file(task.uploaded_video_path, safe_name)
        if task.result_video_path:
            result_name = f"result_{Path(safe_name).stem}.mp4"
            task.result_video_path = _rename_media_file(task.result_video_path, result_name)
        task.save()
        return TaskSerializer(task).data

    raise ValueError("不支持的任务操作。")


def _parse_probability(value, field_name: str, default: float) -> float:
    if value in (None, ""):
        return default

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须是数字。") from exc

    if parsed < 0 or parsed > 1:
        raise ValueError(f"{field_name} 必须在 0 到 1 之间。")
    return parsed


def _parse_positive_int(value, field_name: str, default: int) -> int:
    if value in (None, ""):
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须是正整数。") from exc

    if parsed < 1:
        raise ValueError(f"{field_name} 必须大于等于 1。")
    return parsed


def _parse_bool(value, field_name: str, default: bool | None) -> bool | None:
    if value in (None, ""):
        return default

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{field_name} 必须是布尔值。")


def _parse_process_options(data: dict) -> dict:
    model_path = str(data.get("model_path") or "").strip()
    if not model_path:
        model_path = str(os.environ.get("YOLO_MODEL_PATH") or "").strip()
    if not model_path:
        model_path = "models/model_best.pt"

    raw_target_labels = data.get("target_labels")
    if isinstance(raw_target_labels, str):
        target_labels = [item.strip() for item in raw_target_labels.split(",") if item.strip()]
    elif isinstance(raw_target_labels, list):
        target_labels = [str(item).strip() for item in raw_target_labels if str(item).strip()]
    else:
        target_labels = []

    if not target_labels:
        target_labels = ["fish"]

    return {
        "model_path": model_path,
        "target_labels": target_labels,
        "confidence_threshold": _parse_probability(data.get("confidence_threshold"), "confidence_threshold", 0.25),
        "iou_threshold": _parse_probability(data.get("iou_threshold"), "iou_threshold", 0.45),
        "frame_stride": _parse_positive_int(data.get("frame_stride"), "frame_stride", 5),
        "batch_size": _parse_positive_int(data.get("batch_size"), "batch_size", 8),
        "use_half": _parse_bool(data.get("use_half"), "use_half", None),
    }


def _normalize_pipeline_settings(data: dict | None) -> dict:
    source = dict(DEFAULT_PIPELINE_CONFIG)
    if data:
        source.update(data)

    target_labels = source.get("targetLabels", DEFAULT_PIPELINE_CONFIG["targetLabels"])
    if isinstance(target_labels, list):
        target_labels = ", ".join(str(item).strip() for item in target_labels if str(item).strip())
    target_labels = str(target_labels or DEFAULT_PIPELINE_CONFIG["targetLabels"]).strip() or DEFAULT_PIPELINE_CONFIG["targetLabels"]

    return {
        "modelPath": str(source.get("modelPath") or DEFAULT_PIPELINE_CONFIG["modelPath"]).strip(),
        "targetLabels": target_labels,
        "confidenceThreshold": _parse_probability(
            source.get("confidenceThreshold"),
            "confidenceThreshold",
            DEFAULT_PIPELINE_CONFIG["confidenceThreshold"],
        ),
        "iouThreshold": _parse_probability(
            source.get("iouThreshold"),
            "iouThreshold",
            DEFAULT_PIPELINE_CONFIG["iouThreshold"],
        ),
        "frameStride": _parse_positive_int(
            source.get("frameStride"),
            "frameStride",
            DEFAULT_PIPELINE_CONFIG["frameStride"],
        ),
        "batchSize": _parse_positive_int(
            source.get("batchSize"),
            "batchSize",
            DEFAULT_PIPELINE_CONFIG["batchSize"],
        ),
        "useHalf": bool(_parse_bool(source.get("useHalf"), "useHalf", DEFAULT_PIPELINE_CONFIG["useHalf"])),
    }


def _pipeline_settings_to_toml(settings_payload: dict) -> str:
    normalized = _normalize_pipeline_settings(settings_payload)
    target_labels = [
        item.strip()
        for item in str(normalized["targetLabels"]).split(",")
        if item.strip()
    ] or ["fish"]

    def quote_toml_string(value: str) -> str:
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    escaped_model_path = quote_toml_string(normalized["modelPath"])
    target_label_lines = ", ".join(quote_toml_string(item) for item in target_labels)

    return (
        "[pipeline]\n"
        f"model_path = {escaped_model_path}\n"
        f"target_labels = [{target_label_lines}]\n"
        f"confidence_threshold = {normalized['confidenceThreshold']:.2f}\n"
        f"iou_threshold = {normalized['iouThreshold']:.2f}\n"
        f"frame_stride = {normalized['frameStride']}\n"
        f"batch_size = {normalized['batchSize']}\n"
        f"use_half = {'true' if normalized['useHalf'] else 'false'}\n"
    )


def _ensure_pipeline_config_file() -> None:
    if CONFIG_FILE_PATH.exists():
        return

    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE_PATH.write_text(_pipeline_settings_to_toml(DEFAULT_PIPELINE_CONFIG), encoding="utf-8")


def _parse_pipeline_toml_content(content: str) -> dict:
    try:
        parsed = tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"TOML 配置解析失败: {exc}") from exc

    pipeline_section = parsed.get("pipeline", parsed)
    if not isinstance(pipeline_section, dict):
        raise ValueError("TOML 配置缺少 [pipeline] 节点。")

    settings_payload = {
        "modelPath": pipeline_section.get("model_path"),
        "targetLabels": pipeline_section.get("target_labels"),
        "confidenceThreshold": pipeline_section.get("confidence_threshold"),
        "iouThreshold": pipeline_section.get("iou_threshold"),
        "frameStride": pipeline_section.get("frame_stride"),
        "batchSize": pipeline_section.get("batch_size"),
        "useHalf": pipeline_section.get("use_half"),
    }
    return _normalize_pipeline_settings(settings_payload)


def _read_pipeline_config() -> dict:
    _ensure_pipeline_config_file()
    content = CONFIG_FILE_PATH.read_text(encoding="utf-8")
    settings_payload = _parse_pipeline_toml_content(content)
    return {
        "path": "config/pipeline_settings.toml",
        "settings": settings_payload,
        "content": content,
    }


def _write_pipeline_config(settings_payload: dict, content: str | None = None) -> dict:
    normalized = _normalize_pipeline_settings(settings_payload)
    final_content = content if content is not None else _pipeline_settings_to_toml(normalized)
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE_PATH.write_text(final_content, encoding="utf-8")
    return {
        "path": "config/pipeline_settings.toml",
        "settings": normalized,
        "content": final_content,
    }


class UploadVideoView(APIView):
    def post(self, request):
        video_file = request.FILES.get("video")
        if not video_file:
            return Response({"detail": "请上传字段名为 video 的 mp4 文件。"}, status=status.HTTP_400_BAD_REQUEST)

        if not video_file.name.lower().endswith(".mp4"):
            return Response({"detail": "当前演示版仅支持 mp4 视频。"}, status=status.HTTP_400_BAD_REQUEST)

        upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
        storage = FileSystemStorage(location=upload_dir, base_url=f"{settings.MEDIA_URL}uploads/")
        safe_name = get_valid_filename(video_file.name)
        saved_name = storage.save(safe_name, video_file)
        uploaded_url = storage.url(saved_name)

        task = Task.objects.create(
            original_filename=video_file.name,
            uploaded_video_path=uploaded_url,
            status=Task.Status.PENDING,
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskListView(APIView):
    def get(self, request):
        tasks = Task.objects.order_by("-updated_at", "-created_at", "-id")
        return Response(TaskSerializer(tasks, many=True).data)


class ProcessTaskView(APIView):
    def post(self, request, task_id):
        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            return Response({"detail": "任务不存在。"}, status=status.HTTP_404_NOT_FOUND)

        if task.status == Task.Status.PROCESSING:
            return Response(TaskSerializer(task).data)

        try:
            process_options = _parse_process_options(request.data or {})
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        start_processing(task.id, process_options)
        task.refresh_from_db()
        return Response(TaskSerializer(task).data)


class TaskDetailView(APIView):
    def get(self, request, task_id):
        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            return Response({"detail": "任务不存在。"}, status=status.HTTP_404_NOT_FOUND)

        return Response(TaskSerializer(task).data)

    def delete(self, request, task_id):
        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)

        _delete_media_file(task.uploaded_video_path)
        _delete_media_file(task.result_video_path)
        clear_runtime_progress(task.id)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, task_id):
        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            return Response({"detail": "任务不存在。"}, status=status.HTTP_404_NOT_FOUND)

        action = str(request.data.get("action") or "").strip().lower()
        if action not in TASK_MUTATION_ACTIONS:
            return Response({"detail": "不支持的任务操作。"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                result = _run_task_action(task, action, request.data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if result is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(result)


class TaskBatchActionView(APIView):
    def post(self, request):
        action = str(request.data.get("action") or "").strip().lower()
        task_ids = request.data.get("task_ids")

        if action not in TASK_MUTATION_ACTIONS:
            return Response({"detail": "不支持的批量操作。"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(task_ids, list) or not task_ids:
            return Response({"detail": "task_ids 必须是非空数组。"}, status=status.HTTP_400_BAD_REQUEST)

        normalized_ids = []
        for raw_id in task_ids:
            try:
                normalized_ids.append(int(raw_id))
            except (TypeError, ValueError):
                return Response({"detail": "task_ids 中包含非法任务编号。"}, status=status.HTTP_400_BAD_REQUEST)

        tasks = list(Task.objects.filter(pk__in=normalized_ids).order_by("-updated_at", "-created_at", "-id"))
        if len(tasks) != len(set(normalized_ids)):
            return Response({"detail": "部分任务不存在。"}, status=status.HTTP_404_NOT_FOUND)

        results = []
        try:
            with transaction.atomic():
                for task in tasks:
                    result = _run_task_action(task, action, request.data)
                    if result is not None:
                        results.append(result)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "action": action,
            "count": len(tasks),
            "tasks": results,
        })


class PipelineConfigView(APIView):
    def get(self, request):
        return Response(_read_pipeline_config())

    def put(self, request):
        if "content" in request.data:
            content = str(request.data.get("content") or "")
            try:
                settings_payload = _parse_pipeline_toml_content(content)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(_write_pipeline_config(settings_payload, content=content))

        payload = request.data.get("settings", request.data)
        try:
            settings_payload = _normalize_pipeline_settings(payload)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_write_pipeline_config(settings_payload))
