# 来源、授权与复用边界

## 应用与研究材料

本仓库应用来自用户指定的既有项目源码快照 `dd39fcd`。受限来源地址与旧历史不在公开仓库持久化；上游副本只保留在本地忽略目录。导入时排除模型权重、数据库和媒体。原快照未见 LICENSE，因此没有擅自授予整个衍生项目 MIT 或其他开源许可。公开由项目所有者授权，后续再分发和正式开源前仍需确认原作者授权。

MVP 文档与 fixture 来自用户提供的 `sitp-mvp-v2-research-20261021.zip`，日期为 2026-10-21。导入保留技术提案，移除了旧宿主运行观察和受限来源地址。旧审计仅证明历史静态检查，原始 ZIP 未发布。

## 协作规范来源

- [repo-seed](https://github.com/EricSanchezok/repo-seed)：采用单一规则入口、风险触发 spec、MADR 决策和可执行门禁。项目采用适配实现，不安装 hook，不宣称由其生成器管理。
- [repo-docs-skills](https://github.com/YurunChen/repo-docs-skills)：采用行为导读、证据索引和最小文档同步；不把计划当实现。
- [VibeWise](https://github.com/nykooi1/vibe-wise)：采用成员先解释方案、审查取舍和实施后复述，不强制安装学习插件。

规范参考检索于 2026-10-22。上述内容是项目化改写，未拷贝上游脚本或模板。

## 模型、数据与依赖

科研方案的资料来源见 [研究来源](../mvp/11-sources.md)。Ultralytics、CoralscapesV2、SAM、VLM 辅助工具和各预训练权重分别核对代码、权重、数据、再分发与用途条款。不得因代码仓库可访问就推断模型可以分发。

每次真实实验在受控 artifact 存储记录 source、version、sha256、license、用途与审批状态；公开导出仅使用授权且脱敏的证据。当前未提供任何权重或实测精度。
