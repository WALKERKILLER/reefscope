"""YOLO 目标检测服务 - 使用 ultralytics YOLOv8 进行鱼类检测"""

import os
import subprocess
from functools import lru_cache
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import cv2
import torch
from django.conf import settings
from ultralytics import YOLO

_model_cache = {}


BOX_COLOR = (246, 210, 133)
TEXT_COLOR = (72, 53, 0)
TEXT_BG_COLOR = (246, 210, 133)


def _resolve_annotation_style(frame) -> dict:
    min_side = max(1, min(frame.shape[0], frame.shape[1]))
    scale_factor = max(1.0, min_side / 1080)
    font_scale = min(1.55, max(0.78, 0.82 * scale_factor))
    text_thickness = max(2, int(round(1.8 * scale_factor)))
    box_thickness = max(3, int(round(3 * scale_factor)))
    horizontal_padding = max(7, int(round(8 * scale_factor)))
    vertical_padding = max(5, int(round(6 * scale_factor)))
    label_gap = max(8, int(round(10 * scale_factor)))

    return {
        "font_scale": font_scale,
        "text_thickness": text_thickness,
        "box_thickness": box_thickness,
        "horizontal_padding": horizontal_padding,
        "vertical_padding": vertical_padding,
        "label_gap": label_gap,
    }


def _build_video_writer(result_path: Path, fps: float, width: int, height: int) -> cv2.VideoWriter:
    safe_fps = float(fps) if fps and fps > 0 else 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(result_path), fourcc, safe_fps, (int(width), int(height)))
    if not writer.isOpened():
        raise ValueError(f"无法创建结果视频: {result_path}")
    return writer


@lru_cache(maxsize=1)
def _ffmpeg_encoder_supported(encoder_name: str) -> bool:
    try:
        probe = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    return encoder_name in f"{probe.stdout}\n{probe.stderr}"


def _build_ffmpeg_command(temp_result_path: Path, final_result_path: Path, encoder_name: str) -> list[str]:
    input_args = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(temp_result_path),
    ]
    output_args = [
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(final_result_path),
    ]

    if encoder_name == "h264_nvenc":
        return [
            *input_args,
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",
            "-rc",
            "vbr",
            "-cq",
            "23",
            *output_args,
        ]

    return [
        *input_args,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        *output_args,
    ]


def _transcode_video_for_web(temp_result_path: Path, final_result_path: Path, prefer_gpu: bool = True) -> str:
    requested_encoder = str(os.getenv("YOLO_VIDEO_ENCODER", "auto")).strip().lower()
    encoder_candidates = ["libx264"]

    if requested_encoder == "h264_nvenc":
        encoder_candidates = ["h264_nvenc", "libx264"]
    elif requested_encoder == "libx264":
        encoder_candidates = ["libx264"]
    elif prefer_gpu and _ffmpeg_encoder_supported("h264_nvenc"):
        encoder_candidates = ["h264_nvenc", "libx264"]

    last_error = None
    for encoder_name in encoder_candidates:
        command = _build_ffmpeg_command(temp_result_path, final_result_path, encoder_name)
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return encoder_name
        except FileNotFoundError as exc:
            raise ValueError("未找到 ffmpeg，无法生成浏览器可播放的结果视频。") from exc
        except subprocess.CalledProcessError as exc:
            last_error = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            if encoder_name == "h264_nvenc":
                continue

    raise ValueError(f"ffmpeg 转码失败: {last_error or '未知错误'}")


