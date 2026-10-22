# 本地开发

## 无 GPU 检查

先执行根 README 中的基础检查。`requirements-ci.txt` 只安装 Web 层，不能执行 YOLO 推理。

## 原应用运行

后端要求 Python 3.12。用 `uv venv --python 3.12` 创建环境，激活后按硬件安装 PyTorch，再装旧项目依赖。

```bash
uv pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
uv pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

CPU 环境将上述索引换成 `https://download.pytorch.org/whl/cpu`。取得有授权的鱼类权重，放到 `backend/models/model_best.pt`，记录来源、许可和 SHA256 到团队受控存储。后端另需 ffmpeg；不要执行来源不明的权重文件。

在另一个终端启动前端：

```bash
cd frontend
npm ci
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

访问 `http://127.0.0.1:5173`。Vite 当前没有代理配置，因此分离开发必须显式设置 API 地址。模型路径配置相对后端目录解析，启动前检查设置面板。

## 本地容器演示

先准备权重与数据库文件，再执行 Compose。迁移创建的数据库会作为文件挂载，不能让 Docker 自动创建同名目录。

```bash
.venv/bin/python backend/manage.py migrate
docker compose build
docker compose up -d
```

前端访问 `http://127.0.0.1:18080`；健康检查 `http://127.0.0.1:8000/api/health`。Compose 的 CUDA 镜像要求 NVIDIA Container Toolkit 与 GPU，CPU 开发优先使用前后端分离方式。权重以只读目录挂载，不进入镜像。

当前 API 和媒体访问缺少认证，且保留演示安全配置。保持回环绑定；公网试用必须先完成 [发布前审查](release.md)。
