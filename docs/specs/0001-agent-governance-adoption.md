# Agent 治理与指导流程接入

Artifact-Version: 1
Status: Approved

## Intent

范围依据 2026-10-22 用户明确要求：按 repo-seed 规整仓库，并将 VibeWise 指导功能内嵌到 Agent 协作。保留业务代码、科研契约和已有 Issue。范围不包含全局插件、Git hook、生产部署或重写 Git 历史。

## Contract

repo-seed manifest 管治理路径、Core 能力与文件所有权；现有 CI/CODEOWNERS 复用。AGENTS/CLAUDE 能定位三个治理 skills 与固定版本 VibeWise Learn；默认开发会话按学习指南恢复待确认状态，成员可暂停或直接授权实施。个人学习状态不跟踪，不伪造画像或授权。

架构/测试继续使用现有 owner，决策记录保持编号并迁移为 MADR；移除自建第二份治理清单。第三方许可与来源保留，应用整体仍 UNLICENSED。

## Plan

原生 dry-run/adoption，实例化项目政策，分发 Learn 和来源摘要，统一检查入口与 CI，执行验证后按正常 PR 交付。

## Verification

运行上游 gates、治理审计、项目检查、来源完整性与故障反例测试。核对现有应用源文件无差异、学习状态忽略、未安装 hook；验证项目模板/技能引用可达，manifest 更新后重跑不覆盖 user-owned 内容。

## Evidence

验证实现见 [门禁入口](../../scripts/check.py)、[项目校验](../../scripts/validate_repository.py)、[反例测试](../../tests/test_repository_policy.py)、[学习路由](../agents/learning-workflow.md)。实际 checks 与局限在 PR 报告；静态检查不声称完整学习对话已验收。
