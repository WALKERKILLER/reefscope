# ReefScope

水下视频中的鱼类活动与珊瑚健康研究平台。

ReefScope 从已有 Vue / Django 鱼类检测应用出发，规划同一段视频的鱼类追踪、画面坐标热力图、珊瑚分割、可重算训练报告与海洋信息大屏。当前版本是**可协作的研究开发基线**，新增科研能力仍需逐项实现。

## 当前能力

- 已纳入：原有上传、YOLO 检测、任务查询、视频回放源码和 Docker 配置。
- 已提供：MVP v2 研究文档、模拟数据契约、健康检查、CI 与手动镜像发布流程。
- 待实现：可靠 Worker、真实 track ID、热图、珊瑚训练、评测报告及 `/wall` 大屏。
- 未提供：用户视频、模型权重、训练数据、真实精度结果或生产部署。

原应用的推理需要自行取得授权的鱼类模型和 ffmpeg。`fixtures/mvp/` 全部是示例数据；示例通过校验不代表模型达到科研要求。

## 从哪里开始

首次加入先读 [开发入口](docs/developers/README.md)，再按 [协作流程](CONTRIBUTING.md) 认领工作包。
研究范围见 [MVP 总览](docs/mvp/README.md) 和 [阶段验收](docs/mvp/15-mvp-v2-milestones.md)。全部资料从 [文档导航](docs/README.md) 进入。

## 十分钟基础检查

需要 Python 3.12、Node.js 22、npm；不需要 GPU 或权重。

```bash
python3 scripts/check.py
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-ci.txt
cd backend
../.venv/bin/python manage.py check
../.venv/bin/python manage.py test
cd ../frontend
npm ci
npm run build
```

这些命令覆盖基础治理、模拟契约、Django 和前端构建。运行原应用见 [本地开发](docs/developers/development.md)；本地演示端口仅绑定回环地址，当前 API 尚无访问控制，不可直接用作公网服务。

## 科研约束

画面热图以 `image_plane` 和 `track_seconds` 表达，不能解读为地理热点或鱼类种群数量。珊瑚标签映射须专家复核；训练集和测试集按站点、潜次与父视频分组。缺少真值时指标必须保留 `null` 及原因。

## 来源与许可

见 [来源、授权与复用边界](docs/developers/provenance.md)。公开可见不代表已授予再分发许可。当前没有给继承源码重新套用 MIT 等许可证；数据、模型和第三方依赖按各自条款管理。
