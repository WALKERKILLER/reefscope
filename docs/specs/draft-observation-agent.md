# 观测分析 Agent

Artifact-Version: 1
Status: Draft

## Intent

在观测报告页提供一个真正执行任务的 Agent，而不是一次性问答：它按用户目标列计划，调用平台工具取证和复核，接受平台审计，并在改变数据前请用户批准。目标场景是“分析这次观测并指出值得复核的地方”“检查缺少哪些分析并补跑”“起草报告给我审阅”，以及观测员在监测大屏上边看视频边问“现在画面里鱼多吗”。数值仍全部来自确定性计算。

非目标：不让 Agent 直接写入指标、修改已保存的报告或删除数据；不做多用户权限、流式输出、并行多 Agent、长期记忆或跨观测点检索；不支持 OpenAI Responses API；不评价模型写作质量。

约束：沿用 [观测报告](draft-observation-reports.md) 的模型服务配置、Key 存储和请求边界；只用标准库 HTTP，不新增依赖；外发内容不含坐标、文件名和画面。

## Contract

**执行模型**：`AgentSession`（从观测点或监测大屏上的视频发起；大屏会话可以稍后归档到观测点）→ `AgentRun`（每条用户消息一次）→ `AgentStep`（按序号追加的可见轨迹）。Run 由独立进程 `python manage.py run_agent_worker` 用条件更新领取，租约 180 s，每轮模型调用前续租并检查停止请求。状态：`queued`、`running`、`awaiting_approval`、`applying`、`completed`、`failed`、`cancelled`。租约过期的 Run 记为 `failed`（`worker_lease_expired`）。

**循环**：每轮把系统提示、完整对话记录和工具定义发给模型。

- 无工具调用时：审计回答，未通过则退回改写，最多 2 次，之后带标记接受。
- 读取类工具：立即执行，结果按调用顺序回传。
- 行动类工具（`propose_*`）：生成待批准提议，Run 暂停为 `awaiting_approval`。
- 全部提议决定后 Run 重新排队；Worker 先补齐该轮全部工具结果，再继续。

**预算**：每个 Run 最多 14 轮模型调用、24 次工具调用；每段执行（批准后继续时重新计时）最长 300 s；工具结果超过 8000 字截断。超预算时要求模型不再调用工具并收尾；仍不收尾则 `failed`（`agent_budget_exhausted`）。

**接口格式**：

- `openai_chat`：发送 `tools[{type:"function", function}]`；读取 `message.tool_calls`，结果以 `role:"tool"` 与 `tool_call_id` 回传；助手消息原样重放。
- `anthropic_messages`：发送 `tools[{name, description, input_schema}]`；读取 `tool_use` 块；结果以 user 消息中的 `tool_result` 块回传，相邻 user 内容合并。
- 参数 JSON 无效或工具不存在时，作为 `is_error` 结果回传给模型。

**工具**：

- 读取类：`update_plan`、`get_playback_context`（仅大屏会话）、`get_site_overview`、`list_videos`、`compute_observation_metrics`、`fish_activity_timeline`、`fish_window_summary`、`coral_frame_review`、`model_evidence`、`crw_alert_level`、`search_references`。
- 行动类：`propose_analysis_run`（用最新注册模型和默认参数排队一次分析）、`propose_observation_report`（用一个指标集起草报告）。

**证据台账**：工具返回的每个数值登记为带命名空间的 ID。

| 前缀 | 含义 |
| --- | --- |
| `S{n}` | 指标集 |
| `T{n}` | 时间线 |
| `W{n}` | 时间窗 |
| `C{n}` | 采样帧复核 |
| `E{n}` | CRW 等级 |
| `H{日期}` | 历史报告 |
| `V{视频}` | 视频标签 |
| `SITE` | 观测点 |
| `P{n}` | 大屏当前画面 |

- 模型只看到显示值与标签；视频以“视频 #N”指代。文件名只作为 `user_display` 在界面显示。
- 台账随会话延续：后续消息继承上一次完成 Run 的对话与台账。
- 带时间的指标（时段、时间窗、采样帧时间、当前时刻）另记 `seek_s` 与 `task_id`，供大屏跳转。

**审计**：回答和报告草稿用 `observation.agent.segments` 切分。未知指标 ID、未知资料 ID 和未用占位符的数字算未通过。行首的有序列表编号不算数字。最终回答按 Markdown 子集渲染（不使用 `v-html`，链接只允许 http/https），审计片段保持原样；报告草稿为纯文本。报告草稿只能引用所选指标集内的 ID；保存时去掉集合前缀，再按报告自身的事实重建。

