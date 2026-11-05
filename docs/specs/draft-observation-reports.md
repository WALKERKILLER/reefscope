# 观测点报告与可选 AI 解读

Artifact-Version: 1
Status: Draft

## Intent

把视频分析结果按观测点归档，生成可追溯的观测报告，形成“视频 → 分析 Run → 报告 → 下次观测比较”的闭环。报告数值全部由平台确定性计算；用户可在 Web UI 配置一个兼容 OpenAI Chat Completions 或 Anthropic Messages 的服务，为报告附加文字解读。

非目标：不新增科学指标的计算方法（沿用鱼类与珊瑚 Run 的产物）；不做底栖覆盖率、群体白化发生率、物种丰富度或生物量；不自动获取卫星环境数据；不做多用户权限、流式输出或异步队列；AI 文本不写入任何指标。

约束：后端只用标准库 HTTP；不新增依赖。API Key 不进入数据库、日志、响应或报告。

## Contract

**观测点**：`/api/v1/sites` 列表与创建，`/api/v1/sites/{uuid}` 查看、修改、删除。名称唯一（1–80 字）；纬度 −90–90、经度 −180–180、水深 0–200 m 可空。已有报告的观测点删除返回 409 `site_has_reports`。坐标只在平台内显示，不发送给 AI 服务。

**报告请求**：`POST /api/v1/observation-reports/preview` 与 `POST /api/v1/observation-reports` 接受 `site_id`、`observed_on`（ISO 日期）、`run_ids`（1–8 个已完成 Run，每段视频每种 kind 最多一个）、可选 `environment`、`use_agent`（仅创建）。预览只返回事实，不保存、不外发。错误：400 参数无效，404 观测点或 Run 不存在，409 Run 未完成、产物不可读或 AI 服务未启用。`GET /api/v1/observation-reports/candidates` 按视频列出已完成 Run。

**事实与指标**（`observation-facts/v1`）：每个指标含 `label`、`value`、`unit`、`status`、`reason`、`reason_text`、`display`、可选 `numerator`/`denominator`/`source`。

- 鱼类：MeanCount = 追踪框总数 ÷ 处理帧数（每帧处理，无鱼帧计 0）；画面峰值与其时间；有鱼帧比例；追踪 ID 数；track-seconds；轨迹时长中位数；≥ 5 s 轨迹数；平均置信度。AP50、IDF1/HOTA 为 N/A。
- 珊瑚：沿用 `coral_query.summarize`；另给单帧珊瑚占比范围与出现白化像素的帧数。覆盖率、群体白化发生率、分割精度、死亡/藻覆比例为 N/A 并给出原因。
- 观测点合并值（`site.*`）由各视频的原始分子分母合并，不对视频平均。
- 环境：SST、原位水温、HotSpot、DHW、来源与产品日期由用户录入并做范围校验。CRW 白化警报等级按 NOAA CRW v3.1：HotSpot ≤ 0 无胁迫，0 < HotSpot < 1 观察，HotSpot ≥ 1 时按 DHW 0–4–8–12–16–20 分为预警与 1–5 级；HotSpot ≥ 1 而 DHW 缺失或为 0 时不给等级。
- 比较：同一观测点更早日期的最新报告。模型、分析参数一致且两次都为固定机位时给出变化量；否则只并列数值并列出原因。

**报告**（`reefscope-observation-report/v1`）：不可变记录，章节为观测概况、鱼类活动、珊瑚画面、环境背景、与上次观测比较（如有）、AI 解读、缺失指标与局限、参考资料。所有报告 `human_review_status` 为 `pending`。导出 `/export?export=markdown|html`，HTML 转义且带严格 CSP。

**AI 服务配置**：`GET/PUT /api/v1/report-agent/config`、`POST /api/v1/report-agent/test`。

- 格式 `openai_chat`（`{base}/chat/completions`，`Authorization: Bearer`，不发送 `max_tokens`、`max_completion_tokens` 与 `temperature`）或 `anthropic_messages`（`{base}/v1/messages`，`x-api-key`、`anthropic-version: 2023-06-01`、`max_tokens`）。
- Base URL 只接受 http/https，不含账号、查询或片段；超时 5–100 s；不跟随重定向；响应上限 1 MB。
- API Key 只写：保存到 0600 私有文件，响应只给 `key_configured` 与末四位；修改 Base URL 而未提供新 Key 时清除旧 Key。启用需要地址、模型与 Key。测试只使用已保存的配置。

**AI 输入与输出**：发送站点名称、观测日期、视频序号、镜头运动、指标的标签/显示值/状态/原因、可比性、模型是否有独立评估、局限和资料卡；不发送坐标、文件名、Run ID、画面。输出 JSON（summary、observations、interpretation、limitations、next_steps）。数值只能写 `{{metric_id}}`，由服务端替换；引用只能用资料卡 ID。服务端把文本存为片段并记录审计：未核对数字、未知指标、未知引用。AI 失败时仍保存确定性报告，记录错误码。报告保存提示词版本、请求摘要、格式、模型、主机名、耗时与 token 用量。

## Plan

`backend/app/observation/`：`facts.py`、`agent.py`、`report.py`、`sources.py`、`api.py`；迁移 `0007`。前端 `ReportsView.vue`、`ObservationReportViewer.vue`、`ReportSegments.vue`、`AgentSettingsDialog.vue`，主导航新增“观测报告”。Docker 的 Gunicorn 加线程，`backend/.secrets/` 挂载并被忽略。

## Verification

- `python manage.py test app.test_observation`：教学例 MeanCount、零鱼帧、50% 白化显示、像素合并、CRW 全部边界、比较可比性、Key 只写与 0600、URL/Key 注入拒绝、两种格式的请求路径与头、提示词不含坐标与文件名、片段审计、失败仍保存、重定向拒绝、不可变与观测点删除保护。
- 浏览器：配置服务、测试连接、新建观测点、预览、生成含 AI 解读的报告、查看片段与引用、返回记录；1440×900、1280×720、390×844 两种主题下审计无低对比、过小字号与真实重叠。

## Evidence

Pending until approval.
