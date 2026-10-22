# 15 · MVP v2 冻结范围、并行分工和门禁

> 2026-10-21 综合本轮两个参考 GitHub 项目与大屏调研。画面热图与“最终用信息大屏样式”为已明确需求；具体开源依赖、设计 tokens、验收阈值属于提案，待团队确认。以下按**可拆分 PR**定义工作，不假设已实施。

## 推荐 MVP v2 最小成功标准

同一段真实视频可导入→鱼 YOLO 检测/真实 track ID → image-plane 时间加权热图与可开关叠加→CoralscapesV2 baseline 与可复核 6 类掩膜→导入一份真实测试评测指标→出可重算训练报告→在 Vue3 深海信息大屏展示，并有来源/限制说明。预标注有可选离线辅助通道，不因 VLM 模型下载而阻塞整个演示。

### M0：冻结契约、数据与环境（A/E 协同，所有组前置）

- 冻结 AnalysisRun/TrainingRun/EvaluationRun/TrainingReport/ModelVersion/DatasetVersion ID、sha 和测试集组规则；
- 固定 fish bbox XYWHN、鱼轨迹 track ID、image-plane heatmap track_seconds，固定珊瑚源 96 logits ID0 void→target255、6 类 taxonomy；
- 静态 fixture 校验、DB 独立 Worker、媒体访问规则、硬件/License manifest；
- 报告 schema 与 mask 视频 overlay 先 mock 渲染；定义真实样片/标注来源和不可提供时 fallback。

### M1：视频/鱼类主线（B+D）

- B：YOLO + ByteTrack/BoT-SORT，轨迹 JSONL，时间窗热图 raw/display，基于人工 track GT 的 EvalRunner；
- D：主视频 Canvas bbox/ID/track/heat 时间轴/图层与导出；
- DoD：轨迹 ID 一段视频内稳定可审查，热力图守恒、seek/fullscreen/resize 对齐，并显示“非真实地理热点”。

### M2：珊瑚基础+离线训练（C+E）

- C：CoralscapesV2 预训练 96 通道推理/专家映射、抽帧、CVAT、正式分组 split、同测试集版本化训练；
- E：按类别 Dice/IoU、白化 F1、面积比例误差、unknown ratio、错误样本挖掘；
- DoD：由人工 mask 复算评测，有 raw/merged mask lineage 和 baseline-vs-tuned 对照；若暂无标注展示“待评估”，不能虚构白化识别精度。

### M3：训练效果量化与报告（E+A，C/B 提供原始预测）

- 针对 fish/coral/MOT 三种类型分别封装真实指标计算，存 EvaluationRun；
- 移植 YOLO Report Analyst 七章“报告结构”而不是自动评分阈值，训练曲线 + per-class / confusions + 分组测试 + 推理效率 + 基线/消融；
- AI 自动摘要为可选，原始数据/数值独立保存；PDF/MD 下载，质量审批出现在 ModelVersion 旁；
- DoD：有至少一个真实指标 artifact 可重算，model hash、seed 和 test split 可追溯；缺源 GT 时不声称精度。

### M4：标注提效试点（C+B）

- 视频 scene/motion/interval 抽帧与 SSIM 去重；PoC 单独部署 VLM-AutoYOLO 或导入其 YOLO/COCO zip；
- 数据转换器写 AnnotationProvenance 和 DatasetVersion，人工抽样复核/审核；对 fish detection 与 coral semantic 两套标签分支严格分隔；
- DoD：time-to-label、corrected FP/FN、最终测试集性能有 A/B 记录；在无 GPU 或 license 不适用时可以不启用 VLM 旁路，CVAT 手动标注仍可完成主闭环。

### M5：Vue 海洋生态信息大屏（D+E）

- /wall 生态总览、/wall/train 训练质量、/wall/evidence 生态证据；
- 原 Artplayer 中心占优，周围 3–5 组真实关键指标与 ECharts、右/下方趋势，按需 DataV-Vue3 边框/装饰；
- 与 / 工作台共享数据 API，保存选择的模型版本与时间窗、量纲和科研限制声明；项目视觉遵从 14；
- DoD：1920×1080、4K、缩放/全屏、P95 交互时延和长时间内存稳定性实测；图表全部有 unit/dataset/ROI、对 N/A 显示缺失原因。

### M6：发布审查（A+全部人员）

License / model rights / data copyright 审核、URL/上传安全、第三方模型随镜像发行边界、DB Worker 恢复，UI 无虚构“实时准确率”。结果演示和研究评测分开签收。

## 所属团队与独立 PR

| 组 | 拟提交 PR | 前置依赖 | DoD |
| --- | --- | --- | --- |
| A 平台工程 | feat: add versioned experiment and evaluation entities | 契约 M0 | SQLite migrations、可重试队列、旧接口不回归 |
| B 鱼类算法 | feat: add MOT and image-plane dwell heatmap | M0, 视频样本 | JSONL、时窗 API、同视频所有帧对齐、人工真值评测 |
| C 珊瑚算法 | feat: add coral segmentation and training pipeline | M0, 专家复核标签 | id0/255 映射、group split、per-class 结果 |
| D 信息大屏 | feat: add ocean ecology wall dashboards | M0 mock fixtures | 3 屏、语义面板、不卡主视频、局部按需图表 |
| E 科学评估 | feat: add deterministic model reports | M0 与 B/C Eval artifacts | 真实指标、基线比较、CI source validation |
| C/B 联合 PoC | research: evaluate VLM-assisted annotations | M2 部分样本与硬件 | 标注省时对照与版权合规决定，而非强制主线 |

## 暂不加入 MVP 主线的内容

- 在线跨硬件分布式训练；完整 GoView/DataRoom/React 二套后台；海底 3D 重建/真实 GIS 热力图；生产端依赖 NVIDIA 非商业 LocateAnything 权重；无人工校准的珊瑚自动生物学结论；对任意观众公开全部原始视频/站点数据。

## 参考路线

优先从 [01-architecture.md](01-architecture.md)、[02-contracts.md](02-contracts.md)、[12-training-report-and-benchmark.md](12-training-report-and-benchmark.md)、[13-vlm-autoyolo-integration.md](13-vlm-autoyolo-integration.md)、[14-visual-wall-research-and-spec.md](14-visual-wall-research-and-spec.md) 开始联合评审。核实资料见 [11-sources.md](11-sources.md)。
