# 05 · 依照 VibeWise Learn 的分阶段设计检查点

**状态：待用户推理与确认。** 已参照 `nykooi1/vibe-wise` 的 `skills/learn/SKILL.md`、`behavior.md`、`onboarding.md`；该 Skill 的核心是“开发者提出工程思路 → AI 反馈并解释权衡 → 确认设计 → 允许实现”，而不是套用某种固定架构。

为了让当前用户直接得到代码扫描与初步架构，本轮先把设计作为**未确认提案**写入 `docs/mvp`，不假造学习偏好、团队决定或实现授权；不安装远程 Skill 代码、不读取其 hooks、也不声称已启动完整 VibeWise 会话。

## System check（已核实的现状）

```text
Vue + Artplayer/Canvas
     |
     v
Django upload/process/task
     |
     v
Daemon Thread -> YOLO predict -> detections JSON / result MP4
     |
     v
前端 buildTracks 局部插值 / RightPanel 逐框计数
```

未知：采集相机是否移动、训练显卡、视频总量/站点数、珊瑚专家标签协议、团队人数、部署受众（仅校内 or 公网）。

## Build checkpoint 1 · 热力图的“空间”是什么？（已回答）

**背景概念：** 追踪 ID 将同一鱼的检测框串成视频内轨迹；热图要确定坐标系，才能解释数据。

**待思考：** 如果相机移动，你认为高亮的“鱼经常经过的位置”应当代表镜头画面位置，还是海底某个固定地理区域？为什么？

- 备选 A（MVP 默认提案）：只有画面二维轨迹和相对热图，固定机位效果明确；移动机位标明非地理热点。
- 备选 B（下一阶段）：对相机运动做配准/SLAM/正射，把轨迹投影到空间地图；投入和标定要求明显增加。

**用户已确认：** 视频画面中的鱼类活动位置 image_plane。已记录为 ADR-001，不再重复要求确认。拍摄方式只影响机位运动告警和算法对照。

## Build checkpoint 2 · 什么才算“一条鱼”？

- 现有 `detections.length` 是总检测事件数，同一鱼可能重复很多次。
- MOT Track ID 可避免帧间重复，但遮挡/出入镜头与 ID switch 会把同一鱼分成多条轨迹。
- **待思考：** 平台展示 track count、某一时刻同时可见鱼数，还是要估算生物学个体数量？三者不能混为一谈。

## Build checkpoint 3 · 珊瑚健康的真值定义

- 预训练模型覆盖多种珊瑚/底栖类别，但不同相机、水色造成的白/浅色并非天然等同白化。
- **待思考：** 谁审核“白化/死亡/藻类覆盖/状态未知”？当只凭视频判断不出死亡或褪色时，应标未知还是强制分类？

**AI 提案：** 第一轮保留 uncertain + ignore，形成 expert-reviewed gold set；比“漂亮的六色分割图”更接近可发表结果。

## Design checkpoint（待评审）

拟定组合：保留 Vue/Django；新 AnalysisRun + 单 Worker；后端 YOLO+MOT；CoralscapesV2 SegFormer95 先推理再微调；文件保存轨迹/掩膜；前端分层叠加图层；科研指标附统计范围与分母。

**权衡：** 最短、少新依赖、可并行；单 Worker 吞吐受限，移动镜头的地图能力未覆盖，初期人工标注不能跳过。

只有用户讨论并确认后，才将它标记为 `CONFIRMED`，之后进入 **Implementation checkpoint**（按 backlog 小 PR 逐个授权）。

## Implementation checkpoint（未来）

M0 先做真实健康检查、配置路径修正、分析 Run + Worker，不破坏旧接口；通过契约测试和回归后，再开始 M1/M2/M3。

## 导航

见 `00-repo-audit.md`、`01-architecture.md`、`02-contracts.md`、`03-ml-evaluation.md`、`04-backlog.md`。在 Codex/Claude Code 中正式使用 VibeWise 时应按照官方安装方式运行 learn，再回答其逐项 onboarding；本仓库的图和审计文档可作为证据输入。


## 此次学习式设计的更新

已确认的需求：补全珊瑚训练研究、官方数据/模型权重/论文与可复用开源方案，便于正式分工。技术提案依然标为 proposed，不把资料调研等同于用户批准技术栈。材料详见 06/07/08/10/11 子文档。
