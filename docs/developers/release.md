# CI 与镜像发布

## 自动检查

每个 PR 和 main 推送运行 CI：仓库规则与 fixture、Django Web 层检查/测试、Vue 构建、Compose 语法检查。第三方 Actions 固定完整 SHA，默认 token 只读；PR 不获得包发布权限。

治理事实源位于 `.repo-seed/manifest.json`；`scripts/run-gates.mjs` 使用上游 verifier，`python3 scripts/check.py` 编排上游门禁与项目专属检查，本地与 CI 共用。

## 手动发布

维护者在 Actions 的 Publish images 页面，从 `main` 手动运行。流程先调用同一套 CI，通过后将 backend/frontend 镜像以不可变提交 SHA 标签推到 GHCR。流程仅在发布 job 取得 `packages: write`，无需额外 PAT。镜像不含模型权重和用户数据。

发布流程只上传镜像，不部署任何服务器。首次镜像发布后按需检查 GHCR 包的可见性；仓库公开不自动证明包公开。回滚使用上一个验证过的 SHA 标签。

## 公网部署前

当前没有生产部署目标。启用认证/授权、媒体访问控制、上传内容与大小校验、独立 Worker 恢复机制、可靠备份后，另提部署 spec。关闭 DEBUG、设置独立随机密钥及精确 hosts/CORS，确认数据和权重再分发许可。继承的 Django/ML 依赖较旧，运行依赖尚未完全锁定，需单独做升级回归与安全审查。

## 保护与成员

建议 main 要求 PR、一个非作者评审、通过 `repository` / `backend` / `frontend` 检查并解决讨论，阻止强推和删除。CODEOWNERS 初始维护者是仓库所有者，算法领域负责人由团队后续添加。GitHub 若因账户方案拒绝保护设置，需在团队中执行同等人工评审规则。
