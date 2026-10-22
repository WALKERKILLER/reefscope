# 0002：采用 repo-seed 管理治理并内嵌 VibeWise Learn

## Status
Accepted
Class: process

## Context and Problem Statement

协作仓库需要可执行、可升级的治理，以及成员能在 Agent 会话实际使用的设计指导。只引用上游原则不能分发技能、校验格式或恢复学习中的待确认决定。

## Decision Drivers

使用上游工具而非另写替代；保留既有文档真源和记录身份；维护成员设计控制、隐私与明确授权。

## Considered Options

- 保留自建治理清单和自然语言倡议。
- 强制所有成员全局安装两个插件。
- repo-seed 原生 adoption 与项目内 VibeWise Learn，由 AGENTS/CLAUDE 路由读取。

## Decision Outcome

采用原生 adoption，manifest 注册既有架构/测试和 docs/adr；Core verifier 与三项常驻 skills 保持上游分发。个人学习 guides 固定 VibeWise revision 并分发到项目 skills，根入口默认载入，尊重暂停与直接实施。项目语义内容标为 user-owned，不安装全局插件或 hook，不更改业务 API、模型或部署。

## Pros and Cons of the Options

自建清单无法获得上游治理契约；全局强制安装影响成员环境且不能保证入口一致。项目分发可随克隆获得流程和来源，但需维护版本摘要；静态检查能验证接线，不能保证每次对话的教学质量。

## Links

- [0001：初始选择](0001-research-foundation.md)。
- [治理迁移 spec](../specs/0001-agent-governance-adoption.md)。
- [repo-seed 固定 revision](https://github.com/EricSanchezok/repo-seed/tree/559b84dec5c7c495df274820b4b2e6c611d304b3)。
- [VibeWise 固定 revision](https://github.com/nykooi1/vibe-wise/tree/eefb53df406ab89e31444684ff32c1df205221f8)。
- [治理来源与摘要](../../.repo-seed/upstream.json)。
