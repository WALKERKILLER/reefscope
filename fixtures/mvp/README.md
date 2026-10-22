# MVP 示例契约

本目录为公开模拟数据，不含真实视频、权重、专家标注或模型测量。入口为 `analysis-run.sample.json`，轨迹、热图、taxonomy、实验/报告、预标注与大屏样例各自声明 schema/status，跨文件约束由 [校验器](../../docs/mvp/validate_fixtures.py) 验证。

运行 `python3 scripts/check.py` 可执行示例检查。科研字段与含义以 [MVP 契约](../../docs/mvp/02-contracts.md) 为准；示例通过不表示模型已实现或达到科学门槛。
