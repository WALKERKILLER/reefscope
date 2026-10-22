---
name: repo-review
description: Use when reviewing a pull request or a change in this repository — orients the reviewer to this repository's standards (AGENTS.md conventions, decision log, gates) and the review-specific checks that code alone cannot show
---

# Reviewing a change in this repository

Read the diff, the owning docs, the decision log, and enough surrounding code to understand the design before judging it. **Blocking requirements** are hard: a violation blocks the change. **Manual checks** rank remaining risk by this project's real failure modes — apply the ones the change touches, not every one, to every change.

## Sources of truth

- [AGENTS.md](../../../AGENTS.md): standing repository rules.
- [docs/AGENTS.md](../../../docs/AGENTS.md): documentation placement and prose discipline.
- [docs/adr/](../../../docs/adr/): durable design rationale. Disagreement with a decision record is a design discussion, not an automatic veto.
- [docs/specs/](../../../docs/specs/): risk-triggered change contracts.
- [docs/developers/testing.md](../../../docs/developers/testing.md): risk-to-layer selection, test topology, evidence rules, and maintenance budget.
- [docs/developers/architecture.md](../../../docs/developers/architecture.md): the module map and seams.

## Blocking requirements

### Universal (applies to any repository)

1. **New prose receives semantic review.** Critically review every added or changed Markdown passage, JSDoc, comment, prompt, description, diagnostic, and visible string. Verify required coverage, accuracy, placement, and editorial quality against the owning code or behavior; automated checks do not establish those properties.
2. **Docs match the code.** Config, defaults, errors, wire fields, events, and public behavior update the owning docs and JSDoc in the same diff.
3. **Contracts and decisions use the right artifact.** A risk-boundary change has an Approved spec; a durable choice with real alternatives has a decision record. Do not demand an ADR as a change log.
4. **Tests provide minimum sufficient behavior evidence.** Name the meaningful regression each changed test prevents and place its primary evidence at the lowest sufficiently real boundary. A fix links an existing deterministic reproduction or adds a regression test that fails before the fix and passes afterward; redundant coverage or implementation-only assertions do not satisfy this requirement.
5. **External-source provenance is retained.** If implementation is materially derived from a paper, article, community post, benchmark, research report, or copied/adapted code, cite it at the closest stable code location or link that location to a decision record whose `## Links` cites the source. A pull request, issue, prompt, or chat-only citation does not count; copied or adapted material also preserves applicable license and NOTICE requirements.

### Project-specific (instantiated at seed time from this project's own rules)

1. **科研真实性与契约：** 模拟、未审核标签和缺失真值不冒充实测结果；公共字段与 fixture/调用方同步，旧 API 保持兼容。
2. **数据与模型：** 原始视频、权重、身份、凭据与受限来源不入库；模型路径、媒体读取和导出不越过受信任边界。
3. **单一事实源：** manifest 管治理路径，MVP 文档管科研设计，Issue 管任务；不另建队列、指标公式或视频坐标体系。
4. **学习指导：** Agent 路由能读取本地 VibeWise Learn，尊重已确认/待确认/暂停状态；不得伪造成员推理或将设计确认当实施授权。
5. **变更权限：** 不安装 hook、全局插件，不擅自改远端权限或生产部署；治理能力变更使用 repo-governance，保留授权范围。

## Manual checks

### Project-specific (instantiated at seed time from this project's stack and known failure modes)

- **Django/任务状态：** 追踪 Task→处理线程与 DB 更新；并发/恢复改动以真实数据库/进程边界验证，不能以进度字典 mock 证明恢复。
- **视频/模型：** 检查 PTS、左上 xywhn 转换、Run 内 ID、void 0→ignore 255、数据分组和缺失指标语义；相关 fixture 只是示例约束。
- **Vue/Canvas：** 播放、暂停、seek、letterbox、DPR 与全屏需要浏览器证据；构建不能证明图层对齐。
- **治理与学习入口：** 检查 AGENTS/CLAUDE/常驻 skills、manifest hash、上游许可证和 VibeWise 文件完整性；无 profile/暂停/待实施决定的恢复路径不得被静默跳过。
- **证据位置：** 公开边界反例在 tests/，Web 层在 backend/app/tests.py，科研例子在 fixtures/mvp/；功能实现时才增加真实算法/交互证据，不造不存在的测试命令。

### Universal fallbacks (apply where the project has no specific rule)

- **Intent and interface contracts:** trace both sides of every changed interface. Confirm the implementation matches the change and any decision record, including errors, cancellation, ownership, and disposal.
- **Lifecycle and concurrency:** for async setup, callbacks, processes, or teardown, check races before publication, cancellation during awaits, independent error reporting, and complete cleanup.
- **Human readability:** read changed code from its entry point downward. The primary path stays understandable without opening every helper. Challenge abstractions that only forward or rename, mixed abstraction levels, misleading or generic names, new synonyms for existing concepts, and logic outside its owning boundary. Block when these make behavior unreliable to infer, hide effects or cost, or violate established vocabulary or boundaries; otherwise report subjective polish as advisory. Line counts, parameter counts, duplication, and complexity scores are signals, not verdicts.
- **Scope and necessity:** map each abstraction, option, defensive copy, and compatibility path to its current contract and consumer. Challenge unrelated features and speculative generality.
- **Bounds cover the final operation:** probe tiny and exact limits, oversized chunks, and multibyte text for byte limits.
- **Test value and boundary:** identify the contract each changed test owns, challenge duplicate evidence, and use the real shipped entry path whenever packaging, configuration, process setup, or wiring is part of the risk.
