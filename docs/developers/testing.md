# 验证与证据

## 本地与 CI 对应

- `python3 scripts/check.py`：先执行 repo-seed manifest 选择的治理门禁，再执行项目公开边界、VibeWise 分发完整性、fixture smoke test、检查器反例测试和 Git 差异检查。
- `backend/` 中运行 `python manage.py check`、`python manage.py makemigrations --check --dry-run`、`python manage.py test`：验证 Web 层与健康检查，不加载 ML 模型。
- `frontend/` 中运行 `npm ci`、`npm run build`：验证锁文件安装与生产构建。
- `docker compose config --quiet`：验证 Compose 结构，不代表镜像能运行或 GPU 可用。

fixture 检查器保留在 `docs/mvp/validate_fixtures.py`，其 assert 不得用 `python -O` 执行。它验证示例间约束，不是任意不可信 API 输入的完整 schema 校验器。

## 后续功能验收

追踪需要人工 ID 真值，热图需要时间积分守恒，珊瑚映射需要 void/ignore 和专家复核，评估需要站点分组测试。具体标准由 [阶段验收](../mvp/15-mvp-v2-milestones.md) 负责。

UI 改动必须实际检查播放、暂停、seek、全屏、缩放与画面坐标对齐。当前未建立浏览器自动化和真实 GPU 推理测试；新增相关功能时补齐，不把 build 当交互通过。

CI 的 Web 层依赖以 `backend/requirements-ci.in` 为输入，用 `uv pip compile --python-version 3.12 backend/requirements-ci.in -o backend/requirements-ci.txt` 更新锁定文件。此文件不覆盖 ML 运行依赖。

## 风险、拓扑与证据

测试保护实际行为与边界，优先选最低但足够真实的一层；不以测试数量或覆盖率代替可信证据。纯判断用最小单测，文件/DB/Worker 等状态边界用真实模块组合，公共 CLI/API/UI 在实际入口验证；安全、迁移和逃逸故障才增加必要的纵深防护。

当前测试位置：`tests/test_repository_policy.py` 检查公开文件与指导入口的拒绝反例；`backend/app/tests.py` 经 Django runner 验证健康/路由；`docs/mvp/validate_fixtures.py` 读取共享 `fixtures/mvp/`。上游 `scripts/verify-*.mjs` 校验治理格式/生命周期/来源清单，`scripts/run-gates.mjs` 从 manifest 选择它们。

目前没有真实 GPU、Worker 恢复和浏览器端到端测试；相关功能改动时在其实际边界新增，不创造空测试层级。外部网络/硬件可隔离，项目自己的组合尽量保持真实；断言公开结果、退出状态和持久化状态，不依赖私有调用顺序。

文档或机械变更用语义 Review 和门禁，不制造无行为意义的测试。变更后的测试应能揭示所述回归；重复保护同一行为的测试需说明额外风险。学习指导的静态入口/摘要校验不等同于 LLM 实际引导质量测试。
