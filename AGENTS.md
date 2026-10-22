# ReefScope 工作规则

ReefScope 研究水下视频中的鱼类活动与珊瑚健康。默认用简体中文解释，保留准确的技术标识。

- 先读 [文档导航](docs/README.md)、相关实现和契约；首次写入前运行 `git status --short`，保留已有改动。
- 只做任务范围内的最小变更。旧 API 保持兼容；新增科研接口先更新 `docs/mvp/02-contracts.md` 和 fixture，并经负责人评审。
- 必须区分已实现、提案、模拟与实测。科研口径以 MVP 契约为准；禁止用模拟指标冒充训练结果。
- 数据、权重、凭据、主机信息、个人学习记录和受限来源地址不得入库。具体边界见 [披露规则](docs/agents/disclosure-policy.md)。
- 修改后执行 `python3 scripts/check.py` 和相关应用检查；验证范围见 [测试说明](docs/developers/testing.md)。
- 影响权限、数据删除、部署或契约的改动先提交具体 spec；决策写入 `docs/decisions/`，日常工作记录放 Issue/PR。
- 不自动安装 Git hook、插件或全局工具。不在未经授权时提交、推送、部署或更改远端设置。
- 子代理只允许一次性只读探索，不代替主代理写入和验证。

## Repo docs

行为或入口变化时检查 [仓库导读](docs/repo-docs/README.md)，只修改会误导读者的页面。当前导读范围是基础检查流程；应用架构由开发文档与 MVP 文档负责，避免复制真源。

执行流程与知识索引见 [Agent 入口](docs/agents/README.md)。