def _draw_boxes_on_frame(frame, detections: list[dict]) -> None:
    style = _resolve_annotation_style(frame)

    for detection in detections:
        x = int(round(float(detection.get("x", 0)) * frame.shape[1]))
        y = int(round(float(detection.get("y", 0)) * frame.shape[0]))
        w = int(round(float(detection.get("width", 0)) * frame.shape[1]))
        h = int(round(float(detection.get("height", 0)) * frame.shape[0]))
        confidence = float(detection.get("confidence", 0))
        label = str(detection.get("label") or "fish")
        label_text = f"{label} {confidence * 100:.1f}%"

        x1 = max(0, min(frame.shape[1] - 1, x))
        y1 = max(0, min(frame.shape[0] - 1, y))
        x2 = max(x1 + 1, min(frame.shape[1], x + w))
        y2 = max(y1 + 1, min(frame.shape[0], y + h))

        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, style["box_thickness"])

        (text_width, text_height), baseline = cv2.getTextSize(
            label_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            style["font_scale"],
            style["text_thickness"],
        )
        text_x1 = x1
        text_y1 = max(0, y1 - text_height - baseline - style["label_gap"])
        text_x2 = min(frame.shape[1], text_x1 + text_width + style["horizontal_padding"] * 2)
        text_y2 = min(frame.shape[0], text_y1 + text_height + baseline + style["vertical_padding"] * 2)

        cv2.rectangle(frame, (text_x1, text_y1), (text_x2, text_y2), TEXT_BG_COLOR, -1)
        cv2.putText(
            frame,
            label_text,
            (text_x1 + style["horizontal_padding"], text_y2 - baseline - style["vertical_padding"]),
            cv2.FONT_HERSHEY_SIMPLEX,
            style["font_scale"],
            TEXT_COLOR,
            style["text_thickness"],
            cv2.LINE_AA,
        )


def _render_result_video(
    absolute_video_path: str,
    result_path: Path,
    fps: float,
    width: int,
    height: int,
    detections_by_frame: dict[int, list[dict]],
    progress_callback=None,
    total_frames: int = 0,
) -> None:
    render_cap = cv2.VideoCapture(absolute_video_path)
    if not render_cap.isOpened():
        raise ValueError(f"无法重新打开视频文件: {absolute_video_path}")

    if result_path.exists():
        result_path.unlink()

    temp_result_path = result_path.parent / f"{result_path.stem}_raw_{uuid4().hex}.mp4"
    if temp_result_path.exists():
        temp_result_path.unlink()

    writer = _build_video_writer(temp_result_path, fps, width, height)
    frame_index = 0

    try:
        while render_cap.isOpened():
            ret, frame = render_cap.read()
            if not ret:
                break

            frame_detections = detections_by_frame.get(frame_index)
            if frame_detections:
                _draw_boxes_on_frame(frame, frame_detections)

            writer.write(frame)
            frame_index += 1
            if progress_callback and total_frames > 0 and frame_index % 30 == 0:
                export_ratio = frame_index / total_frames
                export_progress = min(99, 90 + int(export_ratio * 9))
                progress_callback(
                    frame_index,
                    total_frames,
                    f"正在写出 YOLO 输出视频，第 {frame_index}/{total_frames} 帧",
                    export_progress,
                )
    finally:
        render_cap.release()
        writer.release()

    if not temp_result_path.exists() or temp_result_path.stat().st_size < 1024:
        if temp_result_path.exists():
            temp_result_path.unlink()
        raise ValueError(f"结果视频中间文件生成失败: {temp_result_path}")

    try:
        if progress_callback and total_frames > 0:
            progress_callback(
                total_frames,
                total_frames,
                "正在将结果视频转为浏览器可播放格式",
                99,
            )
        encoder_name = _transcode_video_for_web(temp_result_path, result_path)
        if progress_callback and total_frames > 0:
            progress_callback(
                total_frames,
                total_frames,
                f"结果视频已使用 {encoder_name} 编码完成",
                99,
            )
    finally:
        if temp_result_path.exists():
            temp_result_path.unlink()


def _resolve_model_path(model_path: str) -> str:
    normalized = str(model_path or "").strip()
    if not normalized:
        raise ValueError("未提供模型权重路径。")

    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = (Path(settings.BASE_DIR) / candidate).resolve()

    if not candidate.exists():
        raise ValueError(f"模型文件不存在: {model_path}")

    return str(candidate)


def _collect_cuda_diagnostics() -> dict:
    torch_version = str(getattr(torch, "__version__", "unknown"))
    cuda_runtime = getattr(torch.version, "cuda", None)
    cuda_available = bool(torch.cuda.is_available())
    diagnostics = {
        "torch_version": torch_version,
        "torch_cuda_runtime": str(cuda_runtime or "none"),
        "cuda_available": cuda_available,
        "cuda_device_count": 0,
        "cuda_device_name": "",
    }

    if cuda_available:
        try:
            diagnostics["cuda_device_count"] = int(torch.cuda.device_count())
        except Exception:
            diagnostics["cuda_device_count"] = 0

        if diagnostics["cuda_device_count"] > 0:
            try:
                diagnostics["cuda_device_name"] = str(torch.cuda.get_device_name(0))
            except Exception:
                diagnostics["cuda_device_name"] = ""

    return diagnostics


