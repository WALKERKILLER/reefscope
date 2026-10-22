# 04 · MVP 交付切片、分工和验收条件

> **用户确认画面坐标热图目标**，其余架构与分工仍为**待评审候选工作项**。只列每个模块的边界与验收，不把尚未开发的功能标为完成。建议按可运行的纵向切片交付，避免四组人员各写一套服务，最后无法集成。

## 里程碑依赖

```text
M0 稳定当前系统与结果版本化（平台 / 测试）
   ├── M1 鱼类后端跟踪 + tracks.jsonl  ──┐
   └── M2 珊瑚基线 + 人工标注/微调 ───────┤
                                           ├── M3 统一前端可视化 + M4 指标/导出
                                           └── M5 跨视频质量评估 / 交付
```

### M0 · 工程基线（P0，阻塞其他开发）

**责任角色：后端/集成 A；支持：测试 E**
- 修正模型路径不一致并增加默认模型存在性测试。
- `GET /api/health` 真正返回 200，修改 Docker healthcheck。
- 新建 AnalysisRun/ModelVersion（含数据迁移），对 Run 生成 UUID 目录，避免覆盖。
- 单进程独立 Worker、DB 状态更新、心跳与安全重试；Web/API 不直接计算长任务。
- 外网部署前关闭默认 DEBUG/通配 CORS/匿名危险上传，视频内容与大小检查。
- 留住旧 upload/process/task API 的回归测试。

**验收：** 用 1 个视频创建 2 个不同 AnalysisRun；重启 web 不打断 worker；同一 Run 不会被两个 worker 并发处理；重试不覆盖前一 Run；旧接口可用；健康检查返回 200。

### M1 · 鱼类 MOT + 轨迹热图（P0）

**责任角色：CV-鱼类 B；支持：前端 D**
- 从现有 `model_best.pt` 和 detector 输入视频顺序帧；ByteTrack baseline（可选 BoT-SORT）。
- 逐帧写 `track_id`、`timestamp_ms`、bbox、观测标记，导出可分段轨迹 JSONL。
- 轨迹连接规则明确断帧阈值；导出 tracks、轨迹点列表与基于中心点停留时长的 heatmap.json。
- 测试静止/移动镜头混合；图表必须标明 image-plane 类型。

**验收：** 同一目标在至少 3 个连续有观测帧的 ID 能被 UI 关联；视频回放/前进/后退同步正确，尾迹与框同步；固定测试 fixture 的热图重复运行相同且不重复累计；有 IDF1/ID switches 的实验记录。

### M2 · 珊瑚健康分割与微调（P0，平行 M1）

**责任角色：CV-珊瑚 C；支持：数据 E**
- 构建 video/frame/annotated mask 版本化目录与元数据 manifest。
- 下载有许可的 CoralscapesV2 95 类 SegFormer 权重，生成预标注 mask/PNG overlay。
- 发布版本化 source id → six-class taxonomy 映射，不能将死骨骼等同于白化。
- 引入 CVAT 或 napari 人工修正；视频/站点级 train/val/test split。
- 训练 CLI、评估 CLI、模型版本导入；部署推理前先记录原始 baseline 与微调改善。
- 输出像素掩膜文件、每帧质量统计和样本级质量问题；无需第一版部署浏览器内训练。

**验收：** 一段测试视频输出与关键帧同步的 6 类 mask，模型 hash/标签映射可追溯；完成专家审核的独立 test set，报告每类 IoU、白化 F1/Recall 和混淆矩阵；保存 baseline vs tuned 结果。

### M3 · 前端视频分析工作台（P1，可独立使用模拟数据）

**责任角色：前端/产品 D**
- 沿用 Artplayer 和 Canvas，不替换播放器。
- `useAnalysisRun` composable 管理当前 run、轮询状态、错误和版本；渲染器按图层分组件。
- 鱼类模式支持框/track ID/尾迹/全程轨迹/热图各自开关与图例、轨迹选择、时间范围。
- 珊瑚模式支持透明度滑条、类别开关、当前帧掩膜与状态图例、视频与预测版本对比。
- 右侧统计面板用真正 summary 数据；不同模式下不同指标，不再把 detection 数叫“鱼数量”。
- 与 M1/M2 约定 `02-contracts.md`，首日就用 fixture 模拟接口做 UI。

**验收：** 不启动 GPU 模型也能加载 fixture 展示所有图层；移动播放器时间轴后叠加无错位；全屏/缩放后 bbox/mask/heatmap 坐标一致；不能加载 run 时明确提示错误状态。

### M4 · 统计、数据挖掘与导出（P1）

