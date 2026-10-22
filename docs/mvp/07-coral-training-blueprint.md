# 07 · 珊瑚训练与平台联动：实施蓝图

> 2026-10-14 官方数据/模型页核查结果。**此文档是训练协议设计，不宣称已经下载 220 GB 数据或进行了 GPU 训练。** 详情来源 [S03][S04][S05][S13][S17] 见 [11-sources.md](11-sources.md)。

## 1. 研究任务与标签：避免“看到白色=白化”

- **任务 1（强制 MVP）：** 每像素 coral reef 底栖语义分割，得到“可识别珊瑚与环境背景、健康/白化/死亡/藻覆/未知”的区域。
- **任务 2（P1）：** 在已分割珊瑚 ROI 上做影像局部状态趋势比较，含画面受光、水深、模糊、海水色偏和遮挡的质量标签。
- **任务 3（P2）：** 个体/群体（colony）实例 segmentation 与三维正射面积测量，需 CoralSCOP/DeepReefMap 等额外模块，不与第一版语义 mask 混为一谈。

MVP 建议六类：other/background=0；live_unbleached=1；visually_bleached=2；dead_skeleton=3；algae_covered_structure=4；coral_unknown=5；ignore=255。以上是**输出展示类别**，不是源模型 95 类标签。对于只有通用“hard coral”的源类别不能凭标签声称健康，需映射到 unknown；只有可识别“dead”的原始类别才候选 map 到 dead；藻覆结构不能拿普通藻类类替代。确定标准时邀请海洋生态专家定义标注协议，依疾病与共生藻生物学情况可将“褪色但未可确认白化”归 unknown。

### 原始模型最容易写错的细节

- CoralscapesV2 数据集的 **95 个有效语义类 ID 1..95**；预训练 SegFormer-95 模型 **96 logits，ID 0 是 void/ignore** [S03][S04]。
- 原始官方 mask 的 0 与我们显示/训练时的 0 **含义不同**。转换函数必须先特判 source=0 → target=255，而不是其他背景；若是 water column/background 有真实标签可映射到 target=0。
- 当用 6 类微调时需要固定 token：如采用可训练 6 输出 head，应明确预训练 head 初始化策略；更保守的是保留 96 logits，利用 class logits 按组聚合为 6+ignore，并遮罩 source=0 的训练 target。**不允许把 argmax 以后离散标签转换拿去求交叉熵**，那样无法回传梯度。
- 训练 target 只有 0..5/255，dtype uint8；预测 mask resize 使用 nearest-neighbor，logits 上采样使用 bilinear，再 argmax。记录在训练/推理中采用哪一个空间过程。
- 对官方 composite label 从官方 id2label.json 解析 + 人工审核生成带 SHA256 的 mapping YAML；不要根据字符串包含“white”或视觉 RGB 直接推断白化。

## 2. 数据事实与下载

**CoralscapesV2** 官方 Hugging Face 数据页 https://huggingface.co/datasets/josauder/coralscapesV2 ：
- 2,433 张 1024×2048 的专业密集标注视频帧，**95 类**；涵盖 alive、bleached、dead、algae covered 的特定复合标签。
- 官方 dataset card 称 **41 个潜水站点**；split 为 train 1,790 张 / 34 站，validation 170 张 / 3 站，test 473 张 / 5 站 [S03]。注意 **model card 的文字说 55 站，与 dataset card 不一致**，此外 split 所列 34+3+5=42 个 site 计数与总体 41 也存在口径差异（可能跨 split 重复，不能推断唯一值）；应下载 metadata 后以唯一样本 site_id 去重核实，并记录冲突，不混用这些数字。
- Apache-2.0；Hugging Face 数据仓库文件较大，实验先按需提取子集，不纳入 Git。
- 数据带原始 id2label.json、label2color.json；数据集 39 类 legacy mapping **仅用于对照**，不要先折叠为 39 类再尝试恢复细粒度白化标签。
- 生态场景主要红海；国内/其他海区的视频 domain shift 必须单列实验。

建议数据索引形态：

```text
datasets/
  coral_health/
    raw_external/CoralscapesV2/       # 原始数据，仅本地/对象存储
    site_local_2026/                  # 用户拍摄原视频/抽帧
    labels/
      taxonomy_source_v2_95.json     # 来自官方 id2label
      mapping_reviewed_v1.yaml       # 专家签署的目标标签映射
    versions/
      dataset-v001/manifest.json
      dataset-v001/splits/*.jsonl
      dataset-v001/masks/*.png
    experiments/                      # configs/results/link to MLflow run
```

frame manifest 至少含 sample_id, parent_video_id, site_id, dive_id, timestamp_ms, image_sha256, frame_path, mask_path, original_shape, source_dataset, annotation_review_status, reviewer, taxonomy_version, split, camera_motion, ROI_polygon 可选。

## 3. 零训练 baseline 是硬门槛

**模型 A（主线）：** EPFL SegFormer MiT-B5 95-class，https://huggingface.co/EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class
- 官方 95 类 test 报告：single-pass 768×1376 **mIoU=36.420%**；strided 2×1024×1024 **mIoU=37.177%**，pixel acc 分别 79.462%/80.382% [S04]。这些是**官方域 95 类全类别分割指标**，绝不能当作“我们本地白化 F1”或“预期白化准确率”。
- 官方训练配置用于参考：AdamW，学习率 6e-5，weight decay 1e-2，polynomial LR，100 epoch、batch 4；1024 随机 crop + 小幅色彩增强与旋转 [S04]。我们小样本微调不宜机械复制 100 epochs。
- 先完成 zero-finetune 在用户视频的推理和人工诊断，再决定是否训练；缓存原始 95/96 类预测以及合并后的 6 类结果。

