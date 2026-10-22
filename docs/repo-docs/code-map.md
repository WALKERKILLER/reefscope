# 基础检查的改动位置

先读 [检查流程](walkthroughs/one-real-run.md)，再用以下位置定位修改。

- `scripts/check.py:main`：执行 `.repo/governance.json` 清单；新增门禁先改清单。
- `scripts/validate_repository.py:validate`：文档入口、相对链接和 Git 可见文件边界。
- `scripts/validate_repository.py:file_errors`：敏感路径与文件策略；反例在 `tests/test_repository_policy.py`。
- `docs/mvp/validate_fixtures.py:check`：示例跨文件约束；输入在 `fixtures/mvp/`。
- `.github/workflows/ci.yml`：调用治理入口，并分别检查后端与前端。
- `.github/workflows/publish.yml`：主分支手动触发，复用 CI 后发布镜像。

范围外：应用业务代码和未实现的科研模块，分别由 [当前架构](../developers/architecture.md) 与 [MVP 工作包](../mvp/10-work-packages-and-integration.md) 负责。

Evidence status: Confirmed unless noted.
