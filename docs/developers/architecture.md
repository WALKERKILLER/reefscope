# 当前架构与改动位置

## 已有行为

前端通过 `frontend/src/api.js` 上传视频，Django 的 `UploadVideoView` 创建 `Task`。`FishAnalysisPanel.vue` 通过 v1 API 管理 Run、窗口、图层和导出，`VideoWorkspace.vue` 复用 Artplayer 与 Canvas 展示服务端轨迹和热图。旧 `ProcessTaskView` / `start_processing()` 检测接口继续保留，其线程进度仍依赖进程字典。

鱼类 v1 API 创建 `AnalysisRun`，注册的 `ModelVersion` 保存权重谱系。独立 `run_analysis_worker` 用数据库条件更新领取 Run；`app/analysis/fish.py` 顺序追踪，`storage.py` 管私有产物。此路径不使用旧 daemon Thread，运行方法见 [鱼类 Worker](fish-analysis.md)。

## 目录责任

- A 平台：`backend/config/`、`backend/app/views.py`、数据模型、迁移、任务调度、容器与 CI。
- B 鱼类：`backend/app/services/detector.py` 及未来 tracking/heatmap 模块；不得把前端插值 ID 当真实追踪。
- C 珊瑚：后续新增离线训练和分割适配器，当前尚无实现目录。
- D 前端：`frontend/src/`，Vue 与 Artplayer；视觉令牌和基础组件遵循 [前端设计系统](frontend.md)。
- E 评估：`fixtures/mvp/`、评测契约及后续确定性报告；公共字段变动与 A/C/B 联审。
- 维护者：`scripts/`、`tests/`、`.github/` 和文档路由。

## 设计边界

本次基础修正统一默认模型路径、加入只读健康检查并限制 Gunicorn 为一个进程。单进程不能解决重启丢任务和重复处理，v1 Run 使用独立 Worker、租约和 attempt token，旧检测路径仍有上述限制。

新模块按 [MVP 架构](../mvp/01-architecture.md) 和 [工作包](../mvp/10-work-packages-and-integration.md) 逐步加入。尚未创建空壳 API 或假训练服务。旧的上传、处理、查询和配置接口继续保留。
