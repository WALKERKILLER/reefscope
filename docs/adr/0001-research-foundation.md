# 0001：沿用旧应用建立公开协作基线

## Status
Superseded by [0002](0002-managed-agent-governance.md)
Class: process

## Context and Problem Statement

团队已有 Vue/Django 鱼类检测应用和 MVP v2 调研，需要按接口协作并保留科研证据。

## Decision Drivers

保留既有应用和接口，避免公开权重、数据与受限历史，先建立可验证工程基础。

## Considered Options

- 重写应用。
- 直接镜像旧仓库历史。
- 源码快照加项目自建治理清单。

## Decision Outcome

本记录冻结最初选择：采用 ReefScope 名称与源码快照，保留 Vue/Django、旧 API 和研究文档，排除权重、数据和旧历史；标准库清单驱动基础检查，镜像发布手动触发。治理实现由 0002 替代，应用保留与公开边界继续有效。

## Pros and Cons of the Options

重写扩大回归范围；直接镜像会携带权重与受限信息。快照控制公开内容，但失去原始逐次提交追踪；自建治理缺少上游升级与常驻流程，因此仅作被冻结的初始选择保留。

## Links

- [0002：正式治理与学习指导](0002-managed-agent-governance.md)。
- [测试政策](../developers/testing.md)。
- [来源与许可](../developers/provenance.md)。