**责任角色：数据/科研 E**
- 指标层脱离 UI，可基于相同 tracks/masks 重算；所有分母、单位、采样 ROI、坐标空间可见。
- 鱼类轨迹分布、停留热图、样本内行为对比；统计 unique Track IDs 而非 fish population。
- 珊瑚白化比例、有效底栖 ROI 覆盖比、站点可比性约束、低质量样本警告。
- CSV + JSON 导出（包含 provenance、模型版本与 taxonomy）；图表点击定位回放时间段。

**验收：** 数据导出的指标与页面数值一致；单元测试包含零珊瑚、全 unknown、重复轨迹、移动镜头等边界；对无效分母返回 null 而不是 0 或 NaN。

### M5 · 研究复现、集成与验收（P1）

**责任角色：集成 A + 全组**
- 固定 3–5 段有差异的视频做端到端回归；每个模型有参数/版本和质量报告。
- 测试 GPU 不可用回退、ffmpeg 失败、重复 run、任务异常恢复、媒体清理、禁止路径穿越。
- 记录视频 fps/时长、帧数、抽帧率、处理时间、模型显存、网络与磁盘占用。
- 更新 README、Docker Compose、最小本地启动步骤及研究局限说明。

**验收：** 从原始 MP4 到分析 Run 完成、重放、导出整条路径可复现；CI 至少包含 Python lint/测试、前端 build、API 契约 fixture 验证、构建检查。

## 建议的团队边界（4–5 人）

| 角色 | 修改路径主要所有权 | 给下游交付 | 依赖 |
| --- | --- | --- | --- |
| A 后端/集成 | `backend/app/models*,api/,management/,storage.py` | AnalysisRun API + Worker + artifact 路径 | 最早启动 |
| B 目标检测/MOT | `backend/app/analysis/fish.py,tracking.py` | `fish-tracks/v1`, `fish-heatmap/v1` | M0 数据契约（可先用接口模拟） |
| C 珊瑚分割/训练 | `backend/app/analysis/coral.py,taxonomy.py`, `backend/ml/` | `coral-health/v1`, model registry | M0 数据契约（可先独立训练） |
| D 前端与体验 | `frontend/src/components/overlays/,analysis/`, `composables/` | 视频/图表/图层/时间线 | 依赖契约，不必等 GPU |
| E 科研质量/数据 | `backend/app/analysis/metrics.py`，dataset manifests，测试与报告 | 质量阈值、数据划分、指标重算 | B/C 输出格式 |

仅 3 人时：A 兼 E、B 兼 D，C 独立；不必为每个技术名称再设一个负责人。

## 变更约束与合入

- P0 优先只改稳定的数据契约与公共接口，其他成员用 fixture 并行开发；避免同改 `App.vue` 或原 `detector.py`。
- 推荐 PR 顺序：`fix: stabilize analysis baseline` → `feat: persist analysis runs` → `feat: track fish motion` / `feat: segment coral health` → `feat: visualize marine analysis` → `feat: export ecological metrics`。
- PR 标题 Conventional Commits 英文，body 中文（动机、实现、验收、风险与截图/数据）；无需 co-author。
- 每个 PR 必须写明 `scope`、对应 schema version、兼容影响、测试、前后对比、预计计算资源；不让训练模型权重被误提交到 Git（只登记 sha 和访问方式）。


## 细化执行包（现行）

拆 issue 与 PR 按 [10-work-packages-and-integration.md](10-work-packages-and-integration.md) 的 PKG-00..08，追踪热图的原始计算按 [08-video-heatmap-and-datamining.md](08-video-heatmap-and-datamining.md)，珊瑚训练评估按 [07-coral-training-blueprint.md](07-coral-training-blueprint.md)，开源引入的许可证核查按 [06-open-source-adoption.md](06-open-source-adoption.md)。不以尚未经过专家/本地样本测试的论文 mIoU 作为产品验收指标。


## 2026-10-21 MVP v2 新增工作包

量化训练效果、VLM 辅助标注、海洋信息大屏现已纳入端到端里程碑。拆分见 [15-mvp-v2-milestones.md](15-mvp-v2-milestones.md) M0–M6。尤其注意：
- PKG-09 deterministic EvalRunner (fish/MOT/coral)，不可直接由 AI 摘要生成数值；
- PKG-10 TrainingReport 7 章节 + 可追溯 version/hash/test protocol + PDF/Markdown；
- PKG-11 opt-in VLM 预标注/数据导入/人工审核 PoC，阻塞条件为模型权重许可/GPU；
- PKG-12 Vue3 Ocean Wall 3 页面，主视频居中、研究指标独立可信、ECharts/DataV 按需。
