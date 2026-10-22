# 06 · 开源项目复用评估与依赖治理

> 研究日期：2026-10-14；依据官方项目/模型页与仓库说明。选用建议不代表已安装、已验证 GPU 兼容或可在所有场景自由分发。文中 [Sxx] 对应 [11-sources.md](11-sources.md)。

## 结论：避免推倒重建

维持原 Vue 3 / Django / Ultralytics YOLO / Artplayer 组合。按“复用库 > 外部独立工具 > 自研薄适配器 > 重造框架”排序：

- **现在采用（经过兼容性实测后纳入开发）**：Ultralytics 的 ByteTrack/BoT-SORT、CoralscapesV2 数据/SegFormer-B5 checkpoint、HF Transformers、CVAT Community（独立标注工具）、Apache ECharts（前端统计）、PyTorch/torchmetrics 或 NumPy 指标、FFmpeg/OpenCV（已有）。
- **优先候选（小型 PoC 后选择）**：roboflow/supervision 的 HeatMapAnnotator/TraceAnnotator、FiftyOne 的错误样本探索、MLflow Tracking 的训练复现、napari 的本地 mask 修正。
- **研究对照/扩展**：DINOv3-LoRA-DPT 更高精度分割、CoralSCOP 的可提示珊瑚轮廓、TagLab 的珊瑚正射影像分割、DeepReefMap 的 3D 重建、CoralSCOP-LAT 的标注与统计工作流参考。
- **MVP 不引入**：重新写一套完整标注平台、FastAPI 第二后端、Redis/Kafka/Celery 微服务集群、浏览器内大模型训练或海底空间地图。

## 对比矩阵

| 项目 / 资源 | 可直接获得的能力 | 在 SITP 中的具体接入点 | 决策 | 许可证/障碍 |
| --- | --- | --- | --- | --- |
| **Ultralytics Track** [S01] | YOLO + ByteTrack / BoT-SORT，持久化 ID | backend/app/analysis/fish.py，按时间顺序输入帧；从 boxes.id 提取身份 | **采用**，先沿用原 pinned ultralytics 版本 | Ultralytics AGPL-3.0 / 商业许可；务必检查网络部署与修改分发义务 [S15] |
| **supervision** [S02] | 轨迹线、热图、对象 ID 标注器、统一 detections 对象 | 算法 sanity-check / 渲染示例；如适配成本低引入 helper | **试用对照**，正式指标在平台内部计算 | MIT；渲染“累计热力”不等于我们定义的时间加权热图 |
| **CoralscapesV2 数据集** [S03] | 2,433 帧，95 类细分底栖标注，珊瑚 health 状态 | 离线数据下载/评估集，标签元数据 | **采用** | Apache-2.0；地理分布 Red Sea，需域适应 |
| **CoralscapesV2 SegFormer-B5 95** [S04] | 专业珊瑚像素分类的即用模型，96 logits 0=void | backend/app/analysis/coral.py adapter | **MVP 基线** | Apache-2.0；显存、裁片重叠和映射评估 |
| **DINOv3+DPT LoRA（EPFL）** [S05] | 更强的分割对照 | 作为第二个 ModelVersion 运行相同视频 | **P1 对照** | DINOv3 encoder 为 gated，需账号授权并核查模型授权，不能当零门槛 |
| **CVAT Community** [S06] | 视频/图像多成员标注、任务复核、mask 导出 | 单独 compose profile / 独立机器；导出 Segmentation Mask 后转换标签 IDs | **采用，平台不重造编辑器** | Community MIT；视频项目/导出各格式的 tracks/attribute 支持不同，要验证 API 细节 |
| **napari** [S07] | 直接修单通道整数 label layer | 算法人员少量难样本的本地快速修正 | **辅选** | BSD-3-Clause，本地桌面工作流非网页协作 |
| **FiftyOne** [S08] | 比较模型结果、筛错、抽样、按视频和站点浏览 | dataset_version 外部调试，不作为面向用户生产 UI | **P1 可选** | Apache-2.0；额外数据服务/持久化，不可当轻量前端库 |
| **MLflow Tracking** [S09] | experiment run / params / metrics / artifacts / 模型 lineage | backend/ml 训练、评估 CLI；运行日志与 manifest 同步 | **建议采用为训练专用工具** | Apache-2.0；独立轻量服务或本地文件后端，生产 inference 不依赖 MLflow 在线可用 |
| **DVC** [S10] | 大数据版本、remote 指向、repro pipelines | 大数据集增多或多人远程训练时 | **P1 候选** | Apache-2.0；小规模 MVP 先使用强校验 manifest 即可 |
| **Apache ECharts / vue-echarts** [S11] | 折线、柱形、矩阵热图、联动图例 | frontend/src/components/analysis；和 Canvas 热图分离 | **采用** | Apache-2.0（ECharts）；前端包体、按需导入，像素层热图仍由 Canvas/WebGL |
| **TagLab** [S12] | 珊瑚 orthoimages 标注/训练/定量，领域经验丰富 | 看它的科研指标和标注工作流，未来对正射影像集成 | **参考，不复制源代码** | GPL-3.0；桌面/正射用途，不是当前视频自动分类的替代 |
| **CoralSCOP** [S13] | coral vs non-coral/promptable 边界、个体轮廓 | pre-annotation/难样本轮廓修正对照 | **研究阶段候选** | 运行环境与权重分发条款单独审核；与健康状态识别任务不同 |
| **CoralSCOP-LAT** [S14] | 珊瑚密集分割标注、可定制标签、统计工作流 | 参照标注审核 UX，独立 PoC | **参考** | React+FastAPI 与现有栈不同，未发现足以支持直接嵌入的稳定 SDK/明确许可，需核查 |
| **DeepReefMap** [S16] | 3D semantic map、ortho mosaic、benthic cover、viser 查看 | 如后续科研转向移动摄像机真实面积统计，另开离线分析 pipeline | **P2 可选，不放本次视频热图的关键路径** | Apache-2.0 核心；部分 third-party/weights 限制、视频相机标定与算力成本 |

