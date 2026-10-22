# 项目地图

[当前架构](../developers/architecture.md) 负责目录与数据流；[工作包](../mvp/10-work-packages-and-integration.md) 负责未来协作边界。当前应用是同步 API 加后台线程，尚无可靠 Worker、真实追踪和珊瑚服务。

公共数据示例在 `fixtures/mvp/`；校验入口在 `scripts/check.py`；科研契约由 `docs/mvp/02-contracts.md` 管理。新增模型和 UI 从相关工作包切入，不重写既有应用。

治理路径与文件所有权见 `.repo-seed/manifest.json`，本地与 CI 总入口仍是 `scripts/check.py`，其中上游门禁由 `scripts/run-gates.mjs` 执行。学习指南以 `.agents/skills/vibe-wise-learn/` 分发，Agent 读取根路由后恢复本地状态。
