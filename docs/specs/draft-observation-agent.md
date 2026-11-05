# 观测分析 Agent

Artifact-Version: 1
Status: Draft

## Intent

在观测报告页提供一个真正执行任务的 Agent，而不是一次性问答：它按用户目标列计划，调用平台工具取证和复核，接受平台审计，并在改变数据前请用户批准。目标场景是“分析这次观测并指出值得复核的地方”“检查缺少哪些分析并补跑”“起草报告给我审阅”。数值仍全部来自确定性计算。

非目标：不让 Agent 直接写入指标、修改已保存的报告或删除数据；不做多用户权限、流式输出、并行多 Agent、长期记忆或跨观测点检索；不支持 OpenAI Responses API；不评价模型写作质量。

约束：沿用 [观测报告](draft-observation-reports.md) 的模型服务配置、Key 存储和请求边界；只用标准库 HTTP，不新增依赖；外发内容不含坐标、文件名和画面。

## Contract

**执行模型**：`AgentSession`（每个观测点多条会话）→ `AgentRun`（每条用户消息一次）→ `AgentStep`（按序号追加的可见轨迹）。Run 由独立进程 `python manage.py run_agent_worker` 用条件更新领取，租约 180 s，每轮模型调用前续租并检查停止请求。状态：`queued`、`running`、`awaiting_approval`、`applying`、`completed`、`failed`、`cancelled`。租约过期的 Run 记为 `failed`（`worker_lease_expired`）。

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

- 读取类：`update_plan`、`get_site_overview`、`list_videos`、`compute_observation_metrics`、`fish_activity_timeline`、`fish_window_summary`、`coral_frame_review`、`model_evidence`、`crw_alert_level`、`search_references`。
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

- 模型只看到显示值与标签；视频以“视频 #N”指代。文件名只作为 `user_display` 在界面显示。
- 台账随会话延续：后续消息继承上一次完成 Run 的对话与台账。

**审计**：回答和报告草稿用 `observation.agent.segments` 切分。未知指标 ID、未知资料 ID 和未用占位符的数字算未通过。报告草稿只能引用所选指标集内的 ID；保存时去掉集合前缀，再按报告自身的事实重建。

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

**界面**：观测点页分为“Agent 分析”“手动生成”“报告记录”三个标签。

- 主栏：显示目标、步骤轨迹（计划、工具及可展开的参数与返回指标、说明、审计退回、批准卡片、继续、错误）和经审计的回答；运行中每秒增量轮询，可随时停止。
- 侧栏：显示计划清单、按命名空间分组的证据和本轮预算。
- 排队超过 15 s 时提示启动 Worker。

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
- 浏览器，使用脚本化模型服务与真实 Worker：
  - 完成分析会话与报告会话。
  - 批准后打开报告。
  - 1440×900、1280×800、390×844 两种主题下审计无低对比、过小字号与真实重叠。

## Evidence

Pending until approval.
