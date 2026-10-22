# 验证与证据

## 本地与 CI 对应

- `python3 scripts/check.py`：执行治理清单中的标准库检查、fixture smoke test、检查器自身测试和已跟踪文件差异检查。
- `backend/` 中运行 `python manage.py check`、`python manage.py makemigrations --check --dry-run`、`python manage.py test`：验证 Web 层与健康检查，不加载 ML 模型。
- `frontend/` 中运行 `npm ci`、`npm run build`：验证锁文件安装与生产构建。
- `docker compose config --quiet`：验证 Compose 结构，不代表镜像能运行或 GPU 可用。

fixture 检查器保留在 `docs/mvp/validate_fixtures.py`，其 assert 不得用 `python -O` 执行。它验证示例间约束，不是任意不可信 API 输入的完整 schema 校验器。

## 后续功能验收

追踪需要人工 ID 真值，热图需要时间积分守恒，珊瑚映射需要 void/ignore 和专家复核，评估需要站点分组测试。具体标准由 [阶段验收](../mvp/15-mvp-v2-milestones.md) 负责。

UI 改动必须实际检查播放、暂停、seek、全屏、缩放与画面坐标对齐。当前未建立浏览器自动化和真实 GPU 推理测试；新增相关功能时补齐，不把 build 当交互通过。

CI 的 Web 层依赖以 `backend/requirements-ci.in` 为输入，用 `uv pip compile --python-version 3.12 backend/requirements-ci.in -o backend/requirements-ci.txt` 更新锁定文件。此文件不覆盖 ML 运行依赖。
