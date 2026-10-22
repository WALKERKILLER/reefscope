# 09 · 架构决策记录（ADR，2026-10-14）

> 记录**谁确认了什么**，避免将研究推荐和用户批准混淆。当前用户仅明确确认屏幕画面坐标鱼类活动热力图，其余为待评审建议。

## ADR-001 · 鱼类热图属于 video image-plane

- **状态：ACCEPTED by user，2026-10-14**。
- **问题：** 热图是画面相对活动密度，还是海底真实空间分布？
- **选择：** 仅以当前视频画面归一化位置输出；不得标称地理位置/真实鱼密度。按 track 的观测时间权重累计；视频 camera_motion 未知/移动时展示解释提示。
- **实现影响：** 新 AnalysisRun setting 固定 coordinate_space=image_plane；heatmap schema 存 track-seconds、raw grid、归一化与算法版本；不引入 SLAM/3D、相机标定相关阻塞。
- **可逆性：** 未来可增加 map_coordinate_space=georeferenced 类型，必须新 schema 和几何配准模块，不能复用热图值假装有坐标。

## ADR-002 · 模块化单体 + Worker

- **状态：PROPOSED**。
- **理由：** 原仓库已 Vue/Django 完整视频闭环，首要风险是后端 daemon Thread + 2 web workers 使队列状态不可靠。
- **推荐：** 新增 AnalysisRun 数据模型、一个独立 worker、SQLite + 本地文件；横向扩展在指标确定后再迁移队列。
- **替代：** 立即 Celery/Redis，功能强但增加部署复杂度和生产故障面；独立 FastAPI 微服务，重复 API/鉴权和媒体管理。

## ADR-003 · 珊瑚 baseline 选择

- **状态：PROPOSED**。
- **推荐：** CoralscapesV2 SegFormer-B5 95-class 作为 v0，数据 95 个有效类、logits 96 个通道、原始 0 是 void。专家映射健康输出并开展域适应训练。
- **替代：** SAM2/3 或 CoralSCOP 可做轮廓辅助但非现成白化/死亡分类器；DINOv3 高精度对照但 gated encoder 及算力高。
- **风险：** 视觉真值定义、非红海现场 domain shift、类别稀有和 mask 边界误差。
- **决定点：** 先对采集视频做无微调 PoC、组织专家标注后再确认模型。

## ADR-004 · 标注/训练研发工具

- **状态：PROPOSED**。
- **推荐：** CVAT Community + 标准化 PNG/JSON 导出、独立 Python 训练 CLI + MLflow Tracking、必要时 FiftyOne；网页仅做模型版本和分析结果展示，不重写标注编辑器。
- **取舍：** CVAT 对单通道 mask 需要固定 palette 与导出格式转换测试；MLflow 不可成为生产 Django/worker 的单点依赖。

## ADR-005 · 模型依赖与 License

- **状态：PROPOSED + RELEASE BLOCKER**。
- **要求：** 任何将 Ultralytics / GPL 工具 / 预训练权重打包进公网或可分发镜像前，核查许可证、模型数据 provenance、下载审计和编译/运行环境。记录 LicenseManifest，不拷贝外部源代码到主工程以规避审计。
- **环境：** 当前 requirements 固定 ultralytics==8.3.109，文档要按**已锁定版本**实测 track API；不应直接使用网页最新 YOLO26 示例所暗示的版本兼容性。

## 下一步待确认问题

- 拍摄视频以静止机位还是 ROV 移动为主？这会影响 ByteTrack vs BoT-SORT 对照和热图的解释文字，但**不改变 image-plane 已确认决定**。
- 是否有珊瑚白化/死亡的专业复核人员、是否有站点/潜次/样方元数据？
- 算法训练可用显卡/显存与训练时间、团队人数？确定后才能冻结训练 batch/crop/GPU 配置。
- 预期仅校内演示还是允许公网访问？决定最小身份鉴别与 License 合规边界。


## ADR-006 · 训练量化数据必须可复算（2026-10-21）

- **状态：REQUIREMENT ACCEPTED，implementation PROPOSED**。
- 用户要求参照 YOLO Report Analyst 量化训练；决定其报告七章只是模板，指标真实来源由 frozen dataset + EvaluationRun + audit 定量得出；MOT/珊瑚各用专业指标计算，AI report 不成为 single source of truth。

## ADR-007 · VLM-AutoYOLO 只可选接入（2026-10-21）

- **状态：USER REFERENCE CONFIRMED，integration PROPOSED**。
- 用户给定项目用于自动标注提效；拟先基于 dataset ZIP/COCO 输入互通，而非复制 React/FastAPI/AGPL 程序。非商业 NVIDIA 权重与 GPU/SAM3 gating 作 go/no-go 条件。人审和冻结测试集评估不可跳过。

## ADR-008 · 生态大屏是最终视觉目标（2026-10-21）

- **状态：GOAL ACCEPTED；具体开源方案 PROPOSED**。
- Vue3/Vite 保留，ECharts + 自定义深海 16:9 大屏、可选 DataV-Vue3，不替换后端；三个 route: ecology/train/evidence；主视频与鱼热图/珊瑚掩膜始终为中心。参照 IofTV/DataRoom/GoView 但不照搬其全部平台/素材。
