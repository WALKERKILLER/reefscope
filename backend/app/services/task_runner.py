"""后台任务执行器"""

import logging
from threading import Thread
from typing import TYPE_CHECKING

from django.utils import timezone

from app.models import Task

if TYPE_CHECKING:
    from app.services.detector import run_detection as run_detection_type

logger = logging.getLogger(__name__)
_runtime_progress = {}


def _set_runtime_progress(task_id: int, **fields) -> None:
    snapshot = _runtime_progress.get(task_id, {}).copy()
    snapshot.update({key: value for key, value in fields.items() if value is not None})
    _runtime_progress[task_id] = snapshot


def get_runtime_progress(task_id: int) -> dict:
    return _runtime_progress.get(task_id, {}).copy()


def clear_runtime_progress(task_id: int) -> None:
    _runtime_progress.pop(task_id, None)


def start_processing(task_id: int, process_options: dict | None = None) -> None:
    """启动后台检测任务"""
    _set_runtime_progress(
        task_id,
        progress=0,
        current_frame=0,
        total_frames=0,
        message="任务已启动，等待后端读取视频信息",
    )
    Task.objects.filter(pk=task_id).update(
        status=Task.Status.PROCESSING,
        progress=0,
        result_video_path="",
        detections=[],
        updated_at=timezone.now(),
    )

    worker = Thread(target=_process_task, args=(task_id, dict(process_options or {})), daemon=True)
    worker.start()


def _progress_callback(
    task_id: int,
    current: int,
    total: int,
    message: str | None = None,
    progress_override: int | None = None,
):
    """保存处理进度到数据库"""
    safe_total = max(int(total), 1)
    safe_current = min(max(int(current), 0), safe_total)
    if progress_override is None:
        progress = min(int(safe_current / safe_total * 100), 99)
    else:
        progress = min(max(int(progress_override), 0), 99)

    _set_runtime_progress(
        task_id,
        progress=progress,
        current_frame=safe_current,
        total_frames=safe_total,
        message=message or f"后端正在处理第 {safe_current}/{safe_total} 帧",
    )

    Task.objects.filter(pk=task_id).update(
        progress=progress,
        updated_at=timezone.now(),
    )


def _process_task(task_id: int, process_options: dict) -> None:
    """后台处理任务"""
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        return

    try:
        from app.services.detector import run_detection
        from django.conf import settings as dj_settings
        media_root = str(dj_settings.MEDIA_ROOT)

        cb = lambda c, t, m=None, p=None: _progress_callback(task_id, c, t, m, p)
        result = run_detection(
            task.uploaded_video_path,
            media_root,
            progress_callback=cb,
            **process_options,
        )
        total_frames = int(result.get('total_frames') or 0)
        device = str(result.get('device') or 'unknown')
        device_reason = str(result.get('device_reason') or '').strip()
        batch_size = int(result.get('batch_size') or 1)
        use_half = bool(result.get('use_half'))

        Task.objects.filter(pk=task_id).update(
            result_video_path=result['result_video_url'],
            detections=result['detections'],
            progress=100,
            status=Task.Status.COMPLETED,
            updated_at=timezone.now(),
        )
        _set_runtime_progress(
            task_id,
            progress=100,
            current_frame=total_frames,
            total_frames=total_frames,
            message=(
                f"后端处理完成，设备 {device}，batch={batch_size}，半精度 {'开启' if use_half else '关闭'}"
                + (f"。{device_reason}" if device_reason else "")
            ),
        )
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        _set_runtime_progress(
            task_id,
            message=f"后端处理失败: {e}",
        )
        Task.objects.filter(pk=task_id).update(
            status=Task.Status.FAILED, updated_at=timezone.now()
        )
