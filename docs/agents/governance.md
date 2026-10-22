# repo-seed 治理维护

[manifest](../../.repo-seed/manifest.json) 是治理事实源。Core 启用 baseline、spec、MADR decisions 和 postmortems；已有 CI、安全报告与 CODEOWNERS 由 adoption 登记为 external，继续使用既有实现，不生成第二套服务或流程。

## 本仓库采用的路径

架构位于 `docs/developers/architecture.md`，测试政策位于 `docs/developers/testing.md`，决策位于 `docs/adr/`，spec 位于 `docs/specs/`，复盘位于 `docs/postmortems/`。这些路径由上游支持的 governance-path 参数注册，不要求复制上游示例文档，也不导入不属于本项目的示例 ADR。

Core 的三项常驻 skill 位于 `.agents/skills/`。上游 verifier、capability catalog、audit 和 runner 由 scaffold 分发；改进工具版本应重跑上游 skill，而非手改复制的脚本。项目 Review policy、Agent 入口与已实例化文档标记为 user-owned，升级不得覆盖。

## 升级流程

使用 [.repo-seed/upstream.json](../../.repo-seed/upstream.json) 记录的 revision 获取上游到忽略的 `.local/repo-seed/`，阅读它的 `SKILL.md`。若需要升级到其他 revision，先评审版本差异和能力变更，不自动跟随 main。

1. `node scripts/audit-governance.mjs --json` 只读审计；确认建议是否实际适用，已有授权不重复申请。
2. 运行上游 scaffold 的 `--dry-run`，保持 `--hooks skip`，保留既有治理路径与 user-owned 文件。
3. 仅应用获批能力与版本；上游脚本改动按来源对照检查，保留 MIT 许可。
4. 对项目语义内容实例化后用 scaffold `--record-only` 记录，指定所有 user-owned 文件，不手造文件摘要。
5. 执行 `python3 scripts/check.py`，检查 manifest、决策/spec/复盘、链接、placeholder、项目公开边界及实际相关测试。

没有单独授权时不安装 hook、不改全局工具或远端保护。上游默认 MIT 不适用于继承应用；根 LICENSE 与 manifest 的 UNLICENSED 保留项目授权状态，第三方 MIT 只覆盖其分发内容。
