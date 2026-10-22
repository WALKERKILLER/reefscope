FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

WORKDIR /app

# 安装系统依赖（OpenCV + ffmpeg H.264 编码）
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/requirements.txt .
RUN python -m pip install --no-cache-dir uv \
    && uv pip install --system --no-cache-dir \
    torch==2.5.1 torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cu124 \
    && uv pip install --system --no-cache-dir -r requirements.txt

# === CUDA 加速说明 ===
# 当前镜像默认包含 CUDA 12.4 运行时，适合直接挂载 NVIDIA GPU。
# 如果只想构建纯 CPU 版，可改回 python:3.12-slim，并移除上面的 CUDA torch 安装。

# 复制项目代码
COPY backend/ .

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings
ENV YOLO_DEVICE=cuda:0
ENV SKIP_PYTHON_VERSION_CHECK=1

# 收集静态文件
RUN python manage.py collectstatic --noinput --skip-checks

# 确保 media 目录存在
RUN mkdir -p /app/media

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 现有进程内任务状态要求单进程；独立 Worker 完成后再扩展。
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
