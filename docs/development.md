# Development

默认用简体中文协作。环境与应用运行由 [开发指南](developers/development.md) 负责，测试选择由 [测试政策](developers/testing.md) 负责，根 AGENTS 维护命令入口。

## Daily workflow

1. 从 Issue 认领工作包，读取契约与相关实现；按 VibeWise Learn 让成员先解释设计，具体流程见 [学习协作](agents/learning-workflow.md)。
2. 风险变更先获 spec 批准，长期取舍写 MADR，按已批准范围实现；不把普通任务强行转成多次审批。
3. 在相关边界验证行为，提交前运行 `python3 scripts/check.py`；未安装本地 hook，不宣称提交时会自动校验。
4. 用 repo-review 检查语义、证据与来源后交 PR。提交/推送/合并遵循用户和仓库授权，不以流程文本自动获得权限。

## Source attribution

外部论文、文章、算法、benchmark 或派生代码在最接近实现处保留标题、稳定 URL/DOI 与派生内容；跨模块决定通过链接到所属 ADR 的 Links 保存来源。复制的材料同时保留版权、许可证与 NOTICE，单一链接不能替代许可。

治理工具来自 repo-seed 固定 revision，学习 guides 来自 VibeWise 固定 revision，见 [来源登记](../.repo-seed/upstream.json) 和 [项目来源](developers/provenance.md)。第三方材料升级以实际摘要和差异为准，不以聊天说明为唯一凭据。
