# 02 · API / 数据契约（草案 v0.1）

> **以下路由及字段均为待实现的接口设计，不是当前可调用的 API。** 已有 `/api/upload`、`/api/process/{task_id}`、`/api/task/{task_id}` 保持兼容。

## 实体及关系

```text
Task (原始上传视频, 1) ───────< AnalysisRun (多个模型多次实验)
                                      │
                                      ├─ ModelVersion(s) / ConfigSnapshot
                                      ├─ Progress, error, metrics_summary (DB)
                                      └─ manifest.json
                                           ├─ tracks.jsonl
                                           ├─ heatmap.json
                                           ├─ masks/00000012.png
                                           ├─ per-frame.jsonl
                                           └─ metrics.csv / summary.json

AnnotationDatasetVersion ──(引用)──> ModelVersion
```

## 分析 Run API

| 请求 | 参数/响应 | 用途 |
| --- | --- | --- |
| `POST /api/v1/tasks/{task_id}/analysis-runs` | `{kind, models, settings}` → `202 {run_id,status:"queued"}` | 不阻塞、入队；支持重复跑同一视频 |
| `GET /api/v1/tasks/{task_id}/analysis-runs` | `{items:[...]}` | 一视频多版本分析历史 |
| `GET /api/v1/analysis-runs/{run_id}` | 状态/进度/版本/摘要/artifact URL | 轮询和结果页 |
| `GET /api/v1/analysis-runs/{run_id}/tracks?start_ms=&end_ms=&cursor=` | `{items:[...],next_cursor}` | 分时间区间读取轨迹；默认分页 |
| `GET /api/v1/analysis-runs/{run_id}/heatmap` | 栅格数据/平面类型/归一化策略 | 画面级二维热图 |
| `GET /api/v1/analysis-runs/{run_id}/masks?frame=` | PNG 图或校验签名的媒体 URL | 视频同步健康掩膜 |
| `GET /api/v1/analysis-runs/{run_id}/summary` | 指标、限制说明、模型信息 | 图表、CSV 导出 |
| `POST /api/v1/analysis-runs/{run_id}/retry` | `202`，状态重新入队（有次数限制） | 失败后重试 |
| `GET /api/health` | `200 {"ok":true}` | 真实 HTTP 健康检查 |

任务状态：`queued → running → completed | failed`，可选 `cancel_requested → cancelled`。状态转换须在 DB 中原子控制；同一 run 禁止两 worker 并发消费。失败/取消保留错误原因与已生成元数据。不要允许用户传任意服务器模型文件路径作为 API 参数。

### 创建 Run 示例

```json
{
  "kind": "joint",
  "models": {
    "fish": "fish-detector:original-v1",
    "coral": "coral-segformer-v2:baseline-95"
  },
  "settings": {
    "tracker": "bytetrack",
    "tracking_frame_stride": 1,
    "coral_sample_every_seconds": 2,
    "confidence_threshold": 0.25,
    "heatmap": {
      "space": "image_plane",
      "grid_width": 64,
      "grid_height": 36,
      "weight": "dwell_seconds"
    }
  }
}
```

返回的 model id 仅用于从**受信任的注册表**查找权重，不接受不受控文件路径；所有参数落库为不可变 `config_snapshot`。

## 已确认的画面热力图语义

- 已确定 coordinate_space=image_plane，若相机移动或运动未知，UI 常驻提醒非 GIS/海底真实位置。
- 所有 heatmap 正式输出均需要含 track-seconds raw_grid 与非统计用途的 normalized_display_grid 两者；仅将原始 track 观测点按有效时间段积分，不由浏览器 render 帧叠加。
- 当前 examples 已使用 raw/display 双字段，见 [08-video-heatmap-and-datamining.md](08-video-heatmap-and-datamining.md)。

## fish tracking 记录（schema = fish-tracks/v1）

每个 `track_id` 仅保证在 **一个 AnalysisRun 内**有意义，不跨视频/模型沿用；对应 `frame` 或 `timestamp_ms` 不可缺失。

```json
{
  "run_id": "ad3f3ac7-2c16-4f4e-8aab-27a954c6d121",
  "track_id": 12,
  "frame": 150,
  "timestamp_ms": 5000,
  "class_id": 0,
  "label": "fish",
  "confidence": 0.93,
  "bbox_xywhn": [0.42, 0.31, 0.12, 0.08],
  "center_xyn": [0.48, 0.35],
  "observed": true
}
```

- `xywhn` 约定为左上角的 x/y + 宽高，**不是** Ultralytics 的中心式 xywh；录入时显式转换。
- 空缺帧可为显示插值，但是 `observed:false`，不得伪造为真实检测；数据挖掘默认只用 observed points。
- `track_id` 来源必须为跟踪器的 `boxes.id`，不能由浏览器临时猜测。
- 若 `fps` 不可靠，以解码器的 PTS 为准，导出同时带 `frame` 和 `timestamp_ms`。