**模型 B（对照 P1）：** DINOv3 ViT-L + DPT LoRA 95 类，模型索引/实现可从 https://github.com/eceo-epfl/deepreefmap 及 https://huggingface.co/EPFL-ECEO 查；潜在更优精度，但 encoder 许可/gated access、算力开销更高 [S05]。不要把其环境强加给第一版 GPU worker。

**模型 C（轮廓工具）：** CoralSCOP https://github.com/zhengziqiang/CoralSCOP ，擅长珊瑚形态/可提示 mask 生成，不是活/白化/死自动分级模型；用于疑难轮廓预标注，必须经人工分类与检查 [S13]。

## 4. 本地视频标注与 QA

**第一版**从多站点/多个原视频中先筛 150–300 帧做专家复核样本（此数量只是工程 pilot，并非任何精度保证）：
- 从每条片段按 2–5 秒采样，加入各类光照、深度、水色、浑浊度、白沙底、健康/白化/死亡以及空背景负例。过滤糊片但保留足量困难样本。
- 自动预标注原始 95 类与合并 6 类 mask，使用 CVAT Community [S06] 或 napari [S07] 作人工修正，复核结果输出为单通道 PNG 0..5/255。
- 重要样本建议二人独立复核，分歧由海洋生态专业人员裁决；记 reviewer 与 disagreement 原因。
- 优先抽模型高熵、低置信度、边界复杂、模型互相不一致、白化 vs 死骨骼混淆、不同站点/水深的帧，避免纯随机选样造成只选“容易样本”。
- **Split 按 site/dive/video 组**，至少同一 parent_video 全部属于同一 split；站点外测试优先。CVAT 导出的索引 RGB mask 先解析真实 palette，再映射整数 ID，不能按 RGB 去训练。

## 5. 训练对照、消融设计

先同时保存 **95 类原始模型预测**和 6 类变换后的结果，选择以下可复现实验矩阵：

| 编号 | 训练/推理方案 | 需要回答的问题 |
| --- | --- | --- |
| B0 | SegFormer-95 零微调 + 6 类专家映射 | 跨海域直接泛化有多好？ |
| B1 | 仅微调 6 类 decoder/head 或可训练聚合 head | 少量标注能否改善白化/死亡混淆？ |
| B2 | 分阶段解冻 encoder + 小学习率 | 是否改善跨水色/浑浊度泛化？ |
| A1 | 去掉水下光照/色偏增强 | 增强有益还是破坏健康颜色特征？ |
| A2 | 不使用半监督/伪标签 | 人工少量标注究竟带来多少收益？ |
| A3 | 随机按帧 split vs 按视频/站点 split | 量化数据泄漏风险（随机 split 仅作为诊断，不用于正式汇报） |
| C1 | 39 类 Legacy baseline 与 95 类映射比较 | 细粒度健康信息来自哪里？ |
| C2 | DINOv3-DPT 95（可选） | 高算力权衡与边界质量改进？ |

每个实验在多个 seed 下运行（资源允许至少 3 seeds），明确固定 test 集，记录训练/验证 loss、early stopping、模型 hash、学到的类权重/augmentation、验证数据所属站点、推理尺寸和后处理。

## 6. 评估标准（必须同时包含）

- **像素层**：每类 IoU、macro-mIoU、white/bleached Precision/Recall/F1、dead vs bleached 混淆矩阵、valid pixel accuracy。
- **样方面积层**：人工 ROI 内各类面积比例误差（百分点）、分母、未知面积占比，站点 bootstrap 置信区间，不计算没有 ROI 的“真实珊瑚覆盖率”。
- **泛化层**：held-out dive/site，按水色/画面质量/深度切片统计；baseline 与 tuned 同一测试组对比。
- **工程层**：FPS、GPU 显存、原帧到 mask 对齐误差、冷启动时间、模型下载与重跑可重复性；绝不捏造某个消费显卡的显存占用。
- **生态解释**：白化≠必然死亡、灰白死骨骼≠活体白化、藻覆不一定是活珊瑚；低置信度时保留 unknown。

## 7. 研发接口：与 Web 平台解耦

候选的独立训练 CLI（尚未实现）：

```text
python -m ml.extract_frames --video-dir ... --manifest-out ...
python -m ml.preannotate --model segformer-b5-95 --output ...
python -m ml.validate_dataset --dataset-version dataset-v001
python -m ml.train_coral --config experiments/coral/b1.yaml
python -m ml.evaluate_coral --checkpoint ... --split heldout_site
python -m ml.register_model --experiment ... --model-name coral-health-b1
```

训练在离线机器完成；训练过程中 **CVAT/MLflow 非生产后端依赖**。模型注册后，worker 根据 ModelVersion 的受信任路径/sha、preprocess、taxonomy 和权重格式加载，产出 masks 和逐帧计量指标；前端只关心稳定 /api/v1/analysis-runs API。

本目录可添加的基准数据契约示例见 [../../fixtures/mvp/](../../fixtures/mvp/)。训练依赖与 Web 推理依赖必须隔离，避免每次部署平台都重新安装大规模研究包。
