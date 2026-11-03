# 交付珊瑚白化分割模型的视频分析

Artifact-Version: 1
Status: Draft

## Intent

组员交付了珊瑚分割权重 `coral_scs_enhanced_v2.safetensors`（格式 `reef-coral-final/v1`）与配套推理代码。本契约把它接入现有 Run 平台：对已上传视频按时间采样帧，生成与源帧对齐的单通道类别掩膜，在工作台和监测大屏叠加，并给出同源描述统计。范围覆盖 #20 的推理适配、#22 的掩膜图层，以及 #23、#28 中依赖该模型的珊瑚统计与展示。

不在范围：`coral-health/v1` 六类健康结论与专家映射（#19）、再训练与微调（#21）、独立评估执行器（#25）、底栖 ROI 覆盖率、实例分割、`kind=joint` 联合 Run。

约束：权重、交付证据原件、视频和预测图不进 Git；API 只接受注册模型 ID；推理沿用交付代码，不改动其数值路径，取舍见 [0005](../adr/0005-coral-delivered-inference.md)。

## Contract

### 模型输出语义

掩膜采用 `coral-bleaching/v1`：0 背景，1 非白化，2 白化。2 来自冻结的 CoralscapesV2 SegFormer-B5，对应源模型 19 个 bleached 类，两种分支下完全相同。权重内置的图像特征保护（guard）逐帧决定是否启用新训练的非白化分支：

- 启用时（`background_separated=true`）：0 为背景，1 为非白化珊瑚。
- 未启用时：帧内没有 0，1 表示所有非白化像素，包含背景、水体和沙地。

模型不输出 ignore/255。非白化不区分活体、死亡或藻覆，不等于 `coral-health/v1` 的 `living_unbleached_coral`。

### 注册

`register_coral_model <id> <file> [--evidence <dir>]` 只读取 `CORAL_MODEL_ROOT` 内的 `.safetensors`。先按 JSON 头校验格式、三类标签、`predicts_ignore=false` 与张量命名（只含 `base.*`、`head.*` 与两个 guard 参考张量），再用随仓库分发的交付推理代码在 CPU 完整加载一次，包括冻结底模指纹校验。

`ModelVersion` 增加 `kind`（fish/coral，已有记录为 fish）与 `metadata`。metadata 保存源模型、revision、许可证、源模型聚合方式与适用范围、推理参数和训练范围。`--evidence` 只导入 `assessment.json` 与 `test-report.json` 中声明的全图类别指标、评估语境与文件摘要。模型 API 返回 kind 与 metadata，不返回路径。模型 ID 不可覆盖。

### Run 与产物

- `POST /api/v1/tasks/{id}/analysis-runs` 接受 `kind=coral`、`models={"coral": id}`。模型 kind 不符返回 400 `model_kind_mismatch`。settings 只允许 `sample_every_seconds`（0.5–60，默认 2）与 `camera_motion`。
- Run 的 kind 取自模型。轨迹与热图接口对 coral Run 返回 400 `run_kind_not_supported`；summary 按 kind 分派。
- Worker 可用 `--kind` 只领取一种 Run；租约、attempt、重试与失败码规则与鱼类相同。
- 顺序解码，时间戳规则与鱼类共用同一实现：PTS 优先，fps 有效时才按帧号回退并计数。每个采样区间取第一个时间不早于区间起点的帧；超过 1800 个采样帧时失败 `too_many_samples`。
- CUDA 支持 BF16 时使用交付验证的 BF16；否则用 FP32。摘要记录设备、精度、torch 与 Transformers 版本。
- 每个采样帧检查：掩膜为源帧尺寸的 uint8、只含 0/1/2、白化像素与底模预测一致、未启用 guard 时没有 0。任何一项不满足即失败 `invalid_model_output`。
- 产物：`masks/{frame:08d}.png`（单通道 L 模式，像素值即类别），`frames.jsonl`（`coral-frames/v1`：帧号、时间、尺寸、`background_separated`、guard 分数、各类像素数、掩膜文件与摘要），`summary.json`（`coral-summary/v1`），`manifest.json` 记录全部产物摘要。每个掩膜必须恰好被一条帧记录引用，否则不能发布 completed。

### 查询

- `GET /api/v1/analysis-runs/{id}/masks` 返回采样帧索引，不含路径；`?frame=N` 返回该帧 PNG。未完成为 409，未知帧为 404，非 coral Run 为 400。
- `GET /api/v1/analysis-runs/{id}/summary` 对 coral Run 只接受 `start_ms`、`end_ms`、`export=json`，返回 `coral-window-summary/v1`，按采样帧像素合并：
  - `bleached_pixel_share` = 白化像素 / 全部采样帧像素。
  - `coral_pixel_share` = (非白化 + 白化) / 已区分背景帧的像素；没有这类帧时为 null，原因 `no_background_separated_frames`。
  - `bleached_coral_fraction` = 白化 / 已区分背景帧的珊瑚像素；分母为 0 时 null，原因 `no_coral_pixels`。
  - `coral_cover` 恒为 null，原因 `requires_approved_benthic_roi`；`bleaching_accuracy` 恒为 null，原因 `no_local_bleached_ground_truth`。
  - 每个指标带单位、分母、来源和原因；同时返回逐帧序列与解读限制。
