# 00 · 代码现状审计（基于主分支 dd39fcd）

## 已核实的依赖与链路

- 前端 Vue 3 / Vite / Tailwind 4、Artplayer：`frontend/package.json`、`frontend/src/components/VideoWorkspace.vue:160-260`。
- API 封装为 `frontend/src/api.js:11-49` 的 upload/process/task/tasks/config 等请求；容器的 Nginx 转发 `/api/` 和 `/media/`，见 `frontend/Dockerfile:31-56`。
- Django/DRF 入口 `backend/app/urls.py:5-12`：上传、触发处理、轮询、批量操作、配置。上传仅允许扩展名 .mp4，见 `backend/app/views.py:361-381`。
- 单个 `Task` 记录文件路径、status、detections JSON 和 progress，见 `backend/app/models.py:4-25`。
- `start_processing()` 每次启新 daemon Thread，运行中进度在 Python 进程字典并同步部分字段到 DB，见 `backend/app/services/task_runner.py:15-50,82-131`。
- YOLO 使用 `model.predict` 批推理：每 `frame_stride` 帧推断一次，存归一化矩形坐标、置信度、timestamp，见 `backend/app/services/detector.py:387-585`。回放结果另渲染 MP4、ffmpeg 转码。
- 前端 `buildTracks()` 通过类别、IoU 和中心点距离自行贪心匹配，只用于画框插值，没有服务端 Track ID，见 `VideoWorkspace.vue:431-646`。
- `RightPanel.vue:99-105` 的 counts 是对全部 detection 逐条累加，不是独立鱼数。
- `App.vue` 约 982 行、`VideoWorkspace.vue` 约 1119 行；模块化可从新功能拆分入手，不必先重写 UI。

## 需修正的风险（按优先级）

| 优先级 | 发现 | 证据 / 影响 | 处理策略 |
| --- | --- | --- | --- |
| P0 | 配置文件 model_path=`models/best.pt`，提交权重为 `models/model_best.pt` | `backend/config/pipeline_settings.toml:2` 与 `backend/models/model_best.pt`；手动应用配置可能报路径不存在 | 修正默认配置与路径校验，并做回归测试 |
| P0 | 服务端线程不是可靠的队列 | `task_runner.py:49`，容器 `Dockerfile:47` 两个 Gunicorn worker；进度字典彼此不共享，重启会中断任务 | 以独立单 Worker + DB 状态/心跳/可恢复分析 Run 替代 |
| P0 | 未认证 API 与演示级默认安全配置 | `settings.py:6-8,72-77`，DEBUG 默认 true、ALLOW_HOSTS '*'、开发 CORS 可放开，上传只检扩展名 | 外网部署前增上传大小/格式/访问控制、关闭 DEBUG/CORS 通配 |
| P0 | 现有检测结果无法表达真实跨帧身份 | `detector.py:476-520` 不调用 track；`RightPanel.vue:99-105` 是逐帧计数 | 后端新增 track_id、trajectory_points、ID 质量评估 |
| P1 | 结果保存在 Task.detections 单列 JSON 内 | `models.py:14`；视频多帧/多模型结果可能膨胀，无法分页 | DB 保存 Run 元数据+摘要；轨迹用分块 JSONL，掩膜/热图用文件 |
| P1 | 视频结果名称 `result_<stem>.mp4`，重跑可能覆盖 | `detector.py:451-457`，按输入 stem 命名 | 每次 Run 建立唯一 artifact 目录，记录 schema/model version |
| P1 | Dockerfile 健康检查 GET `/api/upload` 但 View 只实现 POST | `Dockerfile:43-44` vs `views.py:361-381`，预计返回 405，容器被标不健康 | 专设 GET `/api/health` |
| P1 | `frame_stride=5` 默认适合检测抽样但不适合快速鱼类追踪 | `views.py:24`；快速运动下的 ID switch/轨迹断裂 | 追踪默认 stride=1；性能不足时显式降帧及记采样间隔 |
| P1 | README 宣称 YOLO26/v8，实际 `ultralytics==8.3.109` 且无系统训练 API | `backend/requirements.txt` 与 `README.md` | 先确认依赖锁与模型兼容，再引入可复现训练 CLI |
| P1 | 缺少真实测试、分层 API 契约、模型与数据版本记录 | 仓库无 tests、无模型注册表、任务只保存文件路径 | 新增契约 fixture、单元/集成/smoke 测试，保存模型 hash |
| P2 | 前端状态与 Canvas 渲染高度集中 | `App.vue`、`VideoWorkspace.vue` | 只抽取新增 composable/overlay renderer，不整体重构 |
| P2 | 监控台占位与状态栏硬编码 | `MonitorView.vue` 以及 `App.vue:225-240` | MVP 不做实时远程相机；隐藏假延迟等统计 |

## 目前测试状态

本页记录历史静态审计，未完成真实 GPU 推理验证。运行要求以当前开发文档为准；本页的行号和风险描述对应旧快照，不能当作当前版本的验证结果。

## 保留的旧接口

`POST /api/upload`、`POST /api/process/{task_id}`、`GET /api/task/{task_id}`、`GET /api/tasks`、`DELETE /api/task/{task_id}` 暂不破坏。新架构通过版本化 `/api/v1/analysis-...` 接口新增行为；最终可将旧接口实现委派到新服务。
