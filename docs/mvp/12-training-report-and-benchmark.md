# 12 · YOLO / MOT / 珊瑚训练量化评估体系

> 2026-10-21 修订。参考 [YOLO Report Analyst](https://github.com/xiangshenchi/yolo-report-analyst) 的七章报告提纲（MIT），但**不等价于直接集成性能评测引擎**。这个仓库实际上是一份 SKILL.md 指令，输入 results.csv / args.yaml / log / 曲线文件，由智能助手生成叙述性报告。[S21][S22]

## 1. 必须建立的“真实计算 → 可解释报告 → 可视化”闭环

- 离线训练工具输出原始训练记录（CSV、yaml、图、val 预测、模型 sha256），独立 EvalRunner 使用**冻结的数据集版本**计算真实指标，生成不可变 EvaluationRun（带 source_artifacts、unit、denominator、commit、config 和环境）。
- Deterministic Parser 解析 YOLO 数据；指标计算必须由可信的评测库/明确公式执行。AI/Skill 仅负责生成自然语言观察、检查异常和建议下一组实验，**不能反向填写精度数值**。
- 报告分七章：**配置与数据**、**基线和最佳模型的量化比较**、**收敛分析**、**按类别混淆和困难样本**、**推理性能**、**诊断与实验建议**、**结果局限与复现信息**。保留 Markdown/可打印 HTML/PDF；Word 为可选离线导出。
- 同步用于训练工作台、模型版本列表及大屏的 API，不再让 frontend 独立以不同公式计算 mAP、FPS、白化率或热图积分。

## 2. 核心模型评估矩阵

| 域 | 必算指标 | 评估集/单位 | 不可替代/混淆 |
| --- | --- | --- | --- |
| Fish Detection（现有单鱼类 YOLO） | AP50 / AP50-95, P, R, F1, PR curve, FP/image, FN, latency p50/p95, FPS | 站点/视频隔离的人工 bbox 真值；按同一 conf/IoU 协议评估 | 一类 fish 不需要声称 per-species；mAP50 不等于种群计数精度 |
| MOT/鱼轨迹（ByteTrack vs BoT-SORT） | HOTA, IDF1, ID switches, fragmentation, track coverage, FPS | 连续视频、帧时序与人工 track ID 真值；先做 IDF1/IDSW，HOTA 有充分标注再加 | results.csv **没有**真实 IDF1/HOTA；必须从 track 真值算 |
| Image-plane 热力图 | raw grid 积分守恒误差、时窗一致性、FPS/时间对齐、定位误差/热点一致性 | PTS 真实轨迹和独立测试序列；单位 track_seconds | 不报 m² 鱼密度，也不能用浏览器渲染帧累计热度 |
| Coral 6-class semantic | per-class IoU, macro-mIoU, Dice, bleached P/R/F1, dead↔bleached confusion | 由专家复核的独立珊瑚 mask；source 0=void 不进损失和分母 | 不能拿 Coralscapes 95 类论文成绩当本地 6 类 F1 |
| Coral area / ROI | 画面有效底栖 ROI 内分数、绝对误差（百分点）、unknown% / ignore% | 指定样方/ROI，按 site bootstrap CI，校准/质量分层 | 重叠视频帧不是独立底栖样本，不能直接声称海底面积覆盖率 |
| 计算资源 | 模型/权重尺寸，初始化耗时，峰值显存，平均功率(可测时)，FPS，p50/p95, OOM 频率 | 固定设备、推理尺寸、batch、预热次数、软件版本 | 训练 loss / 1÷inference_time 都不能直接代表端到端流播放 FPS |

**对照策略**：冻结 test set，先看 validation 选择模型，最后一次独立 test；记录 B0 原始鱼模型、B1 + 更多标注、B2 数据增强、B3 输入尺寸；MOT 2 tracker；珊瑚 B0 zero-finetune、B1 finetuned 等，至少同时记录收益与时延开销。

## 3. 严格的 BEST / LAST 与通用性

YOLO Report Analyst 示例默认**按 mAP50 寻找最佳 epoch**，还把 mAP50≥0.90 直接描述为“工业级优秀”。这些仅是项目中的启发式写作模板；SITP **禁止照搬**：
1. 优先记录训练框架实际保存的 best.pt 对应的 fitness/监控指标；另记录 best_mAP50_epoch、best_mAP50_95_epoch 与 last_epoch，**明确各自依据**，二者可能不同。
2. train/val 的逐 epoch 最优值不是独立 test 结果，也不等于“鱼轨迹精度”或“白化生态准确率”；严禁跨数据集/版本直接比较。
3. 不按单一 mAP 数值自动判“科研可用”或“工业可用”；在实际海域样本、类别漏检成本、错误分布和专家复核后设应用门槛。
4. 同一原视频的抽帧属于一个 group，禁止随机跨 train/val/test。每个模型比较必须在相同 group、label taxonomy、resolution 和 confidence/NMS 协议下完成。

## 4. 版本化评估实体与数据关系

推荐独立四层实体：
- **TrainingRun**（experiment_id、task_type=detect/segment、model family、training_dataset_hash、git_SHA、seed、hyperparams、source files、train state）
- **EvaluationRun**（evaluation_id、training_run_id / model_version_id、eval_dataset_hash、evaluation_protocol_version、metric_json artifact、confusion / PR 和 harder sample URIs、GPU inventory、execution time）
- **TrainingReport**（report_id、evaluation_run_id、report_template_version、AI_prompt_version、Markdown/HTML/PDF artifact、warnings、human_review_status、generated_at）
- **ModelVersion**（模型权重 hash、训练/评估 lineage、模型用途与部署状态 candidate/approved/rejected，先不上线未经测试模型）

**不可变关联**：评测重复执行生成新 EvaluationRun，不覆盖上一组；训练 report 可多次重写但原始 metric JSON 不可被 AI 更新。标注和模型版本的 Git/DVC/MLflow ID 始终可追溯。

## 5. 输入契约与输出

Deterministic ingest：
- fish YOLO: results.csv, args.yaml, train.log, best.pt / last.pt checksum, data.yaml, per-class val.txt/metrics.json, conf matrix raw (如可用), PR 数据或图、数据样例。
- fish MOT: MOTChallenge-like GT (frame,id,x,y,w,h), detection/track predictions, tracker params, frame PTS, video/image sizes。
- coral: mask (uint8 0..5/255), 96-logit source model config (void 0), taxonomy mapping hash, eval images/ROI, model outputs and per-site metadata。
- 任何缺失字段 must be null + missing_inputs[] + availability flag，禁止在报告自动补出未计算或缺失的数字。截图/曲线图片仅作辅助诊断，统计来自原始数值。

新接口（待评审）：
- POST /api/v1/evaluations：指定 model_version_id、dataset_version_id、protocol_id 入队；自动校验 split。
- GET /api/v1/evaluations/{id}：只读结果+置信区间、metric_source、单位、限制。
- GET /api/v1/model-versions/{id}/evaluations：历史比较。
- POST /api/v1/evaluations/{id}/reports：将冻结 metrics 传给 report generator；AI 若不可用仍产出 deterministic Markdown。
- GET /api/v1/reports/{id}/export?format=markdown|html|pdf。
- GET /api/v1/analytics/model-quality-summary：大屏只接聚合的版本化 metrics，不直接扫训练日志。

训练导入与报告生成只在离线 training/benchmark worker 进行；显示页面不允许提供任意服务器路径导入，上传路径校验、解压防 Zip Slip/Zip Bomb。所有外部文本或图像分析内容不允许成为执行命令指令。

## 6. 推荐可验证的开源工具

- **Ultralytics val/export** [S01]：检测标准评测及训练产物收集（核对当前 SITP 固定版本）。
- **TrackEval** https://github.com/JonathonLuiten/TrackEval [S24]：HOTA / IDF1 等 MOT benchmark 计算，与真实 GT 对齐。
- **torchmetrics** https://github.com/Lightning-AI/torchmetrics [S25]：珊瑚语义指标/混淆矩阵计算，可用 NumPy 校验。
- **MLflow** [S09]：不同训练 Run 的 params、metrics、artifact 跨实验对比。
- **YOLO Report Analyst** [S21,S22]：七章叙述模板和异常诊断问题清单；不作为 metric truth，保留 attribution/MIT。

## 7. 科学、工程与 UI 验收

A. **指标真实性**：可用原始预测/GT 在 CI sample fixture 上完全复算（误差规定）；将虚构示例值写成显式 null。
B. **公平对比**：同数据、同评测协议、同硬件；独立 held-out test，无视频泄漏；报告展示样本数与置信区间。
C. **四类页面**：实验列表 / 训练 epoch 曲线 / best-vs-baseline 对比 / 质量报告；大屏只放经审核最重要的 3–5 个摘要指标，深层指标进详情页。
D. **失败态**：无 source file、只有曲线图、没有 GT、样本数太少、loss 趋势异常、鱼类暂未标 ID、珊瑚只有伪标签，都要显示“不可评估/数据不足”，不得补估分数。
E. **最低科研可信要求**：可重复；有 baseline；有定量证据；有错误分析；能区分真正 GT 与 VLM/SAM 伪标签。目标精度门槛将在取得本地代表性验证数据后讨论，不能预设“mAP0.9 必须通过”。