## heatmap 结果（schema = fish-heatmap/v1）

```json
{
  "coordinate_space": "image_plane",
  "camera_motion": "unknown",
  "width": 64,
  "height": 36,
  "weighting": "dwell_seconds",
  "sampled_duration_seconds": 25.0,
  "track_filter": "all",
  "normalization": "max",
  "value_unit": "track_seconds",
  "values_raw": [[0.0, 0.02, 0.0]],
  "values_display": [[0.0, 1.0, 0.0]],
  "interpretation": "画面相对占据度，不代表海底地理坐标或鱼类种群密度"
}
```

上方 `values` 为**字段形状示意**（并非完整 64×36 栅格），正式接口须断言 values 维度为 height×width，数据非负且有明确分母；可选提供压缩/PNG 热图文件。移动机位必须展示 `image_plane` 警示，不能标注地理坐标。权重 `dwell_seconds` 表示各轨迹观察时间加权，一帧多次检测不能重复计入。

## coral mask 与类别表（schema = coral-health/v1）

采用每帧**单通道、整数类别索引 PNG**，与分辨率一致，避免每一像素 JSON 化。初始建议：

| index | class | 释义 |
| --- | --- | --- |
| 0 | other_benthic_or_background | 非目标 / 背景；统计底栖覆盖率时需进一步拆 ROI |
| 1 | living_unbleached_coral | 可判读的存活且未明显白化珊瑚 |
| 2 | bleached_coral | 可判读的活体白化/明显褪色（细化需要专家标准） |
| 3 | dead_coral | 可判读为死亡的珊瑚骨骼/基质 |
| 4 | algae_covered_coral | 藻类覆盖珊瑚结构（须有专家判读证据） |
| 5 | unknown_coral | 珊瑚确知但健康状态无法确认 |
| 255 | ignore | 模糊/遮挡/无效像素，训练损失和统计剔除 |

**注意：** 这不是 CoralscapesV2 原始 95 类的 ID。预训练 SegFormer 模型实际有 96 logits：source=0 为 void，必须变为 target=255（ignore），有效 source=1..95；本系统 target=0 才表示 other/background。必须从模型 `id2label` 提取官方标签，创建**经专家审核**的 `source_label → target_class` 映射，并记录映射版本。没有明确映射的原始类别落入 `unknown` 或 `ignore`，不可凭颜色自动当“健康”。

## 核心统计定义

- `coral_healthy_fraction` = 可确认未白化的活体珊瑚像素 / (可确认未白化 + 白化的活体珊瑚像素)。
- `coral_bleached_fraction` = 白化活体珊瑚像素 / (可确认未白化 + 白化的活体珊瑚像素)。
- `visible_coral_cover` = 可确认珊瑚像素 / 指定**底栖采样 ROI**的有效像素；未设置 ROI 时不输出正式覆盖率，只输出画面描述性占比。
- `track_count` = run 内不同 `track_id` 的个数；注明不是去重生物个体数。
- `total_path_length_px` = 相邻 `observed` 轨迹点的像素距离之和；非真实米数，时间间隙须设阈值。

统计结果必须携带 `unit`, `denominator`, `model_id`, `dataset_version`, `camera_motion` 和 `limitations`；前端如缺少可靠分母则显示 N/A，不假造百分比。

扩展：细粒度珊瑚训练协议：[07-coral-training-blueprint.md](07-coral-training-blueprint.md)，来源 [11-sources.md](11-sources.md)。


## v2 追加契约：量化训练与大屏（尚未实现）

- TrainingRun → EvaluationRun → TrainingReport → ModelVersion：训练记录、固定测试集评估、文字报告、权重审批**分层解耦**。AI 不能写入 metrics，不接受只有 curves 无 GT 的标量“准确率”。
- DatasetImport / AnnotationProvenance：记录工具/模型/提示词/时间帧、原始伪标签/人工审核状态、转换 hash；只有 expert_approved 的数据允许进入正式科研评测。
- WallSummary/WallView：返回 AnalysisRun/EvaluationRun ID、数据新鲜度、相机运动、ROI、模型状态、带 metric_source/denominator 的有限关键指标；null 必须显示 N/A 和缺失原因。
- 接口建议见 [12-training-report-and-benchmark.md](12-training-report-and-benchmark.md) 和 [14-visual-wall-research-and-spec.md](14-visual-wall-research-and-spec.md)，三份 JSON fixture 在 fixtures/mvp 中。
- UI 必须标明 screen=image_plane 不代表海底地理位置；未获 GT 的 mAP、F1 不得显示 0 或臆造分数。
