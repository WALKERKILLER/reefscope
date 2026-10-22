# 模型训练证据与报告

本文是参考说明。页面入口为“记录 → 模型与报告”；视频分析入口见 [鱼类分析 Worker](fish-analysis.md)。

## 导入与保存

维护者使用 `python manage.py import_fish_training MODEL_ID DIRECTORY` 从受控本地目录导入 `results.csv`，可选读取 `args.yaml`、`run_metadata.json` 与 checkpoint 摘要。注册模型必须存在；若目录包含 `weights/best.pt`，其 SHA256 必须匹配注册权重。HTTP 不接受服务器路径。

导入只保存白名单数值配置、逐 epoch 数值、文件摘要与缺失项，不保存数据路径、设备名称、原始日志或图片。CSV 拒绝重复/逆序 epoch、非有限数值及越界概率；YAML 使用安全解析并丢弃路径字段。每次导入创建独立 TrainingRun 和 TrainingReport，公开 API 不提供修改入口。

`--evaluation UUID` 可关联同模型的 EvaluationRun；`--baseline UUID` 仅在数据摘要、协议与评估配置一致时接受比较。EvaluationRun 是证据存储契约，训练导入命令不运行独立评估，也不从验证曲线生成评估记录。

## 页面与导出

页面展示模型的训练、评估与报告历史，实际 CSV 曲线及七章确定性报告。验证 mAP50、验证 mAP50-95 的最优 epoch 与框架 best fitness 分别保存；缺少实际 checkpoint epoch 时保持 N/A。

`GET /api/v1/model-versions/{model_id}/history` 返回各类最新 100 条记录；`GET /api/v1/reports/{uuid}` 返回冻结报告和曲线；`GET /api/v1/evaluations/{uuid}` 返回评估证据。报告导出使用 `/api/v1/reports/{uuid}/export?export=markdown|html`；HTML 提供 A4 打印样式，可通过浏览器打印保存 PDF，不是服务端 PDF 文件接口。

报告输出转义 HTML，禁止脚本和远程资源。所有报告默认待人工审阅。没有独立测试、人工 ID 真值或固定硬件 benchmark 时，对应字段保持 N/A；验证曲线不能证明泛化精度、IDF1 或 HOTA。

## 验证边界

`backend/app/test_reports.py` 检查数值解析、YAML 白名单、不可变记录、基线可比性与导出边界。实际 UI 还需检查模型/报告切换、曲线缩放、原始数值、下载和打印布局；构建成功不能替代这些检查。
