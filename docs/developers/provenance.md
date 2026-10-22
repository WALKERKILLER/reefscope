# 来源、授权与复用边界

## 应用与研究材料

本仓库应用来自用户指定的既有项目源码快照 `dd39fcd`。受限来源地址与旧历史不在公开仓库持久化；上游副本只保留在本地忽略目录。导入时排除模型权重、数据库和媒体。原快照未见 LICENSE，因此没有擅自授予整个衍生项目 MIT 或其他开源许可。公开由项目所有者授权，后续再分发和正式开源前仍需确认原作者授权。

MVP 文档与 fixture 来自用户提供的 `sitp-mvp-v2-research-20261021.zip`，日期为 2026-10-21。导入保留技术提案，移除了旧宿主运行观察和受限来源地址。旧审计仅证明历史静态检查，原始 ZIP 未发布。

## 协作规范来源

- repo-seed：通过固定 revision 的上游 scaffold 正式 adoption；Core scripts 和常驻 skills 随仓库分发，项目政策实例化后标记 user-owned。
- VibeWise：内嵌 Learn 及其 guides/Codex 适配，以根 AGENTS/CLAUDE 路由进入，不要求全局插件或 hook。
- [repo-docs-skills](https://github.com/YurunChen/repo-docs-skills)：行为导读、证据索引与最小文档同步。

精确 revision、版本、文件摘要和适配位置由 [.repo-seed/upstream.json](../../.repo-seed/upstream.json) 管理。Learn 仅改 skill 名称与 Codex 的本地路径、调用名与仓库入口恢复说明；行为、onboarding 和状态模板保持上游内容。repo-review 的 Universal core 保持原文，项目风险部分由本项目规则与源码实例化。

[repo-seed MIT](../../.repo-seed/LICENSE.repo-seed.txt) 与 [VibeWise MIT](../../.agents/skills/vibe-wise-learn/LICENSE.txt) 保留各自版权，仅覆盖相应分发材料，不为继承应用授予 MIT。

## 模型、数据与依赖

科研方案的资料来源见 [研究来源](../mvp/11-sources.md)。Ultralytics、CoralscapesV2、SAM、VLM 辅助工具和各预训练权重分别核对代码、权重、数据、再分发与用途条款。不得因代码仓库可访问就推断模型可以分发。

每次真实实验在受控 artifact 存储记录 source、version、sha256、license、用途与审批状态；公开导出仅使用授权且脱敏的证据。当前未提供任何权重或实测精度。
