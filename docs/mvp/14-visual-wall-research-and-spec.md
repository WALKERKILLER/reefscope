# 14 · 水下生态信息大屏：可靠开源方案对照 + SITP 视觉/交互规范

> 2026-10-21 GitHub/Gitee、npm、项目 README 快照；Stars 只是粗略社会认可信号，不能代替维护、兼容性、许可核验。该页只作为**技术方案与可展示的视觉方向**，尚未实现前端代码。用户已明确“最终采用信息大屏风格”，因此本 ADR 的目标风格为 **ACCEPTED**，具体依赖选型为 PROPOSED。

## 1. 针对现有 Vue3 + Vite + Artplayer 的筛选标准

必须满足：
- 主视频/轨迹/热力/珊瑚 mask 占**视觉中心**，不是通用财务驾驶舱、不是地理地图；保持当前 Artplayer+Canvas 所有交互能力。
- 1920×1080 设计基准、支持 2560×1440 和 3840×2160，以及 1366×768 / 笔记本缩放，不能因 CSS scale 破坏视频指针/框映射。
- 实时任务/模型状态、时间窗、多图层、训练评测指标和可解释生态统计。
- Vue3 Vite 包兼容、成熟图表能力、可按需引入、许可证可复查、历史提交/问题维护。
- 美观且克制：深海墨蓝/青绿、银白文字、适度星点与分隔线；**少霓虹、无紫色泛滥、无重渐变/高频动画**，适合科研答辩和海洋展厅 24/7 播放。

## 2. 真实开源项目对比（GitHub 2026-10-21 快照）

| 方案 / 原始仓库 | Stars / 最近 push | 栈、许可与优点 | 核心风险 | 结论 |
| --- | --- | --- | --- | --- |
| **Apache ECharts** [S11,S27] | ~67.6k / 2026-10-13 | Apache-2.0，成熟时间序列、矩阵、分布图、联动，兼容 Vue3 | 大屏排版/装饰不是它的能力，必须配 Vue 布局和 Canvas | **主图表方案：采用** |
| **VisActor VChart** [S28] | ~1.85k / 2026-10-20 | MIT，活跃的视觉叙事图表、跨端等 | 与 ECharts 功能重叠；同时加入会增加维护和包大小 | **P1 图表替代 PoC，不与 ECharts 同时默认上主包** |
| **vaemusic/datav-vue3** [S29] | ~642 / 2024-10-21 | MIT；Vue3/Vite 专用 DataV 装饰/边框/数字滚动，可局部导入 | 维护活动偏少；最新 npm 1.7.4 已约两年 | **MVP 可选装饰组件（按需/隔离）** |
| **daidaibg/IofTV-Screen-Vue3** [S30] | ~498 / 2026-06-06 | MIT，Vue3/Vite/ECharts，含 scale-screen、动态大屏区块、预览 | 更像完整设计模板；需拆主题、Mock、适配方式；原视频坐标系统需单独处理 | **首选布局/观感参考，可挑剔地移植小组件** |
| **gcpaas/DataRoom** [S31] | ~869 / 2026-10-20 | Apache-2.0，活跃 Vue3 + SpringBoot 全栈低代码设计器，支持数十数据源/AI 创作 | 系统非常重，复用会引入第二后端/JDK/权限体系；开源 README 指当前无开放演示环境、商业版另售 | **参考大屏样式及未来模板编辑器，不并入 SITP 核心** |
| **L-noodle/vue-big-screen-plugin** [S32] | ~169 / 2021-05-25 | MIT，Vue3+TS+DataV/ECharts，1920×1080 scale | 技术代际旧，Node14、VueCLI4，维护已久 | **不作为主依赖，只参考静态截图** |
| **GoView (MTrun/go-view，Gitee)** [S33] | Gitee 资料，**未核实同名 GitHub 官方仓库 Star** | Vue3 大屏模板/可视化设计器，丰富编辑器与视觉案例 | 不同 GoView / GoViewPro 商业或社区版本许可证与可用性不同，GitHub 镜像真假难辨 | **视觉/低代码灵感参考；不直接复制代码或宣称许可已确认** |

