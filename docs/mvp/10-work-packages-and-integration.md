# 10 · 可并行实施的开发包与主分支集成门槛

> 本页细化 [04-backlog.md](04-backlog.md)；架构文档给分工的“可独立交付模块”，不是把全部人安排改 App.vue。每个任务均要求契约 fixture → 算法/后端/前端代码 → 用例 → 交付评审。

## P0 依赖顺序

| 开发包 | 负责人/边界 | 独立输入 | 独立输出 | DoD |
| --- | --- | --- | --- | --- |
| PKG-00 Infra | A: API/Worker/DB | MP4 / Task ID | AnalysisRun + model_registry + artifact store | 旧接口不回归，任务重试/重启可恢复 |
| PKG-01 Fish tracking | B: 仅 fish adapter、tracking.py | 源视频、原 YOLO .pt、config | track JSONL + id + frame PTS | 至少 2 段视频有人工 ID test、IDF1/IDSW |
| PKG-02 Fish heatmap | B/E: metrics.py 的 track module | tracks JSONL + ROI + [t0,t1] | raw grid + display grid + confidence | 时间积分可守恒、全零/断轨/重放单测 |
| PKG-03 Coral dataset | C/E: ml/datasets、CVAT 工具链 | site 原片 + CoralscapesV2 | 95 id mapping + gold masks + grouped split | 标注源证据、专家 QA、版本哈希 |
| PKG-04 Coral baseline | C: models/coral_segformer.py | 预训练 96 logits + 视频抽帧 | source 95 classes / target 6 classes mask | 0 void→ignore + 95→6 映射单测、域内/域外 baseline |
| PKG-05 Coral finetuning | C/E: ml/train, evaluate | PKG-03 gold set, PKG-04 ckpt | model checkpoint + report | 3 seeds / macro mIoU / bleached F1 / site split |
| PKG-06 Video overlays | D: Vue Canvas overlay 层 | PKG-01/02/04 fixtures | boxes/ID/trails/heat/mask | 暂停/seek/fullscreen/DPR/letterbox 对齐 |
| PKG-07 Mining dashboard | D/E: charts + summary | run summary / time bins | 鱼轨迹和珊瑚站点趋势与 CSV | 统计不把 track count 称种群数；单位分母一致 |
| PKG-08 Integration | A/E: CI, Docker, hardening | 全部 adapter/fixture | 健康检查、镜像、联调脚本 | 内部试用与权限/安全检查，smoke 视频结果可回放 |

### 实施过程建议

1. Day 0 由全组审阅 02-contracts、07-coral-training-blueprint、08-video-heatmap，确认标签 0/255、归一化坐标、camera_motion、model provenance、分析 Run 对象含义。未确认项在 PR 描述标为 proposal。
2. M0 API 契约可先打通“mock worker”（无需 GPU），并修正 model_path、Docker healthcheck；F/B/C/D 立即并行用 fixtures。
3. 鱼类和珊瑚两组分别提交 **模型适配器**，不触碰互相训练目录；各自附上一段 5–30s 测试片或来源可追溯的假 fixture，不在 PR 中嵌入受版权限制视频。
4. 前端只抽 overlay 层与 composable，保持 Artplayer 和整体主界面视觉；ECharts 按需加载，做到图表与导出共用后端指标定义。
5. 完整联调后才引入 MLflow、FiftyOne、CVAT 辅助研发容器；不要让非视觉团队先花时间搭微服务/分布式队列。

## 推荐的目录与所有权

```text
backend/
  app/
    analysis/
      contracts.py            # 公共 schema + dataclasses
      fish.py                 # B 鱼类 YOLO track adapter
      heatmap.py              # B/E 原始热图统计
      coral.py                # C SegFormer adapter
      taxonomy.py             # C 官方 95→6 ID 映射
      metrics.py              # E 科研指标
      storage.py              # A 文件和 manifest
    api/analysis.py           # A DRF routes
    management/commands/run_analysis_worker.py # A
  ml/                         # C/E 完全离线
    datasets/
    preannotate.py
    train_coral.py
    evaluate_coral.py
    register_model.py
  media/analysis/<run_uuid>/
frontend/src/
  api/analysis.js
  composables/useAnalysisRun.js
  components/overlays/{Boxes,Tracks,Heatmap,CoralMask}...
  components/analysis/{SummaryCharts,ModelCompare,DatasetInfo}...
fixtures/mvp/
docs/mvp/
```

## 联调测试切片

- A 给出可创建及轮询 run 的 fake/real worker API，确保老版本 API 返回结构不改变。
- B 输入两条两秒以上鱼类样本视频，分别输出 ByteTrack 与 BoT-SORT，统计 IDSW、FPS；同时保留原始检测数。
- C 对 10 帧人工复核图像做 96 logits/0 void/95 细类/6 类映射正确性测试；输出 2 张可叠加 PNG 验证颜色与分辨率。
- D 在浏览器中读取 fixtures 渲染鱼 bbox、ID、热度栅格、珊瑚 mask；全屏/拖动/切原片不乱。
- E 使用 dummy mask (无珊瑚、全 ignore、全白化、死骨骼混杂) 验证比例公式 + null 语义。
- 组织 3–5 个站点/潜次/视频的不重叠 heldout test，保留可复现实验 manifest。

## 合入/发布治理

- 推荐 PR 小于一个子功能，命名 conventional 英文标题，body 中文：背景、变更点、风险、接口 schema、测试、耗时/显存、许可证。
- 不允许将原始用户视频、外部大量训练集或 pretrained checkpoint 直接提交 Git；保存引用 URI/sha256 与保密权限。
- 依赖变更必须锁版本、列出 license、跑 smoke test；有登录要求/gated weights 不能假设所有研发机器已授权。
- 两阶段验收：**工程通过**（接口和 UI 可复现）与 **科学可信**（专家标签、站点独立测试、混淆与不确定性）分别标记；不把工程演示冒充训练模型科学准确率。


## 续增 PKG-09–12：面向训练量化和信息大屏

- **PKG-09 EvaluationRunner（A/E）**：fish bbox held-out AP50/95、fish IDF1/HOTA、coral IoU/Dice/bleached F1/ROI 误差；优先接 TrackEval/torchmetrics；必须引入 provenance 与 missing metrics 的真实语义。
- **PKG-10 Report Generator（E/D）**：读取不可变评测 JSON，基于 YOLO Report Analyst 七章节输出机器可信报告；可选 AI 故障建议不可写入 metric；适配 /wall/train。
- **PKG-11 Annotation Acceleration PoC（B/C）**：VLM-AutoYOLO 独立仓库与导出格式 PoC，仅导入审核通过的数据；鱼 bbox 与珊瑚 health semantic mask 明确分线；验证版权+CUDA。
- **PKG-12 Ocean Wall UI（D/E）**：原有视频 Artplayer 与热图位于主视觉中心，ECharts + 少量 DataV-Vue3/自定义 CSS，三页 /wall /wall/train /wall/evidence，不复制低代码编辑器的完整系统。
依赖、API、验收详见 [15-mvp-v2-milestones.md](15-mvp-v2-milestones.md)。
