# Agent 工作流

读规则与相关实现，检查 Git 状态，明确验收后再修改。公共契约先评审，再同步 fixture 与调用方。只做任务必需的最小变更。

完成后运行 `python3 scripts/check.py` 与 [相关应用检查](../developers/testing.md)，检查差异与 Git 状态。交接报告实际改动、证据、未覆盖范围与风险；不得编造测试或运行结果。

文档按 [导航](../README.md) 定位 owner，只更新会误导后续读者的事实。学习笔记留在本地，任务状态留在 Issue/PR；仅稳定、可复用且脱敏的经验进入 Agent 知识。