def _resolve_inference_device() -> tuple[str, str, dict]:
    requested_device = str(os.getenv("YOLO_DEVICE", "cuda:0")).strip() or "cuda:0"
    diagnostics = _collect_cuda_diagnostics()

    if requested_device.startswith("cuda") and not diagnostics["cuda_available"]:
        reason = (
            f"请求设备 {requested_device}，但 torch.cuda.is_available()=False，"
            f"当前 torch={diagnostics['torch_version']}，"
            f"torch.version.cuda={diagnostics['torch_cuda_runtime']}，已回退到 cpu"
        )
        return "cpu", reason, diagnostics

    if requested_device.startswith("cuda"):
        device_name = diagnostics["cuda_device_name"] or requested_device
        reason = (
            f"已启用 {requested_device}，设备 {device_name}，"
            f"torch={diagnostics['torch_version']}，"
            f"torch.version.cuda={diagnostics['torch_cuda_runtime']}"
        )
        return requested_device, reason, diagnostics

    return requested_device, f"当前按配置使用 {requested_device} 推理", diagnostics


def _resolve_use_half(device: str, use_half: bool | None) -> bool:
    if use_half is None:
        raw_value = str(os.getenv("YOLO_USE_HALF", "true")).strip().lower()
        use_half = raw_value not in {"0", "false", "no", "off"}

    return bool(use_half) and device.startswith("cuda")


def get_model(model_path: str, device: str):
    """获取或初始化 YOLO 模型"""
    resolved_path = _resolve_model_path(model_path)
    cache_key = (resolved_path, device)
    if cache_key not in _model_cache:
        model = YOLO(resolved_path)
        model.to(device)
        if device.startswith("cuda"):
            try:
                model.fuse()
            except Exception:
                pass
        _model_cache[cache_key] = model
    return _model_cache[cache_key]


def _build_label_lookup(model) -> dict:
    names = getattr(model, "names", {})
    if isinstance(names, dict):
        return {int(idx): str(name) for idx, name in names.items()}
    return {idx: str(name) for idx, name in enumerate(names)}


def _resolve_target_class_ids(model, target_labels: list[str]) -> list[int]:
    label_lookup = _build_label_lookup(model)
    normalized_lookup = {
        label.lower(): class_id
        for class_id, label in label_lookup.items()
    }

    class_ids = []
    missing_labels = []
    for raw_label in target_labels:
        normalized = raw_label.strip().lower()
        if not normalized:
            continue
        class_id = normalized_lookup.get(normalized)
        if class_id is None:
            missing_labels.append(raw_label)
        else:
            class_ids.append(class_id)

    if missing_labels:
        available_labels = ", ".join(label_lookup.values()) or "无可用类别"
        raise ValueError(f"模型类别中未找到: {', '.join(missing_labels)}。当前可用类别: {available_labels}")

    return sorted(set(class_ids))


