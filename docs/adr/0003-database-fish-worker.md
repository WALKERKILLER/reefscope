# 0003：本地鱼类分析使用数据库领取和独立 Worker

## Status
Proposed
Class: architecture

## Context and Problem Statement

鱼类分析需要脱离 Web 进程执行，保留多次 Run、故障恢复和模型状态隔离。应用使用 SQLite，开发环境无需消息代理。

## Decision Drivers

优先保证 Run 只由一个 Worker 领取、过期执行不能覆盖新 attempt，以及已有本地研究环境可直接运行。模型加载成本需要摊销，追踪状态不能跨 Run 传播。

## Considered Options

- 延用 Web 内 daemon Thread 和进程字典。
- 引入 Celery 与独立消息代理。
- 数据库条件领取、租约与 attempt token，独立串行 Worker。

## Decision Outcome

本实现选择数据库条件领取和独立 Worker。`queued` 条件更新成功才算领取，后续写入校验 token、running 和未过期租约。过期任务由轮询标为 failed，由用户显式重试。检测模型缓存容量为一个，每个 Run 前后重置 tracker。

## Pros and Cons of the Options

Web 线程启动简单，但进程退出会丢执行，进程字典也不能支持可靠恢复。Celery 适合多机调度，但增加消息代理、部署和恢复配置；当前本地单机工作量不足以证明这项成本。数据库 Worker 保留现有运行依赖，代价是队列吞吐受 SQLite 和串行推理限制；迁移到多机调度时需重新评估。SQLite 的 `select_for_update()` 不提供行锁，因此领取依赖条件更新的匹配行数。

## Links

- [批准的鱼类分析契约](../specs/0002-fish-analysis.md)。
- [Worker 运行方法](../developers/fish-analysis.md)。
- [Django 5.0 QuerySet update](https://docs.djangoproject.com/en/5.0/ref/models/querysets/#update)。
- [Django 5.0 SQLite select_for_update 限制](https://docs.djangoproject.com/en/5.0/ref/databases/#queryset-select-for-update-not-supported)。
- [Ultralytics 连续帧追踪](https://docs.ultralytics.com/modes/track/#persisting-tracks-loop)。
