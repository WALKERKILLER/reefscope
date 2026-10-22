# ReefScope Agent 协作规则

ReefScope 研究水下视频中的鱼类活动与珊瑚健康。默认使用简体中文，保留准确的技术标识。

## 治理与入口

治理由 repo-seed 管理。[manifest](.repo-seed/manifest.json) 是治理路径、能力状态和文件所有权的唯一来源；产品源码仍由项目维护。

先读 [文档导航](docs/README.md)、相关实现与契约，首次写入前执行 `git status --short`。保留已有改动，不覆盖无关文件。

常驻技能路由（自动发现不可用时直接读取对应 SKILL.md）：

- 开发、方案讨论与交接默认载入 [VibeWise Learn](.agents/skills/vibe-wise-learn/SKILL.md)，按 [协作模式](docs/agents/learning-workflow.md) 引导成员并恢复待确认决定。
- 变更/PR 审查使用 [repo-review](.agents/skills/repo-review/SKILL.md)。
- 有真实替代方案的长期决定使用 [repo-decisions](.agents/skills/repo-decisions/SKILL.md)。
- 治理能力变化使用 [repo-governance](.agents/skills/repo-governance/SKILL.md)。
- 初始化、adoption、治理升级使用固定版本的上游 repo-seed skill，流程见 [治理维护](docs/agents/governance.md)；不要手抄脚本模拟升级。

## 学习指导与授权

让成员先解释方案，再检查取舍；必要时说明概念，不虚构成员理解。Build、Design、Implementation checkpoint 的区别以 VibeWise guides 为准。

成员可明确要求“本任务直接实施”或“暂停学习”；尊重当前范围的既有授权，不重复询问相同批准。设计确认不自动等于实施授权，未解决的新重大决定仍需讨论。学习模式、进度和个人项目图只留在被忽略的本地目录，不进入团队文档。

## 命令与验证

- Test: `python3 scripts/check.py`（治理门禁、项目边界、科研 fixture 和标准库测试）。
- Gates: `node scripts/run-gates.mjs`（由 manifest 选择上游校验器）。
- Whitespace: `git diff --check`。
- 后端/前端与真实 UI 验收按 [测试政策](docs/developers/testing.md) 选择，不用 build 代替交互或科研验证。

每次提交前运行总检查；Git hook 仅在单独明确授权后安装。

## 项目硬约束

1. 只做任务范围内的最小变更，保留旧 API 兼容；共享契约先评审，同步所属文档、fixture 与调用方。
2. 区分实现、提案、模拟与实测。科研口径以 MVP 契约为准，不用伪标签、训练曲线或演示数据冒充真实精度。
3. 风险边界改动从 Approved [spec](docs/specs/README.md) 开始；有意义的替代取舍记入 [MADR](docs/adr/README.md)，不是每次提交写一篇 ADR。
4. 系统性、隐蔽且有复发成本的逃逸故障写 [postmortem](docs/postmortems/README.md)，关联永久防护。
5. 外部派生代码/算法保留最接近实现的来源与许可证，规则见 [开发流程](docs/development.md#source-attribution)。
6. 数据、权重、凭据、个人身份、主机信息和受限来源不入库，见 [披露规则](docs/agents/disclosure-policy.md)。不读取 .env 或其他秘密。
7. 不擅自安装 hook、全局插件、提交、推送、改远端权限或部署。用户明确授权范围内的工作可继续；新权限/破坏性边界需单独确认。
8. 子代理只做一次性只读探索，写入与验证由主代理负责。

## 文档与维护

遵循 [docs/AGENTS.md](docs/AGENTS.md) 的单一事实源与文档分层。项目地图见 [架构](docs/developers/architecture.md)，长期 Agent 知识见 [索引](docs/agents/README.md)。

行为变化时检查 [仓库导读](docs/repo-docs/README.md)，只修改会误导读者的页面；Issue 管任务状态，个人学习笔记与聊天不是项目事实源。治理升级只能通过 repo-seed 重新运行并保留 user-owned 内容，不建立第二份治理清单。
