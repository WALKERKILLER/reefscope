# 0006：观测报告的 AI 解读只写占位符，同步调用用户配置的服务

## Status
Proposed
Class: feature

## Context and Problem Statement

平台需要把视频分析结果整理成观测点报告，并允许用户在 Web UI 配置一个外部语言模型服务撰写解读。MVP 契约要求 AI 不能写入指标（[02-contracts](../mvp/02-contracts.md)、[12](../mvp/12-training-report-and-benchmark.md)）。需要决定：AI 文本里的数值如何保证来自平台，调用以什么方式执行，以及没有登录鉴权、CORS 放开的本地平台如何保存 API Key。契约见 [观测报告 spec](../specs/draft-observation-reports.md)。

## Decision Drivers

- 报告中的每个数字都能追溯到确定性计算；AI 出错或不可用时报告照常生成。
- 不新增依赖、服务进程或队列；兼容两种主流接口格式。
- 不把 Key 暴露给浏览器、数据库备份或日志；第三方网页无法借 CORS 把 Key 发到别处。
- 外发数据最少：不发送坐标、文件名和画面。

## Considered Options

- 数值占位符：AI 只写 `{{metric_id}}`，服务端替换并审计残留数字；同步调用；Key 存私有文件并绑定 Base URL。
- 自由文本 + 事后核对：AI 直接写数字，服务端抽取数字与事实表比对。
- 工具调用（function calling）让 AI 查询指标。
- 经数据库队列由 Worker 异步调用 AI，报告先生成后补解读。

## Decision Outcome

选择第一项。服务端把指标表（标签、显示值、状态、原因、资料 ID）发给服务，要求输出固定 JSON；数值只能以占位符出现，引用只能用给定资料 ID。服务端把文本拆成片段：已核对的指标、引用、未核对数字、未知指标。界面高亮未核对数字，导出写成“（未核对）”。

调用在请求内同步执行，超时 5–100 s，不跟随重定向，响应上限 1 MB。Docker 的 Gunicorn 仍为单进程，加 4 个线程，使等待 AI 时其他请求不被阻塞；单进程保留旧检测路径依赖的进程内状态。

API Key 只写，保存在 `backend/.secrets/`（0600，被 Git 忽略，Docker 中挂载）。Key 绑定保存时的 Base URL：只改地址不改 Key 会清除 Key；连接测试只用已保存的配置。这样即使第三方页面改写配置，也无法把已有 Key 发往新地址。

## Pros and Cons of the Options

占位符让数值替换可机械验证，也不依赖服务是否支持工具调用；代价是模型偶尔仍写裸数字，只能标记，不能杜绝，因此报告保持待人工审阅。自由文本 + 事后核对需要解析单位、百分数、取整和中文数字，误判多且难以解释给审阅者。工具调用在 OpenAI 兼容服务之间支持不一致，多轮调用增加延迟和失败面，而指标表本身只有几十项，一次给全更简单。异步队列能避免长请求，但要让不可变报告在生成后被修改，或拆成两条记录，并让 Worker 承担网络调用；当前单用户、单次调用数十秒的规模不需要。若出现多用户并发或需要流式输出，应重新评估队列方案。Key 放数据库更简单，但会随数据库文件被复制或备份；放环境变量则无法在 Web UI 配置。

## Links

- [OpenAI Create chat completion](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)：`max_tokens` 已弃用并由 `max_completion_tokens` 取代，且与 o 系列推理模型不兼容；参数支持因模型而异，所以平台两者都不发送。
- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages)：`POST /v1/messages`，必填 `model`、`max_tokens`、`messages`，`system` 为顶层字段。
- [NOAA Coral Reef Watch 5km 方法说明](https://coralreefwatch.noaa.gov/product/5km/methodology.php)：DHW 与 Bleaching Alert Area 分级（2023 年 12 月更新）。
- Schobernd, Bacheler & Conn (2014), [doi:10.1139/cjfas-2013-0086](https://doi.org/10.1139/cjfas-2013-0086)：MeanCount 与 MaxN。
- [观测报告开发说明](../developers/observation-reports.md)、[观测报告 spec](../specs/draft-observation-reports.md)。
