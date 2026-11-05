# 观测报告

本文是参考说明，契约见 [观测报告 spec](../specs/draft-observation-reports.md)，取舍见 [0006](../adr/0006-observation-report-agent.md)。页面入口为主导航“观测报告”；AI 解读服务在顶栏齿轮按钮或报告页的“AI 解读”按钮中配置。

## 流程

1. 新建观测点（名称、水深、坐标、备注）。坐标只在平台内显示。
2. 选择观测日期和视频分析。候选列表按视频取最新一次已完成的鱼类和珊瑚 Run，一份报告最多 8 个 Run。
3. 可选录入环境数据。“预览数值”只计算，不保存，也不外发。
4. “生成报告”保存不可变的报告记录；开启“附加 AI 解读”时，同步请求已配置的服务。AI 失败不影响确定性部分。
5. 下一次在同一观测点生成报告时，自动与更早日期的最新报告比较。

## 指标口径

| 指标 | 定义 | 解释边界 | 依据 |
| --- | --- | --- | --- |
| 平均可见鱼数（MeanCount） | 追踪框总数 ÷ 处理帧数；`tracking_frame_stride` 固定为 1，无鱼帧计 0 | 相对丰度，不是个体数或密度；无 ID 的检测不计入 | Schobernd et al. 2014 |
| 画面峰值鱼数 | 单帧追踪框数的最大值及其时间 | 类似 MaxN，鱼多时偏低；单类模型只能给合并峰值 | Schobernd et al. 2014；Hsu et al. 2025 |
| 有鱼帧比例 | 有追踪框的帧 ÷ 处理帧数 | 描述性指标 | — |
| 追踪 ID 数、轨迹时长中位数、≥ 5 s 轨迹 | 每个 ID 首末观测的时间差 | ID 会因遮挡断轨重复；中位数很短说明断轨多 | Luiten et al. 2021（无真值不评 HOTA） |
| track-seconds | 沿用鱼类窗口统计的积分 | 可超过视频时长 | [鱼类分析](fish-analysis.md) |
| 珊瑚像素占比 | 背景已分离采样帧中珊瑚像素 ÷ 全部像素 | 画面平面统计，不是覆盖率 | GCRMN 2020；Beijbom et al. 2015 |
| 珊瑚像素中的白化比例 | 白化像素 ÷ 珊瑚像素 | 不是群体白化发生率或严重度 | AGRRA 2023 |
| 观测点合并值 | 各视频原始分子分母相加后再相除 | 只在两段以上视频时单列 | — |

缺失项保持 N/A 并给出原因：检测 AP50、IDF1/HOTA、活珊瑚覆盖率、群体白化发生率、白化分割精度、死亡与藻覆比例（当前模型只有背景、未白化、白化三类）。

## 环境与 CRW 警报等级