推荐组合不是“最炫模板拿来套所有东西”，而是 **SITP 原有 Vue3/Vite + ECharts (数据图表) + 自定义 CSS Grid 信息大屏布局 + Artplayer/Canvas + 极少量 DataV-Vue3 装饰**。如组内要按模板赶工，优先拿 IofTV-Screen-Vue3 的网格/比例适配思想做参考。DataRoom/GoView 只做 UI/低代码产品调研参考。

## 3. 最终大屏的三种页面

### A. 海洋生态总览（Wall Overview，16:9 全屏，默认展示屏）

1920×1080 逻辑网格，**6% 标题+12% KPI+60% 主分析+18% 底部趋势/状态**，最后少量留白。中心视频占主分析区约 55–65% 宽，旁边统计小卡不要挤到遮挡画面。

```text
┌──────────────────── 生态视频智能解析 · 站点 / 日期 / 当前模型 ────────────────────┐
│ [处理视频]   [观测轨迹]  [检测准确性]  [白化识别]  [有效 ROI]  [分析状态/更新时间] │
├───────── 海洋环境/模型质量 ─────────┬────────────── 主视频与 Overlay ────────────┤
│ 站点 / 潜次 / 采样质量              │                                               │
│ 当前对象数 / 跟踪轨迹数（单位解释） │          Artplayer 视频 + Canvas Overlay     │
│ YOLO mAP50-95 / GT 样本来源        │          BBox / ID / tail / image_heatmap    │
│ 珊瑚专家审核率、模型不确定性       │          indexed coral mask 与类别图例       │
├────────────────────────────────────┤          跟随时间轴缩放和 seek               │
│ 有效 ROI 分类、白化与死亡比例      │                                               │
│ 根据抽样/ROI 资格显示 N/A         │                                               │
├────────────────────────────────────┴───────────────────────────────────────────────┤
│ 时间轴占据曲线 / 分类比例趋势 / 最近分析 Run / 模型版本对照 / 告警与科研限制       │
└────────────────────────────────────────────────────────────────────────────────────┘
```

- 主视觉为“活的科研可视化”，禁止用无关地图或 3D 地球占据中心；视频不支持播放时显示可定位错误。
- 缺少专家 GT 时大屏模型准确率显示「未验证」而不是凭训练曲线显示百分比。
- 左右面板信息密度优先精简，不为了填满每块屏展示不相关图或捏造指标。
- 大屏常驻注明：**鱼类画面位置热图 · 非海底真实地理密度**。移动机位必须额外提示。

### B. 训练质量大屏（Training Observatory）

- 上排：本轮训练/验证状态、best ckpt、实际监控 metric、模型版本、数据集 hash、测试集独立性。
- 主内容：epoch loss / precision-recall / mAP50-95、珊瑚 per-class IoU、bleached F1、混淆矩阵、错例/漏标关键帧对照。
- 下排：同一冻结测试集 baseline-vs-new（差值/置信区间/推理 FPS / GPU 显存）、AI 报告链接与警告。
- 不在大屏跑训练控制台或耗费性能的逐像素 mask 评测；训练由独立 worker。

### C. 数据采集/生态分析大屏（Ecology Evidence）

- 鱼类 image-plane 热图（带 raw track-seconds）、鱼类轨迹计数曲线、区域停留时间。
- 珊瑚 ROI segmentation 与专家 reviewed mask 对比、site/dive 质量切片、白化率和 unknown fraction。
- 对未完成 group split / 未审定 ROI 的值，不提供统计显著性/物理面积标签。

## 4. UI 设计 tokens（提议）

- 背景: #081B28（deep ocean）、底板: #102B39、边框: #24505B，强调: #61C7C2（seafoam）、次强调: #65AFCF（ice blue）、告警: #EABF70、危险: #EE8790，主文字: #EAF5F6、次文字: #9CB5C1。
- 深海风格不依靠全屏动态模糊、密集粒子、紫色/高亮荧光或多层渐变；板块通过 1px 结构线、阴影层次与衬度组织信息。
- 视觉语义：珊瑚健康/白化/死亡/藻覆 palette 固定于 taxonomy-v1；不允许不同页面或实验自动变更类颜色。
- Tabular numbers、等宽数值、高对比度、明确单位和图例，图表 tooltip 保留 run_id/dataset 来源。
- 动效只在数字状态变化或短时转场上发生，不可影响视频播放；prefers-reduced-motion 生效。