- 采样帧相互重叠，不作为独立样方；比例是画面像素占比，不是底栖覆盖率。

### 工作台与大屏

- 分析面板分“鱼类”“珊瑚”两个视图，各自管理 Run。珊瑚视图提供 Run 选择与创建、掩膜图层（开关、按类别显示、不透明度）、统计、逐帧曲线和来源。
- 叠加层使用播放头之前最近的采样帧，且仅在一个采样间隔内显示；画面注明掩膜来自哪个时刻与当前帧各类像素占比。提供填充、轮廓及两者结合的显示方式（轮廓不随不透明度变淡）、与原画面的分隔线对比、光标处类别读数，以及视频下方的采样帧时间线（点击定位，未分离背景的帧单独标示）。未区分背景的帧只绘制白化类，并注明原因。掩膜位于鱼类图层之下，使用现有 letterbox 与 DPR 映射；颜色固定且图例带文字。
- 大屏增加珊瑚面板（珊瑚像素占比、白化占珊瑚、当前掩膜，并紧邻数值注明白化未经本地真值验证）与“珊瑚”图层按钮；覆盖率保持 N/A 并给出珊瑚 Run 的原因；有未分离背景的采样帧时，证据边界列出帧数。只有珊瑚 Run 时显示珊瑚面板与图层，鱼类区域保持等待状态。
- 视频库的“重新分析”只重排鱼类 Run；珊瑚 Run 在珊瑚视图中创建。
- 交付方指标标明“回归复核，测试集在开发中已查看，非独立测试”，不与平台测得值混排。

## Plan

1. 契约、决定记录与契约文档同步（本切片）。
2. 后端：迁移、注册命令、交付推理代码、采样适配器、Worker、API、测试与开发者文档。
3. 前端：珊瑚面板、掩膜图层、统计、来源与大屏。

各切片独立 PR 并按顺序叠加，留给维护者验收，不自动合入。

## Verification

- `python3 scripts/check.py`、`git diff --check`；`backend/` 中 `manage.py check`、`makemigrations --check --dry-run`、`manage.py test`；`frontend/` 中 `npm ci`、`npm run build`。
- Django 测试覆盖：注册拒绝根目录外文件、非 safetensors、错误格式与标签、截断头；kind 与模型不符；采样间隔越界；未被索引的掩膜阻止发布；掩膜接口的 404/409/400；鱼类接口拒绝 coral Run；像素合并、窗口筛选与两种缺失原因。
- 本地 GPU：注册交付权重并在授权视频上完成 coral Run，记录设备、精度、耗时与显存；适配器掩膜与交付命令行在同一帧上逐像素比较；平台运行时与交付验证运行时在同一帧上逐像素比较并报告差异。
- 浏览器：暂停、seek、全屏与缩放下掩膜对齐；按类别显示；大屏在既定分辨率与两套主题下一屏无溢出。

## Evidence

- 后端（切片 2）：`manage.py test` 31 项通过，`makemigrations --check` 无变更。本地 RTX 4060 Laptop 注册交付权重并完成授权 4K 视频的 coral Run：30 个采样帧，全部区分背景，无白化预测；每帧约 0.97 s，峰值显存约 1.3 GB；设备 `cuda:0`、精度 BF16。适配器掩膜与交付命令行逐像素一致；平台与交付验证运行时的差异见 [0005](../adr/0005-coral-delivered-inference.md)。
- 前端（切片 3）：`npm run build` 通过。本地 Chromium 中，暂停在 10.3 s 时叠加层与同帧掩膜按 letterbox 缩放后的类别 1 像素 IoU 为 0.992；播放时当前采样帧随 2 s 采样间隔切换；仅白化着色路径只绘制类别 2。轮廓模式只绘制不透明边界像素、填充模式只绘制半透明像素；对比分隔线在 50% 时掩膜止于画面中线，鼠标拖动与方向键都能调整且不触发播放；光标读数给出类别与源帧像素坐标；采样帧时间线点击后跳到对应采样帧。大屏在 1280×720、1366×768、1600×960、1920×1080、2560×1440 一屏无溢出；深浅两套主题下珊瑚面板与大屏无低对比度或过小文字。图表描边色在两套主题下的色觉差异 ΔE ≥ 14。授权视频无白化预测，白化类着色只用合成数据检验。
