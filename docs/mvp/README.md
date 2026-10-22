# SITP 水下生态监测平台 · MVP 设计提案

> 状态：**架构待团队评审**；已确认鱼活动热图采用 image_plane，最终展示目标为海洋信息大屏。本目录记录基于 `main@dd39fcd` 的代码审计和可分工架构，不代表用户已确认，也不意味着功能已经实现。
>
> 面向：已有鱼类 YOLO 检测演示；希望增加多目标追踪/运动轨迹/热力图、珊瑚健康分割、训练与实验管理、生态可视化和数据挖掘。

## 从哪里开始

1. [00-repo-audit.md](00-repo-audit.md)：代码和环境证据，已知问题、风险及优先级。
2. [01-architecture.md](01-architecture.md)：模块化单体 MVP 架构、运行链路、部署边界、UI 布局。
3. [02-contracts.md](02-contracts.md)：最小数据模型、API 草案、轨迹/掩膜标准。
4. [03-ml-evaluation.md](03-ml-evaluation.md)：鱼类追踪与珊瑚分类的现成模型、数据集、训练流程和评估指标。
5. [04-backlog.md](04-backlog.md)：里程碑、并行分工、DoD/验收条件及风险。
6. [05-vibe-wise-checkpoints.md](05-vibe-wise-checkpoints.md)：依据 vibe-wise Learn 工作流提出的设计检查点，保留待用户决定项。
7. [architecture.mmd](architecture.mmd)：Mermaid 架构图；GitHub 支持预览。
8. [architecture.drawio](architecture.drawio)：可编辑的 diagrams.net 架构源文件。
9. [../../fixtures/mvp/](../../fixtures/mvp/)：前后端并行开发用的示例 Run / Track / Heatmap / Taxonomy 数据；运行 `python3 docs/mvp/validate_fixtures.py` 验证。

## 已确认的用户需求（2026-10-21 更新）

- **鱼类活动热图：画面坐标 image_plane，ACCEPTED。** 按真实轨迹观测累计 track-seconds，不是海底地理分布。详见 [08-video-heatmap-and-datamining.md](08-video-heatmap-and-datamining.md) 与 [09-architecture-decisions.md](09-architecture-decisions.md)。
- **珊瑚**：CoralscapesV2 SegFormer 95 有效类但含 96 logits，ID0=void，来源和训练方案见 [07-coral-training-blueprint.md](07-coral-training-blueprint.md)。其余提案仍待评审。新增目标：训练效果必须有独立基线量化报告（不能只是 AI 文案），数据展示最终是海洋生态信息大屏，而非普通管理后台。

## 推荐 MVP 最短闭环

**视频上传 → 选择分析类型 → 独立工作进程分析 → 保存版本化结构化结果 → 视频叠加/轨迹/热力图/珊瑚掩膜 → 分析摘要与导出**。

- 鱼类：YOLO 原有权重 + ByteTrack / BoT-SORT（连续帧追踪）；可计算轨迹中心点、停留/占据热力图、Track 数，不能把 Track 数无条件当作生物个体数量。
- 珊瑚：先用现成 **CoralscapesV2 SegFormer-B5 95 类**推理，再由专家修正小批量标注微调，建立健康/白化/死亡/藻类覆盖/未知等类别映射。
- 平台：保持 Vue/Django/SQLite+文件存储的模块化单体；把不可恢复线程替换为**一个独立 DB 驱动的 Worker 进程**；高并发时再升级 Redis/Celery，不先微服务化。
- 研究边界：镜头移动导致的二维热力图只代表**画面坐标**，不能假装是海底地理热点；相邻视频帧的白化像素比例不能直接视为真实样方面积比例。

## 边界和确认

不修改已有生产推理与上传流程；本分支只提交架构、数据契约和分工规划。具体实现应在团队就关键设计决策达成一致后，按 backlog 小 PR 分批合入。

资源：
- 旧项目：受限来源，公开仓库仅记录版本；见 [来源与许可](../developers/provenance.md)。
- VibeWise：https://github.com/nykooi1/vibe-wise （已读 `skills/learn/SKILL.md`、`behavior.md`）
- Ultralytics Track：https://docs.ultralytics.com/modes/track/
- CoralscapesV2：https://josauder.github.io/coralscapesv2/
- 预训练权重：https://huggingface.co/EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class

## 扩充的架构/调研资料导航

- [06-open-source-adoption.md](06-open-source-adoption.md)：开源组件复用、替代方案、许可证/依赖治理。
- [07-coral-training-blueprint.md](07-coral-training-blueprint.md)：珊瑚数据集、预训练权重、95→6 映射、专家复核与消融实验。
- [08-video-heatmap-and-datamining.md](08-video-heatmap-and-datamining.md)：已确认的画面活动热图公式/前端叠加/生态挖掘。
- [09-architecture-decisions.md](09-architecture-decisions.md)：已确认/待确认的架构 ADR。
- [10-work-packages-and-integration.md](10-work-packages-and-integration.md)：团队并行分工与每个阶段的验收清单。
- [11-sources.md](11-sources.md)：官方开源项目/论文/模型/数据集资料索引。


## 第三轮新增（2026-10-21）

- [12-training-report-and-benchmark.md](12-training-report-and-benchmark.md)：YOLO Report Analyst 启发的七章报告、真实 fish/MOT/coral 评测、TrainingRun / EvaluationRun / TrainingReport 契约与科学正确性门禁。
- [13-vlm-autoyolo-integration.md](13-vlm-autoyolo-integration.md)：VLM-AutoYOLO 能力/许可/GPU 边界，视频关键帧、自动标注、人工复核、跨平台导入及效率 A/B PoC。
- [14-visual-wall-research-and-spec.md](14-visual-wall-research-and-spec.md)：ECharts、VChart、DataV-Vue3、IofTV、DataRoom、GoView、旧 Vue 大屏的流行度/维护/栈/许可对比；深海大屏布局、设计 tokens、性能与科学文案规范。
- [15-mvp-v2-milestones.md](15-mvp-v2-milestones.md)：M0–M6 里程碑和跨组可拆 PR 工作包。
- 新增 [../../fixtures/mvp/training-report.sample.json](../../fixtures/mvp/training-report.sample.json)、[../../fixtures/mvp/auto-annotation.sample.json](../../fixtures/mvp/auto-annotation.sample.json)、[../../fixtures/mvp/wall-view.sample.json](../../fixtures/mvp/wall-view.sample.json) 供集成契约测试。**样例不含真实评测结果。**

新增开源资料统一索引：[11-sources.md](11-sources.md) S21–S33。