## 5. 前端实现与性能约束

**组件树提案**：

```text
frontend/src/
  views/wall/{EcologyOverview,TrainingObservatory,EvidenceView}.vue
  components/wall/{WallShell,WallHeader,KPIGrid,QualityFlag,MetricCard}.vue
  components/analysis/{ExperimentTrend,ConfusionMatrix,ModelCompare}.vue
  composables/{useWallMetrics,useWallLayout,useAnalysisRun}.ts
  components/overlays/     # 继承原 Canvas：fish/heat/mask, unchanged coordinate semantics
  theme/ocean-wall.css
```

**路线**：/wall（总览）、/wall/train、/wall/evidence；工作台仍 /（保留当前任务管理交互）。页面使用现有 Vite Router（如果原 App 尚未安装 Router，评估后可先靠局部视图切换，不因此强制大重构）。

**几何规则**：视频 Canvas pointer = (clientPosition - renderedVideoRect) × inverse(scale), 然后转归一化源帧坐标；保持视频 object-fit letterbox，Canvas DPR 与 ResizeObserver 一致；全屏 / 投屏 / 浏览器 zoom / 4K DPR 下必须核对 bounding boxes 与 masks 对齐。**不要把整个工作台简单包 CSS transform:scale 导致 hit-testing/tooltip 错位**。

**性能规则（目标，非现有实测）**：
- 原 mp4 画面优先保证流畅；按需加载大屏路由和 ECharts 系列，缩略视频/高分辨率 mask 不一次载入；
- 图表合批更新，聚合计算在后端，切时间窗访问 raw 网格并缓存，非图表 DOM 变化不触发视频重编码；
- 1920×1080、4K 两类硬件上测试浏览器 CPU/GPU/frame pacing、内存增长/24h kiosk；给出 P95 图层更新延迟与预算，**阈值以目标展厅机型实测冻结，不捏造已有 60FPS**；
- 一次最多一个同源 Artplayer 视频实例，轮播切换时正确销毁图表实例与 subscriptions；离线/断网/无指标时稳定降级显示。

**可访问性**：尽量保证指标文案与图表图例对比度达到 WCAG 4.5:1（正文）；高亮颜色不单独承担数值状态，视频分析必须可暂停与键盘交互。

## 6. 设计验收与视觉评审

- 不同屏幕比：16:9、21:9、16:10 及浏览器缩放 80/100/125%，不得拉伸海洋视频或丢失重点图表；导航/视频控件可用。
- 两个完整真实 run 的大屏联调：fish-only 和 joint；对于无珊瑚、无 track、无 GT/无 ROI，展示 N/A 与缺失原因而不是 0 分。
- 大屏可一键切换演示/真实源；演示数据必须有 DEMO / synthetic 标识，不能用于培训报告或论文。
- 设计上优先科技感但科研可信（数值有单位、出处、样本量）；至少经历科研同学+视觉同学各一次 review。
- 监控图表前端不再派生模型精度，所有评测来自不可变 EvaluationRun，错误来源可追溯。

资料导航：[11-sources.md](11-sources.md)、[12-training-report-and-benchmark.md](12-training-report-and-benchmark.md)。


### 视觉样例入口（引用原项目，不随设计包转发图像素材）
- IofTV-Screen-Vue3 项目效果预览：https://www.gaobug.com/bigscreen-vue3
- DataV-Vue3 官方 Demo：https://datav-vue3-demo.netlify.app/
- DataRoom 原仓库截图目录：https://github.com/gcpaas/DataRoom/tree/master/doc/image
- GoView 大屏样式示例：https://www.mtruning.club/guide/screenTemplate/vueScreenTemplate.html
- Apache ECharts Gallery：https://echarts.apache.org/examples/en/index.html
