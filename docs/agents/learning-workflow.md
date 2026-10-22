# VibeWise 开发协作模式

这是团队 Agent 的指导入口，行为规范由仓库内 [Learn skill](../../.agents/skills/vibe-wise-learn/SKILL.md) 及其相邻 guides 负责。默认开发会话读取此 skill；不依赖成员全局安装插件，也不依赖自动 skill 触发。

## 会话进入与恢复

Agent 先读取本仓库规则和相关代码，再按 Learn/codex guide 定位当前 Git 边界内的 `.vibe-wise/` 或旧 `.sensible-vibes/`。不存在画像时按 onboarding 一次问一个问题；有画像时恢复 profile/map，并检索完整 progress 中的待确认决定，不能只看文件开头。

画像显示 paused 或成员明确要求暂停时，尊重暂停。成员要求“这个任务直接实施”可跳过该任务学习对话；不能据此永久伪造已掌握知识。新会话不读取其他仓库或其他成员的学习状态，不跟随学习目录/文件的符号链接。

## 成员如何使用

- 在 Codex 中使用 `$vibe-wise-learn`；其他工具可直接要求 Agent 读取仓库 Learn skill。
- 普通开发请求会保留“成员先推理、Agent 再反馈”的流程。需要帮助时可请求概念解释、方案示例或选项。
- Design checkpoint 确认只记录设计；Implementation checkpoint 确认具体修改范围并授权实施。已经授权的范围不重复申请批准。
- 实施后说明改动如何对应成员设计、关键机制、测试新增与实际运行结果；不把点击确认当作理解证据。
- Build/Design/Implementation 并非强制停三次；已能实施的具体设计可一次确认。只因时间或工具调用次数增加检查点没有意义。

## 团队交接与隐私

个人 profile/progress/map 保存在忽略目录。团队共享成果进入 Issue/PR、批准的 spec、MADR 或正式文档；只记录实际同意的结论，不复制原始学习记录、身份和聊天。

本仓库内嵌 Learn 及其 Codex 适配，未安装 Claude SessionStart hook 或全局插件。Codex 的恢复依靠每次会话的 AGENTS 路由，不宣称存在系统级会话 hook；完整上游插件与 reset 命令不是本地 Learn 包提供的功能。

## 来源与维护

版本、revision、文件摘要和必要适配在 [.repo-seed/upstream.json](../../.repo-seed/upstream.json)，保留 [原 MIT 许可](../../.agents/skills/vibe-wise-learn/LICENSE.txt)。升级需核对上游变更与根路由，不能只改一个版本号；验证检查 Learn 的引用、文件摘要、忽略规则和暂停/恢复契约文本。

引入指导流程不替当前成员创建画像，也不追认任何未确认设计。实际引导质量仍需开发会话人工检验，静态校验只能证明接线与分发内容。
