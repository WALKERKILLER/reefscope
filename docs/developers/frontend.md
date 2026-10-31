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

两套主题中 `--ink-3` 对 `--surface` 的 WCAG 对比度不低于 5.5:1，状态色不低于 4.5:1。数值颜色不能单独表达状态，必须同时有文字或图标。

字号按角色使用：说明 11px、次要 12px、正文 13px、标题 14px、页面标题 18px、指标 22px、大屏指标 30px。所有变化的数值使用 `.tnum` 等宽数字；中文不加字距、不转大写。

## 基础组件

`components/ui/` 封装 Reka UI：`UiSelect`、`UiSwitch`、`UiSlider`、`UiSegmented`、`UiTabs`、`UiMenu`、`UiTooltip`、`UiToaster` 和 `UiDialogHost`。按钮与输入框使用 `.btn`、`.btn-primary`、`.btn-ghost`、`.input` 等全局类。确认和重命名通过 `lib/dialogs.js` 的 `confirmDialog` / `promptDialog`，不使用浏览器原生对话框；通知通过 `lib/toast.js`。使用 `UiTooltip` 的视图需由根组件提供 `TooltipProvider`。

`UiSelect` 允许空字符串选项（如“全部类别”），内部转换为 Reka 可接受的占位值。分段控件始终保留一个选中值。

旧模板中的 `m3-*` 工具类映射到新令牌，仅为过渡；新代码不得使用，相关视图迁移后删除映射。

## 图标与动效

图标来自 `@tabler/icons-vue`，按名称导入。全局样式把 `.tabler-icon` 设为 16px、描边 1.5；与半粗文字并排时设 `--icon-stroke: 2`。默认使用线性图标，选中态可用对应 Filled 变体。

交互状态只过渡颜色、阴影与缩放，时长不超过 200ms；按下缩放 0.96。弹层进入使用 140ms 透明度与缩放。不使用常驻呼吸灯、发光或装饰性渐变。`prefers-reduced-motion` 时关闭动画。

## 文案

界面使用简体中文，按钮以动词开头并说明具体动作，如“开始分析”“删除视频”。破坏性确认重复后果。错误说明原因和下一步，不使用“哎呀”或感叹号。空状态说明这里是什么、如何开始。缺失指标显示 N/A 并说明缺少的输入，不写成 0。

## 字体与许可

Inter Variable 通过 `@fontsource-variable/inter` 自托管，SIL OFL 1.1；按 unicode-range 分包，页面不请求远程字体。中文依次使用 HarmonyOS Sans SC、PingFang SC、Noto Sans CJK SC 与微软雅黑。Reka UI 与 Tabler Icons 为 MIT 许可，随构建分发。
