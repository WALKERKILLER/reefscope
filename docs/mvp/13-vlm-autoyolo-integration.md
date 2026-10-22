# 13 · VLM-AutoYOLO：自动标注/训练简化方案与许可决策

> 2026-10-21 对照用户指定的 GitHub 源码及官方 README / 中文 README / docs/API.md。[Somnusochi/VLM-AutoYOLO](https://github.com/Somnusochi/VLM-AutoYOLO) AGPL-3.0，GitHub snapshot 267★、2026-09-22 最新 push [S23]。其能力真实但**不能把一个完整的 React/FastAPI/数据库产品直接当成 Vue3 Django 组件**。

## 1. 从原仓库已经确认的可复用能力

| 能力 | 原仓库的具体实现或 API | SITP 用途 / 边界 |
| --- | --- | --- |
| 视频智能关键帧 | scene/motion/interval 抽帧、SSIM 去重；POST /videos/{id}/extract-keyframes | 采用抽帧思想/可选 CLI，标签来源保留 sample_id、PTS、camera_motion |
| 自动检测标注 | LocateAnything-3B 文本开放词汇检测：POST /detect，categories 如 fish | 鱼目标伪标签预标注，可作为人工加速工具；海洋低能见度必须评估 |
| 精细轮廓 | VLM bbox → SAM2 mask；或 SAM3 文本引导 | 鱼实例掩膜、珊瑚轮廓；**不自动判定白化、健康或死骨骼** |
| 人工干预 | Canvas add/edit/delete bbox、过滤、NMS | 分工职责：保留 CVAT 主协作审核；VLM 项目用于独立批量预标注/修正 PoC |
| 标签导出 | POST /detections/export-batch 或 export-all，格式 YOLO / YOLO-Seg / COCO / VOC / CreateML | 通过 zip→SITP DatasetIngestAdapter 受控转换；检查坐标系、class mapping、mask polygon、误标签 |
| YOLO 一键训练 | POST /train/jobs、/train/jobs/{id}/progress/stream；detect/segment，SSE | 优先作为 fish 检测训练辅助；分析 Run 的正式 Worker 仍走自己的隔离队列 |
| 模型与验证 | PT/ONNX 下载、重训、模型验证/视频推理 | 经过独立 EvalRunner 与 ModelRegistry 才进入平台“候选模型” |
| GPU 管理 | CUDA/MPS lazy load, 10min idle unload, GPU worker | 借鉴资源策略，不复制硬编码到 Django |

官方 API 资料：https://github.com/Somnusochi/VLM-AutoYOLO/blob/master/docs/API.md

## 2. 推荐接入级别

- **MVP-A（确定需要的功能，优先）**：不部署它作为用户的第二站点。SITP 离线工具实现可复用的关键帧抽样 + SSIM 去重、label import/export、人工复核态，并在 docs 中提供 VLM-AutoYOLO 作为**可选旁路工具**的使用步骤。产物统一走 dataset manifest；模型训练仍沿用既有 Ultralytics/CVAT/PyTorch 管线。
- **MVP-B（完成 PoC 后决定）**：如 GPU/许可合适，在隔离内网启动原项目 Docker（需要独立数据库与 VLM/SAM 模型缓存）；由 DatasetIngestAdapter 读取它导出的 YOLO/COCO zip。**推荐初期文件互通而非服务 API 耦合**，每步 hash 校验、权限核对。
- **P1**：若上传与审核效率有量化收益，再实现 opt-in API adapter。仅使用它已文档化的 API；上传用户视频/标注前获得授权，后台凭据不可暴露给 Vue 客户端，设置超时、队列/GPU 并发限制。
- **不做**：复制 React 组件替换 Vue；未经审查将 AGPL 项目直接 vendoring；在生产 Django 工程 pip install 其所有模型；直接信任其训练后输出的 metrics 在展示层成为“正式研究评测”。

## 3. 权重/许可证/设备硬阻塞

- VLM-AutoYOLO **代码 AGPL-3.0**；网络提供修改版服务的义务需审计 [S23]。
- **LocateAnything-3B 权重非商业**：NVIDIA 官方模型卡明确“academic and non-profit research only”，项目 AGPL 代码许可**不会传递商业使用模型权利** [S26]。本项目可能是学生研究但不能无条件推定全部用途满足许可；公网展示/商业/校企合作前要另查。
- SAM3 需要 Hugging Face gated access + HF_TOKEN，源码/模型也要独立核查访问条件；不要把 token 放前端、zip 或论文仓库。
- 项目 README 建议 Linux/Windows **NVIDIA VRAM 12GB 起，16GB 推荐**（作者给出的估计而非 SITP 实测），Python 3.12+、Node 22+、CUDA，Docker 需要 NVIDIA Container Toolkit；MPS Mac 不走 Docker GPU [S23]。
- 模型尺寸、下载缓存、SAM2+VLM/SAM3 的 GPU 占用可能和现有鱼 YOLO、珊瑚 SegFormer 不可同时加载：排队/闲置卸载策略独立设计。
- 自动下载模型/执行 remote code 的行为存在 supply chain 风险；pin revision、校验 hash、隔离容器权限/网络，避免 trust_remote_code 未审查执行。

## 4. 两类标注必须明确分线

**鱼类 detection**：
视频→scene/motion/interval 采样 + SSIM 去重→VLM 预标 fish bbox→人工纠错→YOLO detect 格式数据集→视频级 split→训 YOLO→EvaluationRun (mAP/Recall)→模型审批→ByteTrack/BoT-SORT（独立 MOT evaluation）。

**珊瑚 semantic health**：
视频→分组抽帧→CoralscapesV2 SegFormer 95 类预标 + VLM-AutoYOLO SAM2/3 **可选轮廓工具**→海洋生态专家审 6 类与 255 ignore→indexed PNG mask + taxonomy hash→SegFormer semantic fine-tune→EvaluationRun (mIoU, bleached F1, ROI error)。不能直接将 YOLO-Seg 多边形文件等同于**健康状态六类的每像素完整语义 GT**；重叠、未知、void、分辨率等需要转换和审核。

## 5. 标注质量/效率的实证 PoC

相同的 1–2 条鱼活动视频加若干多样化珊瑚关键帧，设计双臂试验：

| 指标 | 不使用自动预标 | 使用 VLM-AutoYOLO |
| --- | --- | --- |
| 人工标注用时 | 记录真实人分钟 | 记录真实人分钟+纠错时间 |
| 单帧目标漏标/误标 | 标准 GT 审查 | 同一 GT 审查 |
| bbox / mask 质量 | IoU / inter-annotator agreement | 同一尺度 |
| 样本多样性 | 不重复比例 / 各站点覆盖 | 相同采样预算 |
| 训练结果 | 相同 YOLO 版本/超参/seed/测试集 | 相同协议 |
| 系统成本 | 人工/本地硬件 | VLM/SAM 显存+推理秒数+硬件 |

成功门槛初期**不硬设数字**：要求在人工复核后标注时间显著下降，同时同一冻结 test set 的模型质量不退化；用实测数据决定是否常驻部署 VLM 工具。

## 6. 数据契约（仅建议）

- PreAnnotationJob (source_tool, tool_version, model_id, weight_sha, prompt, frame_selection_config, confidence_threshold, nms_config, status, created_by)
- AnnotationProvenance (sample_id, video_id, frame_pts_ms, source_tool, raw_model_output_uri, model_label, confidence, human_review_status, reviewer, approved_class_id, mask_transform_version)
- DatasetVersion (grouped_split, source_annotation_ids, dataset_manifest_sha, taxonomy_mapping_sha, review_summary, usable_for_training=false until approval)

导入时若 raw source tool 只提供 bbox，则不能伪造 segmentation mask；若自动标注少数帧，不能据此推导全视频珊瑚覆盖率。

接口示例仅供设计：POST /api/v1/datasets/import-annotations (file + format, source_tool, model_revision) → 202 dataset_import_id；GET /api/v1/dataset-imports/{id}；POST /api/v1/dataset-versions/{id}/approve。这不是现有 Django 路由。
