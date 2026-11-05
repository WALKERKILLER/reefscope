# 珊瑚白化分析

## 模型与注册

本页说明本地珊瑚 Run 的运行方法，契约见 [珊瑚白化分析契约](../specs/draft-coral-bleaching-analysis.md)。当前支持组员交付的 `reef-coral-final/v1` 单文件权重：冻结的 CoralscapesV2 SegFormer-B5、新训练的非白化分支和图像特征保护（guard）都在同一个 `.safetensors` 中。推理代码随仓库分发在 `backend/app/analysis/vendor/coral_model.py`，与交付版本逐字节一致，来源见 [vendor 说明](../../backend/app/analysis/vendor/README.md)。

Worker 环境需要 `requirements.txt`（含 Transformers 4.57.1 与 safetensors）和匹配驱动的 CUDA PyTorch。把权重放进 `CORAL_MODEL_ROOT`（默认 `backend/models/`），从 `backend/` 注册：

```bash
python manage.py register_coral_model coral:scs-enhanced-v2 models/coral_scs_enhanced_v2.safetensors --evidence /path/to/evidence
```

注册先按 JSON 头检查格式、三类标签和张量命名，不读取 pickle；再在 CPU 上完整加载一次，校验冻结底模指纹。`--evidence` 指向交付包的 `evidence/` 目录，只导入 `assessment.json` 与 `test-report.json` 的全图类别指标、评估语境和文件摘要。模型 ID 不可覆盖；权重变化时注册新 ID。

## 创建与执行

以已有 Task 创建 coral Run：

```json
{"kind": "coral", "models": {"coral": "coral:scs-enhanced-v2"}, "settings": {"sample_every_seconds": 2, "camera_motion": "unknown"}}
```

`sample_every_seconds` 取 0.5–60。鱼类模型不能用于 coral Run，反之亦然。Worker 可按种类分开运行；交付代码加载时会关闭 TF32 并把 PyTorch CPU 线程设为 6，分开进程可避免影响鱼类 Run：

```bash
python manage.py run_analysis_worker --kind fish
python manage.py run_analysis_worker --kind coral
```

Worker 顺序解码视频，每个采样区间取第一帧，时间戳规则与鱼类相同。CUDA 支持 BF16 时使用交付验证的 BF16，否则使用 FP32，摘要记录实际设备与精度。超过 1800 个采样帧的 Run 失败，需加大采样间隔。

## 产物与查询

每次 attempt 写入 `masks/{frame:08d}.png`、`frames.jsonl`、`summary.json` 与 `manifest.json`。掩膜是与源帧同尺寸的单通道 PNG，像素值即类别：0 背景、1 非白化、2 白化。帧记录包含时间、`background_separated`、guard 分数和各类像素数。manifest 记录全部文件摘要，每个掩膜必须恰好被一条帧记录引用。

- `GET /api/v1/analysis-runs/{run_id}/masks`：采样帧索引。
- `GET /api/v1/analysis-runs/{run_id}/masks?frame=N`：该帧 PNG，产物不可变，响应可长期缓存。
- `GET /api/v1/analysis-runs/{run_id}/summary`：接受 `start_ms`、`end_ms` 与 `export=json`，返回白化像素占比、珊瑚像素占比、白化占珊瑚像素和逐帧序列。

## 证据边界

guard 未启用的帧没有背景类，1 包含背景，因此珊瑚像素占比与白化占珊瑚只统计已区分背景的帧。比例按采样帧像素合并，相邻采样帧重叠，不是独立样方，也不是底栖覆盖率；覆盖率需要批准的底栖采样 ROI，保持 N/A。非白化不区分活体、死亡或藻覆，与 `coral-health/v1` 六类不同。

交付方本地测试集没有白化真值，平台不报告白化识别精度。交付证据是对此前已查看测试集的回归复核，不是独立测试；界面与导出按此标注，不与平台测得值混排。
