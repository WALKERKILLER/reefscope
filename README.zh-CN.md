# ReefScope

面向鱼类活动与珊瑚健康研究的水下视频分析平台。

[![CI](https://github.com/WALKERKILLER/reefscope/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/WALKERKILLER/reefscope/actions/workflows/ci.yml)

[English](README.md) · **简体中文**

ReefScope 将视频回放、鱼类检测，以及追踪、珊瑚分割和可复现评估的研究方案放在同一仓库中。项目基于 Vue 3 和 Django，使用共享数据契约支持算法与前端协作。

## 项目状态

当前应用包含视频上传、YOLO 鱼类检测、任务进度、视频回放和检测框叠加。仓库已提供 Docker 配置、CI、示例契约和手动容器发布流程。

以下能力仍在规划中：

- 具有持续轨迹 ID 的鱼类追踪，以及按停留时间加权的画面热力图。
- 珊瑚分割、专家复核的健康标签和可复现训练。
- 确定性评估与训练报告。
- 结合视频叠加的海洋监测信息大屏。

仓库不包含模型权重、视频和训练集。示例数据仅用于说明契约，项目尚未声明模型精度或珊瑚健康识别效果。当前应用用于本地研究，API 尚无认证。

## 快速开始

### 环境要求

- Python 3.12 和 [uv](https://docs.astral.sh/uv/)。
- Node.js 22 和 npm。
- 可从 `PATH` 调用的 ffmpeg。
- 已获使用授权、兼容当前 Ultralytics 固定版本的鱼类检测模型。

### 后端

```bash
git clone https://github.com/WALKERKILLER/reefscope.git
cd reefscope
uv venv --python 3.12
source .venv/bin/activate

# CPU 环境；CUDA 配置见开发指南。
uv pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install -r backend/requirements.txt
```

将模型放到 `backend/models/model_best.pt`，再启动后端：

```bash
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### 前端

打开另一个终端，从仓库根目录执行：

```bash
cd frontend
npm ci
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

访问 [localhost:5173](http://127.0.0.1:5173)，上传 MP4 视频并启动检测。健康检查地址为 [localhost:8000/api/health](http://127.0.0.1:8000/api/health)。

上述命令使用 POSIX shell。CUDA 和 Docker 配置见 [开发指南](docs/developers/development.md)。完成认证、媒体访问控制和部署加固前，请保持服务仅供本地访问。

## 开发与验证

无需 GPU 依赖即可运行仓库和示例契约检查：

```bash
python3 scripts/check.py
```

只检查后端、不执行模型推理时，可在单独的 Python 3.12 环境中安装 `backend/requirements-ci.txt`。完整命令与验证边界见 [测试说明](docs/developers/testing.md)。CI 覆盖仓库检查、Django 检查与测试、前端构建。容器发布由维护者手动触发，不会部署服务器。

## 文档

- [文档导航](docs/README.md)：全部项目文档的入口。
- [开发指南](docs/developers/README.md)：环境、架构、测试与发布。
- [MVP 研究](docs/mvp/README.md)：科研范围、数据契约与模型提案。
- [工作包](docs/mvp/10-work-packages-and-integration.md)：模块职责与集成验收。
- [里程碑](https://github.com/WALKERKILLER/reefscope/milestones)与[任务](https://github.com/WALKERKILLER/reefscope/issues?q=is%3Aissue%20is%3Aopen)：认领和评审开发工作。

项目的详细文档目前以简体中文维护。

## 参与贡献

先读 [CONTRIBUTING.md](CONTRIBUTING.md)，选择工作包，并在实施前约定输入、输出和验收条件。共享契约变更需要评审，PR 应附相关测试和验证证据。

研究结果须说明模型、数据集和评估协议。画面热图不能证明地理热点或种群数量；珊瑚标签映射须经专家复核，缺失指标须保留原因。

## 许可与来源

继承源码的授权仍待确认，因此项目尚未指定整体许可证。模型权重、数据集和第三方依赖分别遵循各自条款。再分发前请阅读 [来源与复用边界](docs/developers/provenance.md)。
