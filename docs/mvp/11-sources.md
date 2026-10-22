# 11 · 原始资料索引与核查记录

> 核查日期：**2026-10-14**。优先官方论文项目页、Hugging Face model/dataset card、GitHub README / LICENSE / 文档；论文指标仅在其发表的指定测试集上有效。链接可能更新，重新开发时应固定 commit、dataset revision、model revision 和 LicenseManifest。

| 代码 | 名称 | 直接资料 | 此次可支持的事实 |
| --- | --- | --- | --- |
| S01 | Ultralytics YOLO Track | https://docs.ultralytics.com/modes/track/ | model.track, persist=True, ByteTrack/BoT-SORT 和 tracker state；**使用原项目 pinned ultralytics==8.3.109 前要确认对应接口**。 |
| S02 | Supervision 热图/追踪示例 | https://github.com/roboflow/supervision/blob/develop/examples/heatmap_and_track/script.py | HeatMapAnnotator、sv.ByteTrack、视频帧处理、ID 叠加；它默认算法不能直接当科研意义的停留时间指标。 |
| S03 | CoralscapesV2 数据集 | https://huggingface.co/datasets/josauder/coralscapesV2 | 2,433 张，95 有效类别及 split、健康复合分类；Apache-2.0；dataset card: 41 dive sites。 |
| S04 | SegFormer-B5 95 checkpoint | https://huggingface.co/EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class | 96 logits（0 void、1..95 valid），segmentation benchmark mIoU 36.420/37.177，训练超参数，Apache-2.0。 |
| S05 | EPFL DeepReefMap / DINOv3 分割家族 | https://github.com/eceo-epfl/deepreefmap | segformer/dinov3 B/L、39/95 模型选项，DINOv3 encoder gated，3D/ortho/benthic_cover；core Apache-2.0、subcomponents 需单独审核。 |
| S06 | CVAT Community 与 segmentation 导出 | https://github.com/cvat-ai/cvat ; https://docs.cvat.ai/docs/dataset_management/formats/format-smask/ | 社区版 MIT、视频/图像协作标注、Segmentation Mask 导出；tracks 属性需另核验格式。 |
| S07 | napari | https://github.com/napari/napari ; https://napari.org/stable/howtos/layers/labels.html | BSD-3-Clause；label layer 绘制/修正像素掩膜。 |
| S08 | FiftyOne | https://github.com/voxel51/fiftyone ; https://docs.voxel51.com/ | 数据集浏览、错误样本审查、模型结果对比；引入前复核本地部署需求和当前依赖许可。 |
| S09 | MLflow Tracking | https://mlflow.org/docs/latest/ml/tracking/ ; https://github.com/mlflow/mlflow | experiment metrics/params/artifacts 跟踪；模型注册使用数据库后端等约束需核对当前版本。 |
| S10 | DVC | https://dvc.org/doc ; https://github.com/iterative/dvc | 数据版本、外部 remote/pipeline reproduction；非小规模首版强制项。 |
| S11 | Apache ECharts | https://echarts.apache.org/en/index.html ; https://github.com/apache/echarts | Apache-2.0 可复用前端图表与热力矩阵；视频 Canvas 叠加仍自管坐标。 |
| S12 | TagLab | https://github.com/cnr-isti-vclab/TagLab | 面向珊瑚正射影像的桌面分割/标注和统计；GPL-3.0，研究借鉴不复制。 |
| S13 | CoralSCOP + CoralMask | https://github.com/zhengziqiang/CoralSCOP | CVPR 2024 珊瑚专门模型、提示分割、掩膜预标注，发布预训练权重；源码和 checkpoint 具体条款单独核查。 |
| S14 | CoralSCOP-LAT | https://github.com/ykwongaq/CoralSCOP-LAT | 珊瑚标注/分割/分析 workflow 参考；该仓库展示 React/FastAPI 技术栈；未验证嵌入能力或完整许可。 |
| S15 | Ultralytics 授权 | https://www.ultralytics.com/license ; https://github.com/ultralytics/ultralytics | AGPL-3.0 及商业许可路线，切勿自动推断可闭源 SaaS。 |
| S16 | DeepReefMap 科研与发布边界 | https://github.com/eceo-epfl/deepreefmap/blob/main/THIRD_PARTY_NOTICES.md | 依赖权重与第三方许可需单独审核；非第一版必选。 |
| S17 | CoralscapesV2 项目/论文 | https://josauder.github.io/coralscapesv2/ | 39/95 类、珊瑚状态、fish instances、场景标注；学术引用 Sauder et al. ECCV Marine Vision 2026。 |
| S18 | CoralscapesV2 官方模型训练脚本 | https://github.com/eceo-epfl/coralscapesScripts | 该仓库主要是 Coralscapes V1 的 39 类脚本；不得假设能直接用于 V2 95 类训练，需单独核实训练结构；训练参数也可从 S04 官方模型卡读取。 |
| S19 | VibeWise Learn Skill | https://github.com/nykooi1/vibe-wise | 设计者先思考、Build/Design/Implementation 检查点，讨论与确认分离；不把我们的技术提案冒充用户决策。 |
| S20 | CVAT Community 许可 | https://github.com/cvat-ai/cvat/blob/develop/README.md | MIT core；serverless assets/FFmpeg 二级许可例外。 |

## 证据冲突 / 不确定性（开发时必须注意）