SST、原位水温、HotSpot、DHW、数据来源和产品日期都由用户录入，平台只做范围校验（SST 与水温 −5–45 °C，HotSpot −15–15 °C，DHW 0–100 °C-weeks）。警报等级按 [NOAA CRW v3.1](https://coralreefwatch.noaa.gov/product/5km/methodology.php)：

| 条件 | 等级 |
| --- | --- |
| HotSpot ≤ 0 | 无胁迫 |
| 0 < HotSpot < 1 | 白化观察 |
| HotSpot ≥ 1，0 < DHW < 4 | 白化预警 |
| HotSpot ≥ 1，DHW 4–8 / 8–12 / 12–16 / 16–20 / ≥ 20 | 警报 1 / 2 / 3 / 4 / 5 级 |

HotSpot ≥ 1 而 DHW 缺失时不给等级；DHW 为 0 时提示核对录入值。卫星产品是约 5 km 网格的背景，报告不用它解释白化原因。

## 比较

只与同一观测点更早日期的最新报告比较合并值。模型、分析参数相同且两次都标记为固定机位时，给出变化量（比例以百分点计）；否则只并列两次数值并列出不可比的原因。镜头运动在分析配置中设置，默认“未知”，因此默认不计算变化量。

## AI 解读服务

- **格式**：OpenAI 兼容填写包含 `/v1` 的 Base URL，请求 `{base}/chat/completions`；Anthropic Messages 填写服务根地址，请求 `{base}/v1/messages`（Base URL 已以 `/v1` 结尾时只追加 `/messages`）。对话框显示解析后的请求地址。OpenAI 格式不发送 token 上限和 temperature；Anthropic 格式发送“最大输出 tokens”。
- **请求边界**：只接受 http/https，不跟随重定向，单次超时 5–100 s，响应上限 1 MB。后端进程的 `HTTP(S)_PROXY` 环境变量照常生效。
- **Key**：只写。保存在 `REPORT_AGENT_KEY_PATH`（默认 `backend/.secrets/report-agent.key`，权限 0600，被 Git 忽略）。响应只返回是否已保存和末四位。修改 Base URL 时若没有同时填写新 Key，旧 Key 会被清除；“测试连接”只使用已保存的设置。
- **外发数据**：站点名称、观测日期、视频序号、镜头运动、各指标的标签、显示值、状态与原因、可比性、模型是否有独立评估、局限说明和资料卡。不发送坐标、文件名、Run ID 和画面。
- **输出与审计**：模型输出固定 JSON；数值只写 `{{metric_id}}`，由服务端替换；引用只用资料卡 ID（见 `backend/app/observation/sources.py`）。服务端记录未核对数字、未知指标和未知引用。页面用虚线下划线标出平台填入的数值，用黄色标出模型自行写出的数字；导出写成“（未核对）”。
- **记录**：报告保存提示词版本 `reefscope-observation-agent/v1`、请求内容的 SHA-256、格式、模型、主机名、耗时、token 用量和错误码，不保存 Key 和完整响应。

## API

- `GET/PUT /api/v1/report-agent/config`、`POST /api/v1/report-agent/test`
- `GET/POST /api/v1/sites`、`GET/PATCH/DELETE /api/v1/sites/{uuid}`、`GET /api/v1/sites/{uuid}/reports`
- `GET /api/v1/observation-reports/candidates`、`POST /api/v1/observation-reports/preview`、`POST /api/v1/observation-reports`
- `GET /api/v1/observation-reports/{uuid}`、`GET /api/v1/observation-reports/{uuid}/export?export=markdown|html`

## 部署

Docker 的 Gunicorn 为 1 个进程、4 个线程，等待 AI 服务时其他请求不受阻塞。`docker-compose.yml` 把 `backend/.secrets/` 挂载到容器，重建容器后 Key 仍在。平台没有登录鉴权，只应在受信任的本机或内网使用。

## 与组员调研的对照

组员整理的《浅海珊瑚监测指标与平台集成说明》是本模块的起点。已采纳：MeanCount 与画面峰值的分母规则、零检测帧计 0、比例只转换一次、缺失项保留 N/A 和原因、AI 只读不写指标、文献不替代本地结果。已核对或修正：

- 文中 E07（doi:10.1007/s00338-024-02613-6）正式发表于 Coral Reefs 44(2):435–449（2025）。
- 文中假设的六类珊瑚标签（死亡、藻覆、未知、ignore）当前模型不输出，相关比例保持 N/A。
- 文中引用的 `docs/knowledge-base/`、`docs/mvp/16`、`docs/mvp/18` 不在仓库中；资料卡改为 `sources.py` 中逐条核对过的条目。
- CRW 警报等级需要 HotSpot 与 DHW 同时判定，不能只看 DHW。

暂缓：物种丰富度、生物量、群体白化发生率、大型藻类覆盖、底栖 ROI 覆盖率，都需要新的标注或现场调查数据。

## 验证边界

`backend/app/test_observation.py` 用本地 HTTP 服务验证两种接口格式、Key 存储、URL 与 Key 校验、提示词外发内容、片段审计、失败回退、重定向拒绝和不可变记录，并覆盖教学例、CRW 边界与比较规则。测试不调用真实模型服务，也不证明任何模型的写作质量；生成的解读必须人工审阅。