def run_detection(
    input_video_path: str,
    media_root: str,
    progress_callback=None,
    model_path: str = "",
    target_labels: list[str] | None = None,
    confidence_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    frame_stride: int = 5,
    batch_size: int = 8,
    use_half: bool | None = None,
) -> dict:
    """
    对输入视频执行 YOLO 目标检测

    Args:
        input_video_path: 上传视频的相对 URL 路径（如 /media/uploads/xxx.mp4）
        media_root: MEDIA_ROOT 绝对路径
        progress_callback: 进度回调函数，接收参数 (current, total)

    Returns:
        dict: {
            'result_video_url': str,  # 结果视频的相对 URL 路径
            'detections': [检测结果列表]
        }
    """
    device, device_reason, device_diagnostics = _resolve_inference_device()
    use_half = _resolve_use_half(device, use_half)
    model = get_model(model_path, device)
    label_lookup = _build_label_lookup(model)
    target_class_ids = _resolve_target_class_ids(model, target_labels or ["fish"])
    frame_stride = max(int(frame_stride), 1)
    batch_size = max(int(batch_size), 1)

    if device.startswith("cuda"):
        torch.backends.cudnn.benchmark = True
        try:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        except Exception:
            pass

    # 将媒体 URL 路径转换为绝对文件路径
    if input_video_path.startswith(settings.MEDIA_URL):
        relative_path = input_video_path.replace(settings.MEDIA_URL, "", 1)
        absolute_video_path = str(Path(media_root) / relative_path)
    else:
        absolute_video_path = input_video_path

    # 打开视频
    cap = cv2.VideoCapture(absolute_video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {absolute_video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sample_interval_seconds = frame_stride / fps if fps and fps > 0 else 0

    if total_frames == 0:
        cap.release()
        raise ValueError("无法读取视频文件（帧数为 0）")

    # 准备输出视频
    input_path = Path(absolute_video_path)
    result_filename = f"result_{input_path.stem}.mp4"
    result_dir = Path(media_root) / 'results'
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / result_filename

    all_detections = []
    detections_by_frame: dict[int, list[dict]] = defaultdict(list)
    frame_count = 0
    pending_frames = []
    pending_indices = []

    if progress_callback:
        progress_callback(
            0,
            total_frames,
            f"已加载模型。{device_reason}，批量大小 {batch_size}，半精度 {'开启' if use_half else '关闭'}",
            0,
        )

    def flush_batch() -> None:
        if not pending_frames:
            return

        results = model.predict(
            pending_frames,
            verbose=False,
            conf=confidence_threshold,
            iou=iou_threshold,
            classes=target_class_ids,
            device=device,
            half=use_half,
            batch=batch_size,
        )

        for frame_index, result in zip(pending_indices, results):
            if result.boxes is None:
                continue

            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = label_lookup.get(cls_id, f'class_{cls_id}')

                norm_x = x1 / width
                norm_y = y1 / height
                norm_w = (x2 - x1) / width
                norm_h = (y2 - y1) / height
                time_sec = frame_index / fps

                detection = {
                    'frame': frame_index,
                    'label': label,
                    'confidence': round(conf, 4),
                    'x': round(norm_x, 4),
                    'y': round(norm_y, 4),
                    'width': round(norm_w, 4),
                    'height': round(norm_h, 4),
                    'timestamp': round(time_sec, 4),
                    'start_time': round(time_sec, 2),
                    'end_time': round(time_sec + sample_interval_seconds, 2),
                    'sample_interval_seconds': round(sample_interval_seconds, 4),
                    'frame_stride': frame_stride,
                    'fps': round(fps, 4) if fps else 0,
                }
                all_detections.append(detection)
                detections_by_frame[frame_index].append(detection)

        if progress_callback:
            last_processed_frame = min(pending_indices[-1] + 1, total_frames)
            inference_ratio = last_processed_frame / total_frames if total_frames > 0 else 0
            inference_progress = min(89, int(inference_ratio * 89))
            progress_callback(
                last_processed_frame,
                total_frames,
                f"后端正在使用 {device} 批量推理，第 {last_processed_frame}/{total_frames} 帧",
                inference_progress,
            )

        pending_frames.clear()
        pending_indices.clear()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 按抽帧间隔处理，兼顾实时性和吞吐
        if frame_count % frame_stride == 0:
            pending_frames.append(frame)
            pending_indices.append(frame_count)
            if len(pending_frames) >= batch_size:
                flush_batch()

        frame_count += 1

    cap.release()
    flush_batch()

    # 最终进度回调
    if progress_callback:
        progress_callback(
            total_frames,
            total_frames,
            f"推理完成，开始生成 YOLO 输出视频（设备 {device}）",
            90,
        )

    _render_result_video(
        absolute_video_path=absolute_video_path,
        result_path=result_path,
        fps=fps,
        width=width,
        height=height,
        detections_by_frame=detections_by_frame,
        progress_callback=progress_callback,
        total_frames=total_frames,
    )

    return {
        'result_video_url': f'/media/results/{result_filename}',
        'detections': all_detections,
        'total_frames': total_frames,
        'device': device,
        'device_reason': device_reason,
        'device_diagnostics': device_diagnostics,
        'frame_stride': frame_stride,
        'fps': round(fps, 4) if fps else 0,
        'sample_interval_seconds': round(sample_interval_seconds, 4),
        'batch_size': batch_size,
        'use_half': use_half,
    }