**批准**：`POST /api/v1/agent-runs/{uuid}/decisions`，请求体 `{tool_call_id, decision: approve|reject, note}`。

- 状态从 `awaiting_approval` 条件更新为 `applying` 后执行，避免重复决定和 SQLite 读写事务升级。
- 批准时执行提议：保存不可变报告（`agent.mode = "agent_run"`、`agent_run_id`），或排队分析 Run。
- 拒绝时把备注作为工具结果交给模型。
- 已决定或无此提议时返回 409 `no_pending_proposal`。

**API**：

- `GET/POST /api/v1/sites/{uuid}/agent-sessions`（POST `{text}` 创建会话与首个 Run；服务未启用返回 409 `agent_disabled`）
- `GET/DELETE /api/v1/agent-sessions/{uuid}`（活动中不能删除，409 `session_active`）
- `POST /api/v1/agent-sessions/{uuid}/messages`（409 `run_in_progress`）
- `GET /api/v1/agent-runs/{uuid}?after=N`（只返回序号大于 N 的步骤）
- `POST /api/v1/agent-runs/{uuid}/cancel`
- `GET/POST /api/v1/tasks/{id}/agent-sessions`：大屏会话。POST `{text, context, site_id?}`；`context` 为 `{current_time_s, fish_run_id?, coral_run_id?}`，只保留该视频已完成的 Run，取值无效返回 400 `invalid_context`。追问同样携带 `context`。
- `PATCH /api/v1/agent-sessions/{uuid}` `{site_id}`：大屏会话归档或取消归档；观测点会话返回 409 `site_session_fixed`。

**监测大屏**：每次发送时记录当前视频、Run 与播放时刻。系统提示告知 Agent 这些信息，要求它回答“现在”“这里”之类的问题时先调用 `get_playback_context`，并在提到时刻时使用带时间的指标 ID。`get_playback_context` 登记当前时刻、当前帧可见鱼数、全片平均可见鱼数、最近的珊瑚采样帧时间及其像素占比。未归档的会话可以计算指标（不做历史比较），但不能读取观测点概况或起草报告，工具会提示用户先选择观测点。

**界面**：观测点页分为“Agent 分析”“手动生成”“报告记录”三个标签。

- 主栏：显示目标、步骤轨迹（计划、工具及可展开的参数与返回指标、说明、审计退回、批准卡片、继续、错误）和经审计的回答；运行中每秒增量轮询，可随时停止。
- 侧栏：显示计划清单、按命名空间分组的证据和本轮预算。
- 排队超过 15 s 时提示启动 Worker。
- 监测大屏：顶栏“观测助手”按钮（快捷键 A）或右栏“证据 / 观测助手”切换，把助手停靠在右栏，视频照常播放。面板包含会话选择与归档、可折叠的计划与证据条、自动跟随的轨迹和固定在底部的输入框。回答中带时间的数值显示为 ▶ 按钮，点击即跳到视频该时刻。

## Plan

- 后端：`backend/app/agent/{providers,tools,loop,api}.py`、`management/commands/run_agent_worker.py`、迁移 `0008`。
- 前端：`AgentWorkspace.vue`，并在 `ReportsView.vue` 中分标签。
- 报告：Agent 保存的报告章节名为“Agent 解读”，并说明经用户批准。
- 文档：[开发说明](../developers/observation-agent.md)，取舍见 [0007](../adr/0007-observation-agent-loop.md)。

## Verification

- `python manage.py test app.test_agent`，以本地脚本化模型服务验证：
  - OpenAI 格式的“计划 → 工具 → 审计退回 → 回答”，含工具结果的顺序与内容，以及提示词不含文件名。
  - Anthropic 格式的“提议 → 等待批准 → 批准保存报告 → 继续”，以及消息角色交替。
  - 草稿审计、拒绝备注与跟进消息继承台账。
  - 未知工具与无效参数、预算收尾、停止、服务关闭。
  - 分析提议排队与增量步骤。
  - 大屏会话：上下文记录与校验、当前画面指标与跳转字段、未归档时的报告限制与归档。
- 浏览器，使用脚本化模型服务与真实 Worker：
  - 完成分析会话与报告会话。
  - 批准后打开报告。
  - 监测大屏：打开助手、就当前画面提问、点击时刻跳转、快捷键切换。
  - 1440×900、1280×800、390×844 两种主题下审计无低对比、过小字号与真实重叠。

## Evidence

Pending until approval.
