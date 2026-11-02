# 0004：前端设计系统采用 Reka UI 与 Tabler Icons

## Status
Proposed
Class: architecture

## Context and Problem Statement

工作台、监测大屏和报告页需要一致的选择器、开关、标签页、菜单、对话框与通知，并满足键盘、焦点和读屏要求。原界面混用 Material 风格令牌、手写下拉菜单、浏览器原生 `confirm`/`prompt` 和多来源内联 SVG，同类控件的外观与行为不一致。科研展示还需要克制、高信息密度的视觉语言，见 [大屏规范](../mvp/14-visual-wall-research-and-spec.md)。

## Decision Drivers

- 可访问的交互行为（焦点管理、键盘导航、ARIA）由维护活跃的库负责，项目只维护视觉。
- 视觉完全由项目令牌决定，不继承通用后台模板外观。
- 按需引入，保持首屏体积；与 Vue 3.4+、Vite、Tailwind v4 共存。
- 许可证宽松，可随前端构建分发。

## Considered Options

- Reka UI（无样式组件）+ Tabler Icons + 项目令牌。
- Naive UI 或 Element Plus 等带样式组件库。
- PrimeVue unstyled 模式。
- 继续手写全部控件与内联 SVG。

## Decision Outcome

选择 Reka UI 2.11.0 提供交互原语，Tabler Icons 3.50.0 提供图标，Inter Variable 5.3.0 自托管拉丁字形，中文使用系统黑体。`frontend/src/style.css` 是唯一令牌来源，`frontend/src/components/ui/` 封装基础组件；功能组件不直接写颜色值、不再新增内联 SVG 图标。使用规则见 [前端设计系统](../developers/frontend.md)。图表继续使用 ECharts，按需注册模块。

## Pros and Cons of the Options

Reka UI 只提供行为，外观由令牌控制，代价是每个基础组件需要自写样式，并由项目维护 `components/ui/` 封装。带样式组件库开箱即用，但主题覆盖面大，默认外观接近通用管理后台，与科研大屏的克制风格冲突，且体积更大。PrimeVue unstyled 同样可行，但组件面与 pass-through 配置复杂度高于本项目所需。继续手写可以避免依赖，但菜单焦点、Escape 关闭、滚动锁定与读屏语义需要逐个实现和测试，已有实现存在点击外部与键盘支持缺口。Tabler 提供统一 24px 网格、可调描边和部分实心变体，覆盖面大于手写图标；Lucide 同样合适，选择 Tabler 是为了沿用其实心变体表达选中态。

## Links

- [Reka UI 文档](https://reka-ui.com/docs/overview/introduction)，MIT 许可。
- [Tabler Icons](https://tabler.io/icons)，MIT 许可。
- [Fontsource Inter](https://fontsource.org/fonts/inter)，SIL Open Font License 1.1。
- [Apache ECharts 按需引入](https://echarts.apache.org/handbook/en/basics/import/)。
- [前端设计系统](../developers/frontend.md)。