## 实际接入策略

### 路径 A：鱼类业务不换基础检测器

把当前 detector 的视频读取及权重初始化能力抽成 adapter（不在首次迭代大规模重构）。新模式以 1 帧/step 提供给现有权重的 model.track，persist 只作用于**同一段视频**，切换视频必重建 track 状态；优先 ByteTrack，比较 BoT-SORT 在移动机位上的稳定性 [S01]。选择 supervision 只复用可验证的标注展示与数据转换，不把其默认热图解释成生态指标 [S02]。

### 路径 B：Coralscapes 直接作为离线模型

模型与输入 processor 在 worker 独立加载并复用；记录模型 checkpoint 的 revision/sha256。推理时将 96 维输出插值到原图 (H,W)，再对 1–95 的类别按专家审定的映射归类。任何类别和概率映射不应绕过 schema 验证；未知归 unknown 或 ignore。有效区域 ROI 单独管理，掩膜 PNG 和原始 class/logits 版本均留痕 [S03,S04]。

### 路径 C：把标注、实验视为独立研发工具

- CVAT 保存协作标注；脚本导出为规范 PNG、JSON metadata [S06]。
- FiftyOne 可用来筛选高不确定性帧、不同模型 disagreement 帧 [S08]。
- MLflow 保存实验参数指标与权重链接，但 Web 用户业务只读经平台注册的 ModelVersion，不直接依赖 MLflow [S09]。
- 不允许 worker 动态 clone 用户任意提交、直接执行外部模型仓库任意代码或未经检查 trust_remote_code=True。

## 开源治理检查项

1. 引用资料和许可证分别用于数据、预训练权重、源代码、二级依赖；不能只看 GitHub 仓库根 LICENSE。
2. Ultralytics 是 AGPL 路线，未来公网 SaaS、发行二进制或商业用途须由项目方核验是否满足其条款，不在本文件作法律结论。
3. 对 gated DINOv3、GPL TagLab、无明确 LICENSE 的 CoralSCOP-LAT **先隔离作为研究工具**，不直接复制代码。
4. 每个依赖必须有：准确包版本、python/torch/CUDA 矩阵、模型下载哈希、许可记录、模块负责人、最小推理/训练 smoke test 和卸载替代方案。
5. 珊瑚图像/视频版权、拍摄许可、站点数据保密性不能以“模型开源”推定自动可转发。

来源详见 [11-sources.md](11-sources.md)。


## 2026-10-21 更新：模型报告/标注/信息大屏

新增参考：[YOLO Report Analyst](https://github.com/xiangshenchi/yolo-report-analyst)（MIT，仅 Skill 报告结构，不作为指标计算器）；[VLM-AutoYOLO](https://github.com/Somnusochi/VLM-AutoYOLO)（AGPL-3.0，NVIDIA LocateAnything 权重非商业，独立离线可选工具）；[IofTV-Screen-Vue3](https://github.com/daidaibg/IofTV-Screen-Vue3)（MIT、页面设计/scale 参考）；[datav-vue3](https://github.com/vaemusic/datav-vue3)（MIT，按需轻装饰，维护较慢）；[DataRoom](https://github.com/gcpaas/DataRoom)（Apache-2.0，大型 Spring Boot 大屏编辑器，参考未来配置模板）；[VisActor/VChart](https://github.com/VisActor/VChart)（MIT，未来图表替代 PoC）。

**确定层级**：ECharts 优先正式接入（已有 Vue 技术选型），DataV 装饰小范围；VChart 不与 ECharts 默认共存；不用 DataRoom/GoView 的全站替换原 Vue/Django。AI 报告不能代替科学量化计算。详情 [12-training-report-and-benchmark.md](12-training-report-and-benchmark.md)、[13-vlm-autoyolo-integration.md](13-vlm-autoyolo-integration.md)、[14-visual-wall-research-and-spec.md](14-visual-wall-research-and-spec.md)。独立源与流行度快照见 [11-sources.md](11-sources.md) S21–S33。
