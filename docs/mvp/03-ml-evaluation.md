# 03 · 模型、数据、训练与评估（首轮可执行路线）

> 进一步研究材料：珊瑚训练 [07-coral-training-blueprint.md](07-coral-training-blueprint.md)；开源选型 [06-open-source-adoption.md](06-open-source-adoption.md)；可复查资料 [11-sources.md](11-sources.md)。

## A. 鱼类检测 + 追踪

### 重用已有工作

- `backend/models/model_best.pt` 是已提交的单类 fish 检测权重；本阶段不强制重训。
- 当前推理由 `backend/app/services/detector.py:387-585` 的批量 `model.predict` 完成，输出 bbox 时间戳，却没有 `track_id`。
- 在新 `fish_tracking` 模式中使用 `YOLO.track` 对顺序帧运行 ByteTrack；对照 BoT-SORT。保留现有 `fish_detection_legacy` 模式以保护兼容性。不同视频必须重置 tracker 状态。
- 默认逐帧（stride=1），优先 track ID 稳定；不要把大 stride 预测批处理直接拼接成轨迹。输出连续 ID、置信度、时间戳和归一化轨迹，兼容旧检测框 UI。

### 评估

- 标注 3–5 条具有不同水体浑浊度/拥挤度/相机运动的视频，至少每条选几十秒连续序列，人工标注 ID。
- 检测：Precision/Recall/mAP50；追踪：IDF1、HOTA 或 ID switches、ID fragmentation、轨迹完整度（按有标注条件选择）；处理性能 FPS、VRAM。
- 轨迹展示：只画相同 track_id 的观测点连续线段；超时断轨应断开。热图用轨迹中心的时间加权频数，而不是叠加每帧 bbox 计数。
- 输出对比：ByteTrack vs BoT-SORT；stride=1 vs 2/5；动态机位 vs 固定机位，记录 FPS 与错误类型。

## B. 珊瑚健康语义分割（最快启动）

### 推荐第一模型

**CoralscapesV2 95-class SegFormer MiT-B5**：
https://huggingface.co/EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class

数据说明与模型基线：
https://josauder.github.io/coralscapesv2/
https://huggingface.co/datasets/josauder/coralscapesV2

- 直接加载 `AutoImageProcessor` + `SegformerForSemanticSegmentation`，先做 **zero-shot/domain baseline（直接推理）**。
- 该预训练模型是 95 类底栖生境细粒度语义分割，不等于输出六个健康类别的成熟判定；需要审核 taxonomy 以及适应本地视频的不同水色、散射、曝光。
- `SAM 3.x` 可做可选边界修正/视频伪标签传播，不把开放词汇提示的白化结果当生态真值。
- 若基线在本海域显著失效，增加 DINOv3 ViT-L + DPT（同 CoralscapesV2）作为高精度对照；不要一开始同时维护三个模型体系。
- 预训练权重可能需要额外 `transformers` / `torch` 与显存，建议独立推理进程、分辨率分块 overlap 推理；确保 label id 与 resize 时 nearest-neighbor mask 复原不混淆。
- 任何训练前确认数据/模型许可证、实际拉取版本 hash 与训练环境。

### 标注与训练流程

1. **元数据采集**：video_id、站点/样方、日期、设备、深度(若有)、镜头固定/移动、质量、帧率、色卡(若有)、训练/测试来源。
2. **抽帧**：按间隔 + 多样性采样，过滤严重模糊，保证不同视频、光照、白化程度；第一版先挑 150–300 张待核验代表性关键帧，不把这个数字当统计学保证。
3. **自动预标注**：CoralscapesV2 95 类推理；保留原始 95 类 logits/类别及映射版本，转换为 6 类伪标签 + `ignore`。
4. **专家复核**：用 CVAT 或 napari 修边界和健康状态；白色沙、骨骼、眩光等困难样本必须人为评定。模糊的健康/死亡设 unknown，不强行猜测。
5. **按站点/视频分组划分数据集**：禁止同一个原始视频的相邻帧同时进入训练集和测试集；可用 train/val/test 70/15/15 作为初版建议，最终按站点与样本规模决定。
6. **微调**：从已有 SegFormer-B5 checkpoint 出发，可先冻结部分 encoder、训练 decoder/head，再小学习率解冻；按标注量调节数据增强（水下色偏、轻量模糊、尺度旋转），避免破坏白化颜色诊断。
7. **评估**：每一类 IoU、mIoU、白化 F1/Recall/Precision、死珊瑚与白化混淆、样方级白化面积误差、站点外泛化；每次实验存 seed/config/数据版本/权重 hash/混淆矩阵。
8. **模型注册与回滚**：录入 ModelVersion，前端选择版本，处理过的视频可同视频不同版本重跑，比较结果后再提升为默认模型。

