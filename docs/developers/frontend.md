# 前端设计系统

本文是参考说明，描述 `frontend/src/` 的视觉令牌、基础组件、图标与文案规则。选型理由见 [0004](../adr/0004-frontend-design-system.md)，大屏布局目标见 [大屏规范](../mvp/14-visual-wall-research-and-spec.md)。

## 令牌

`style.css` 是颜色、字号、圆角和阴影的唯一来源，颜色使用 OKLCH。深色主题源自大屏规范的深海墨蓝与海沫青，浅色主题为纸面白。主题保存在浏览器本地，由 `lib/theme.js` 切换根元素的 `dark` 类。

| 角色 | 令牌 | 用途 |
| --- | --- | --- |
| 底面 | `--canvas` `--surface` `--surface-2` `--surface-3` | 页面、面板、输入与悬停层级 |
| 线 | `--line` `--line-strong` | 结构分隔与控件描边 |
| 文字 | `--ink` `--ink-2` `--ink-3` | 正文、次要信息、说明与标签 |
| 强调 | `--accent` `--accent-ink` `--accent-soft` | 主操作、选中态与焦点，每个视图只填充一个主操作 |
| 状态 | `--info` `--ok` `--warn` `--danger` 及 `-soft` | 运行中、完成、提示与失败；不承担装饰 |
| 图表序列 | `--series-1` `--series-2` | 同一面板内的两条序列，如训练与验证；不表示状态 |

两套主题中 `--ink-3` 对 `--surface` 的 WCAG 对比度不低于 5.5:1，状态色在面板与对应 `-soft` 底色上不低于 4.5:1。两种序列色对面板不低于 3:1，三类色觉模拟下的 OKLab 色差不低于 19。数值颜色不能单独表达状态，必须同时有文字或图标。

字号按角色使用：说明 11px、次要 12px、正文 13px、阅读 14px、标题 14px、页面标题 18px、指标 22px、大屏指标 30px。界面文字不小于 11px。报告等长段落使用 `.prose`（阅读字号、行高 1.65、宽度不超过 68ch，中文约 40 字一行）。所有变化的数值使用 `.tnum` 等宽数字；中文不加字距、不转大写。

## 页头与导航

顶栏分三区：品牌靠左，导航位于整页中线，操作靠右；两侧列等宽，导航在任何宽度都真正居中。导航是胶囊分段样式，选中项用随宽度测量的底块标出，首屏不播放滑动；480px 以下只显示图标，名称保留为无障碍名称。居中顶栏适合少量顶级视图；顶级视图超过五个时应改用侧栏，参见 Ant Design Pro 的 top 布局与 Vercel 2026 年改用侧栏的说明。

工作台三列（视频库、播放器、分析面板）使用同一 44px 的 `.panel-head`，标题基线与顶边对齐；需要分隔线时加 `.ruled`。分析面板的页头就是“鱼类 | 珊瑚”切换与刷新按钮，不再重复面板标题和文件名。记录与报告等阅读页面使用 `.page`、`.page-inner`（最宽 1120px 居中）与 `.page-head`，内容块使用 `.ui-card` / `.ui-card-head`。

## 共享样式

横幅、指标块、运行状态、进度条、文字链接、列表与 N/A 列表各只有一份定义：`.ui-banner`（`-warn` / `-danger` / `-info`）、`.ui-kpis` 与 `.ui-kpi`（列数用 `--kpi-cols`，缺值加 `.missing`）、`.ui-run-state`、`.ui-progress`、`.ui-link`、`.ui-bullets`、`.ui-na-list`，以及 `.truncate`、`.empty-title`。报告阅读视图共用 `.ui-report`（章节目录与正文两栏）、`.ui-toc`、`.ui-chapters`、`.ui-chapter`、`.ui-rows`（键值行）和 `.ui-table`，模型质量报告与观测报告都使用它们。组件只写布局差异和修饰，不复制这些规则。

观测报告的 AI 解读按片段渲染（`ReportSegments.vue`）：平台填入的数值加虚线下划线，悬停显示指标名；模型自行写出的数字用警示色标记；引用链接到参考资料。

## 基础组件

`components/ui/` 封装 Reka UI：`UiSelect`、`UiSwitch`、`UiSlider`、`UiSegmented`、`UiTabs`、`UiMenu`、`UiTooltip`、`UiToaster` 和 `UiDialogHost`。按钮与输入框使用 `.btn`、`.btn-primary`、`.btn-ghost`、`.input` 等全局类。确认和重命名通过 `lib/dialogs.js` 的 `confirmDialog` / `promptDialog`，不使用浏览器原生对话框；通知通过 `lib/toast.js`。使用 `UiTooltip` 的视图需由根组件提供 `TooltipProvider`。

`UiSelect` 允许空字符串选项（如“全部类别”），内部转换为 Reka 可接受的占位值。分段控件始终保留一个选中值。

## 图标与动效

图标来自 `@tabler/icons-vue`，按名称导入。全局样式把 `.tabler-icon` 设为 16px、描边 1.5；与半粗文字并排时设 `--icon-stroke: 2`。默认使用线性图标，选中态可用对应 Filled 变体。

交互状态只过渡颜色、阴影与缩放，时长不超过 200ms；按下缩放 0.96。弹层进入使用 140ms 透明度与缩放。不使用常驻呼吸灯、发光或装饰性渐变。`prefers-reduced-motion` 时关闭动画。

## 图表

ECharts 在 `frontend/src/charts/echarts.js` 按需注册，组件通过 `useChart` 懒加载，容器有尺寸后才初始化，并随主题切换重绘。ECharts 不解析 OKLCH，图表颜色由 `chartTokens()` 从同一组令牌换算为 RGB。

轨迹 ID 颜色由 `frontend/src/lib/palette.js` 按 ID 固定映射：视频叠加用高明度色，浅色图表用中明度色。筛选不重排颜色，标签始终带 `#ID`。热图等连续量使用 inferno 单向色阶，并标注单位与峰值。珊瑚掩膜类别色由 `CORAL_CLASSES` 固定：未白化青绿、白化品红，视频上半透明填充；图表与条形图按主题取描边值，两色明度拉开以区分色觉差异，白化线另用虚线，图例始终带类别文字。多个量纲不同的指标拆成共享横轴的小多图，第二条序列同时用虚线区分。图表不使用双 y 轴；无真值的指标显示 N/A 与原因，不画占位曲线。

## 文案

界面使用简体中文，按钮以动词开头并说明具体动作，如“开始分析”“删除视频”。破坏性确认重复后果。错误说明原因和下一步，不使用“哎呀”或感叹号。空状态说明这里是什么、如何开始。缺失指标显示 N/A 并说明缺少的输入，不写成 0。

## 字体与许可

Inter Variable 通过 `@fontsource-variable/inter` 自托管，SIL OFL 1.1；按 unicode-range 分包，页面不请求远程字体。中文依次使用 HarmonyOS Sans SC、PingFang SC、Noto Sans CJK SC 与微软雅黑。Reka UI 与 Tabler Icons 为 MIT 许可，随构建分发。
