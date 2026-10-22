# 证据索引

## Traversal

- Pass 1：读取旧应用入口、模型、路由、依赖与容器，识别既有行为及静态审计边界。
- Pass 2：对照 repo-seed manifest、常驻 skills 与 VibeWise 分发清单、fixture 检查器、反例测试和 CI，确认新成员基础检查路径。

覆盖治理与示例契约；不覆盖真实视频推理、GPU 性能和大屏交互。

| Claim | Evidence | Confidence | Caveat | Used by |
| --- | --- | --- | --- | --- |
| 本地与 CI 共用门禁 | `scripts/check.py:main`、`.github/workflows/ci.yml` | 高 | 不代表全部功能验收 | walkthrough |
| 权重不应入库 | `scripts/validate_repository.py:file_errors`、`tests/test_repository_policy.py` | 高 | 仅扫描 Git 可见文件和有限模式 | walkthrough |
| 指标可保留缺失值 | `docs/mvp/validate_fixtures.py:check`、`fixtures/mvp/training-report.sample.json` | 高 | 是模拟契约 | walkthrough |

Falsifying check：临时调用 `file_errors('model.pt', b'example')` 若返回空列表，则权重阻断说明失效；已有单测覆盖该反例。

Likely reader follow-up：为什么基础检查通过仍不能报告白化精度？因为示例没有真实真值和实测指标，见开发测试说明。