### 非伪代码的最小加载路径（训练完成前先做推理）

```python
from transformers import AutoImageProcessor, SegformerForSemanticSegmentation
MODEL_ID = "EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class"
processor = AutoImageProcessor.from_pretrained(MODEL_ID)
model = SegformerForSemanticSegmentation.from_pretrained(MODEL_ID)
# 对视频抽取的 RGB PIL 图像：
inputs = processor(images=image, return_tensors="pt")
logits = model(**inputs).logits  # 后续插值至原图尺寸再 argmax；不能直接把 95 IDs 当作 6 IDs
```

实际脚本需要处理设备移动、拼接瓦片、批量推理、PNG 掩膜导出和映射审查；上面只是权重连通性示例。

## C. 指标解释与数据挖掘边界

- **鱼类二维轨迹、屏幕热力图**：可演示鱼的驻留、路线与画面占据；移动镜头未配准时，不代表固定海底地理位置。估计游动速度必须先有标定/尺度与相机运动补偿，不能把像素/秒称为 m/s。
- **珊瑚白化可见像素比例**：同一视频帧可以做描述性估计；相邻帧高度相关且重复覆盖，不能直接汇总当作珊瑚礁覆盖率。正式站点生态指标需指定底栖 ROI、样方/样带方案，或正射/三维重建去重。
- **死亡和白化**：褪色、活体白化、死亡裸露骨骼视觉上高度相似；任何论文报告需要专家定义的真值与不确定性统计。
- **数据挖掘 MVP**：分析 run 的 5 类图表优先：不同时间段轨迹密度、按 ID 的轨迹长度分布、置信度/ID switch 质量、不同采样站点的健康/白化面积比、模型版本比较与样方不确定性。先 CSV 导出，不做黑箱“生态健康综合评分”。
- **质量阈值**：首轮作为验收建议：评估集比基线白化 mIoU/F1 有可复现改善，不接受无验证集结论；轨迹/热图时间轴与回放误差低于 1 帧（PTS 可靠时）；导出与可视化统计一致。具体模型精度门槛要看本地人工真值，不凭空设定准确率。

## D. 可重复性

`experiments/<date-run-id>/` 保存：git SHA、模型与数据版本、requirements/lock、CUDA、random seed、split、训练 yaml/json、metrics、confusion matrix、样例可视化；大数据和权重存对象/本地数据目录而非 Git。模型许可、真实 GPU 训练、端到端定量结果均需后续验证。


## F. 官方 benchmark 与本地指标必须分离

模型卡报 CoralscapesV2 SegFormer-B5 95 类 mIoU 36.420%（single pass）/ 37.177%（strided）；源模型输出 96 logits，原始 ID0=void，1–95 才是语义类。本地珊瑚健康/白化 F1 必须等有专家审定的独立测试集后计算，不能引用这个 95 类 mIoU 当成本地白化精度。

原业务环境固定 ultralytics==8.3.109，官网最新 YOLO Track 示例的支持选项可能不同；算法组须优先用锁定依赖 smoke test。


## G. 完整量化报告和可选自动标注工作流（第三轮）

参考 yolo-report-analyst 的完整七章报告，**但本项目另设可复算 EvaluationRun**：YOLO detection 独立 held-out AP50/AP50-95/P/R/latency；tracking 单独 IDF1/HOTA/IDSW（需要标注）；珊瑚独立 mIoU/per-class Dice/bleached F1/ROI error。写明 baseline、best/last、源数据、统计样本数和置信区间，不照搬“mAP50≥0.90 即工业优秀”启发式。
VLM-AutoYOLO 可以帮人工预标鱼 bbox、SAM2/SAM3 轮廓和智能抽帧，但与“珊瑚 6 类健康 GT”不同。两条训练支线都先人工审核，再拆分数据集、训练、评估，量化比较自动标注是否节省人工时间而不损害最终精度。

操作细则：[12-training-report-and-benchmark.md](12-training-report-and-benchmark.md)、[13-vlm-autoyolo-integration.md](13-vlm-autoyolo-integration.md)。