- **CoralscapesV2 站点数**：官方 dataset card 写 41 dive sites；S04 模型卡个别段落写 55。系统按照 dataset split 中实际 site/dive metadata 计算，split 中列 34+3+5=42 个 site 计数，若有跨 split 重复可能仍为 41 个唯一站点；本文不在没有元数据的情况下“统一解释”。
- **95 类 vs 96 logits**：不是矛盾，而是 0=void + 1..95 有效类；所有转换、交叉熵训练、mask 颜色映射必须维持该区别。
- **指标**：模型卡的 37.177 mIoU 为官方 95 类 held-out 测试，不能推广为中国近海珊瑚白化或“死珊瑚识别准确率”。
- **项目版本漂移**：网页 YOLO 示例使用当前版本（2026），原 SITP 锁定 ultralytics 8.3.109（2025）。不能照搬新参数不经锁定环境 smoke test。
- **许可证**：某些模型/权重/研究代码可能与主仓库不同条款；本表仅列官方已显示或必须待核事项，不能替代发布前许可证核查。
- **资源估计**：无目标机器 GPU、模型实测 batch 与视频尺寸，本文不声称实时 FPS、显存使用、数据下载完成或训练分数达标。

## 推荐参考与引用说明

成果报告至少应引用 CoralscapesV2（2026，ECCV Marine Vision Workshop）、CoralSCOP（2024，CVPR）及实际用到的模型/数据版本；ByteTrack/BoT-SORT 若最终采用也需要引用原论文。对外公开标注数据前需复核采集视频的知识产权、采集授权与涉及站点的信息保护要求。

## 第三轮 2026-10-21 追加资料（GitHub 官方连接器核查）

| 编号 | 资源 | 原始地址 | 已核查的具体能力/边界 |
| --- | --- | --- | --- |
| S21 | YOLO Report Analyst README | https://github.com/xiangshenchi/yolo-report-analyst | MIT，2026-10-21 GitHub API 12 stars / last push 2026-05-10，training results.csv / args.yaml / logs → 7 章报告；是报告 Skill 而非评测引擎。 |
| S22 | YOLO Report Analyst SKILL.md | https://github.com/xiangshenchi/yolo-report-analyst/blob/main/SKILL.md | loss/mAP 解析、best epoch/7章诊断框架；其内置 mAP50 优秀等级与猜测建议不是科研模型验收标准。 |
| S23 | VLM-AutoYOLO README/API/LICENSE | https://github.com/Somnusochi/VLM-AutoYOLO ; https://github.com/Somnusochi/VLM-AutoYOLO/blob/master/docs/API.md | AGPL-3.0，267 stars / last push 2026-09-22；VLM+SAM2/SAM3、SSIM、YOLO/COCO 导入导出、SSE 训练与验证。React/FastAPI，不能直接替换 Django/Vue。 |
| S24 | TrackEval | https://github.com/JonathonLuiten/TrackEval | HOTA、IDF1 等跟踪评价，需要真实逐帧 ID 标注、匹配协议与版本锁定。 |
| S25 | torchmetrics | https://github.com/Lightning-AI/torchmetrics | 语义 IoU/F1/混淆；具体 ignore_index / class 语义须做单元测试。 |
| S26 | NVIDIA LocateAnything-3B 官方权重许可证 | https://huggingface.co/nvidia/LocateAnything-3B | NVIDIA License，模型卡称 academic/non-profit research、非商业；项目代码 AGPL 不自动授予模型权重商业使用权。 |
| S27 | Apache ECharts | https://github.com/apache/echarts | 2026-10-21 GitHub API ~67,560 stars / last push 2026-10-13；Apache-2.0，成熟浏览器图表引擎。 |
| S28 | VisActor VChart | https://github.com/VisActor/VChart | MIT，~1,852 stars / last push 2026-10-20；主打数据叙事交互，拟作为 ECharts 替代 PoC，不同类工具不宜双栈叠加。 |
| S29 | datav-vue3 | https://github.com/vaemusic/datav-vue3 ; https://www.npmjs.com/package/@kjgl77/datav-vue3 | MIT，~642 stars / last push 2024-10-21；Vue3/Vite 装饰组件，按需引入；npm 1.7.4 两年前发布，维护风险。 |
| S30 | IofTV-Screen-Vue3 | https://github.com/daidaibg/IofTV-Screen-Vue3 | MIT，~498 stars / last push 2026-06-06；Vue3/Vite/ECharts / scale-screen，大屏视觉/页面构图参考。 |
| S31 | DataRoom | https://github.com/gcpaas/DataRoom | Apache-2.0，~869 stars / last push 2026-10-20；Vue3+SpringBoot3、几十数据源、AI 生成、编辑器；系统完整较重，作者称开源项目暂无公开演示，商业版单独提供。 |
| S32 | vue-big-screen-plugin | https://github.com/L-noodle/vue-big-screen-plugin | MIT，~169 stars / last push 2021-05-25，旧 VueCLI 技术栈，参考视觉不推荐直接用。 |
| S33 | GoView 社区原型 | https://gitee.com/MTrun/go-view ; https://www.mtruning.club/guide/screenTemplate/vueScreenTemplate.html | 具备低代码大屏视觉示例；官方 GitHub 同名仓库未成功核实，社区/Pro 的代码权利不在本轮确认，不复制源码。 |

**快照边界**：Stars、last push 为 2026-10-21 GitHub API 某时刻结果，可能变更；它们不是性能指标，也不保证开源代码可直接混用。第三方图像/大屏模板素材单独核查授权；未验证的依赖不能仅依据 README 推定已运行成功。
