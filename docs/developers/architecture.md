# 当前架构与改动位置

## 已有行为

前端通过 `frontend/src/api.js` 上传视频，Django 的 `UploadVideoView` 创建 `Task`。`ProcessTaskView` 触发 `start_processing()`，后台线程调用 `run_detection()`。任务状态写入 SQLite，进度还依赖进程内字典。前端轮询任务并由 Artplayer 与 Canvas 展示结果。

此处描述的是已读取的源码路径，完整模型推理尚需授权权重和真实样片验证。

## 目录责任

- A 平台：`backend/config/`、`backend/app/views.py`、数据模型、迁移、任务调度、容器与 CI。
- B 鱼类：`backend/app/services/detector.py` 及未来 tracking/heatmap 模块；不得把前端插值 ID 当真实追踪。
- C 珊瑚：后续新增离线训练和分割适配器，当前尚无实现目录。
- D 前端：`frontend/src/`，沿用 Vue、Artplayer 与现有视觉体系。
- E 评估：`fixtures/mvp/`、评测契约及后续确定性报告；公共字段变动与 A/C/B 联审。
- 维护者：`scripts/`、`tests/`、`.github/` 和文档路由。

## 设计边界

本次基础修正统一默认模型路径、加入只读健康检查并限制 Gunicorn 为一个进程。单进程不能解决重启丢任务和重复处理，可靠 Worker 仍由 M0 交付。

新模块按 [MVP 架构](../mvp/01-architecture.md) 和 [工作包](../mvp/10-work-packages-and-integration.md) 逐步加入。尚未创建空壳 API 或假训练服务。旧的上传、处理、查询和配置接口继续保留。
