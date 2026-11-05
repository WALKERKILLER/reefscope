# 0007：观测 Agent 在独立 Worker 中运行工具循环，写操作经人工批准

## Status
Proposed
Class: feature

## Context and Problem Statement

[0006](0006-observation-report-agent.md) 让模型为报告一次性撰写解读，本质仍是“提问 → 产出文本”。用户需要的是在平台中执行分析任务的 Agent：它要能自己决定查什么，深入某个时段或采样帧，发现缺少分析时补跑，起草报告后交给人审阅，并且让每一步可见、可停止、可追溯。

同类数智化平台的做法：

- Snowflake Cortex Agents：规划、调用工具、反思，设有预算与运行轨迹。
- Databricks Genie Agent 模式：先列研究计划，多次查询迭代，报告附引用。
- Palantir AIP：Agent 只生成提议，由人审批，并保留决策日志。
- Microsoft Fabric 数据 Agent：展示中间步骤与生成的查询，只读。

需要决定：循环在哪里执行，Agent 能改变什么，数值可信如何延续 0006 的保证，以及怎样在 SQLite 与单进程 Web 下运行。契约见 [观测分析 Agent spec](../specs/draft-observation-agent.md)。

## Decision Drivers

- 体现 Agent 能力：计划、工具选择、迭代、反思、面向用户的中间状态。
- 每个数字仍可追溯到确定性计算；Agent 不能写入指标或改写已有报告。
- 改变平台数据的动作必须由人批准，且能附带修改意见。
- 长任务不占用 Web 请求；可停止、可恢复、有明确预算。
- 不新增依赖或服务；兼容 OpenAI 兼容与 Anthropic 两种格式。

## Considered Options

- 独立 Worker 运行的工具循环 + 行动提议待批准 + 确定性审计器（本方案）。
- 在 Web 请求内同步执行整个循环。
- 固定工作流（提示链）：平台按固定顺序取数后让模型写一次。
- 用第二次模型调用做评审（LLM-as-judge）。
- 允许 Agent 直接保存报告和排队分析。
- 使用服务商托管的 Agent 或 OpenAI Responses API。

## Decision Outcome

选择第一项。Run 写入数据库队列，由 `run_agent_worker` 按与分析 Worker（[0003](0003-database-fish-worker.md)）相同的条件更新和租约方式领取。每轮结果持久化为对话记录与步骤，所以暂停批准、Worker 重启和跟进提问都从数据库继续。

工具分两类：

- 读取类：立即执行。
- 行动类：只生成提议，Run 暂停为 `awaiting_approval`。批准后由平台执行，再把结果作为工具结果交给模型；拒绝时交回用户备注。

工具结果中的每个数值登记到带命名空间的证据台账。回答和报告草稿只能写台账 ID 的占位符，由 0006 的片段审计逐一核对；未通过时把具体问题退回模型改写，最多 2 次。审计规则是确定性的，所以这一步按评估者-优化者模式用规则代替第二个模型。

批准请求不用数据库事务，而是先把状态条件更新为 `applying`：SQLite 中先读后写的事务在 Worker 并发写入时会无法升级而报“database is locked”，实际预览中已复现。

## Pros and Cons of the Options

**本方案。**

- 优点：
  - 循环、批准和审计各自可测；轨迹就是数据库记录，界面增量轮询即可展示。
  - 预算与停止在每轮检查。
- 代价：
  - 需要多运行一个 Worker 进程，未运行时任务一直排队，界面会提示。
  - 工具调用依赖服务支持函数调用；不支持的服务会直接给文字回答，审计照常执行，但体现不出 Agent 行为。
  - 报告草稿只能引用一个指标集。时间线和采样帧复核的数值留在会话中，不进入不可变报告，因为报告按自身事实重建。

**其他方案。**

- Web 请求内同步循环：最简单，但多轮调用可达数分钟，超出请求超时，停止与批准都需要另建状态，单进程 Gunicorn 的线程也会被长期占用。
- 固定工作流：可预测，但不能根据中间结果决定下一步，正是用户指出的“和 chat 一样”的问题。
- LLM-as-judge：能评语气和完整性，但对“数字是否来自平台”这一首要标准不如规则可靠，且多一次外发与费用。
- 直接写入：交互更快，但违背 AI 只读指标的 MVP 契约，误操作难以撤回。Palantir AIP 与 LangGraph 的人工中断模式都把写操作放在审批之后。
- 托管 Agent 或 Responses API：可得到服务端工具编排，但锁定单一服务商，且数据与工具执行要离开平台。OpenAI 新模型在 Chat Completions 中的工具支持可能受限，这是已知限制；若成为主要用法，再评估增加 Responses 格式。

## Links

- [Snowflake Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents) 与[构建最佳实践](https://www.snowflake.com/en/developers/guides/best-practices-to-building-cortex-agents/)：规划、工具、反思、监控与预算。
- [Databricks Genie Agent 模式](https://docs.databricks.com/aws/en/genie-agents/concepts)、[深度分析发布说明](https://www.databricks.com/blog/expanding-genie-agents-deep-analysis-file-reasoning-and-more)：研究计划、多次查询与引用。
- [Palantir AIP Logic 自动化](https://www.palantir.com/docs/foundry/logic/aip-logic-integration-automate)、[平台概览](https://www.palantir.com/docs/foundry/platform-overview/overview)：提议待审、决策日志。
- [Microsoft Fabric 数据 Agent](https://learn.microsoft.com/en-us/fabric/data-science/how-to-create-data-agent)：展示中间步骤与生成的查询。
- [Anthropic：Building effective agents](https://www.anthropic.com/research/building-effective-agents)（工作流与 Agent、评估者-优化者）、[Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)（少而完整的工具、命名空间、精简上下文）。
- [LangChain 人工介入](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)：批准、编辑、拒绝与恢复。
- [Anthropic 工具调用](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)、[OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)、[OpenAI 函数调用指南](https://developers.openai.com/api/docs/guides/function-calling)。
- [ReefCloud（AIMS）](https://www.aims.gov.au/research/technology/reefcloud)：珊瑚礁影像自动分析与标准化报告。
- [观测分析 Agent 开发说明](../developers/observation-agent.md)。
