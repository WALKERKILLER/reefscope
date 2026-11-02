# 鱼类分析 Worker

## 准备与注册

本页说明本地鱼类 Run 的运行方法。安装 [开发环境](development.md) 后，从 `backend/` 执行迁移。Web 环境不需要导入 Ultralytics；实际模型注册和 Worker 需要完整 `requirements.txt`、匹配驱动的 CUDA PyTorch 和授权权重。

```bash
python manage.py migrate
python manage.py register_fish_model fish:local-v1 models/model_best.pt
```

注册命令只读取 `YOLO_MODEL_ROOT` 内的 `.pt` 文件，默认目录为 `backend/models/`。显式加载本地 pickle 权重意味着信任提供者，只注册自己确认来源的权重。模型 ID 不可覆盖；权重变化时使用新 ID。API 返回类别、框架版本和 hash，保留本地路径为私有字段。

## 创建与执行

保持 Web 服务运行，调用模型列表 `GET /api/v1/models`，再以已有 Task ID 创建 fish Run：

```json
{
  "kind": "fish",
  "models": {"fish": "fish:local-v1"},
  "settings": {
    "confidence_threshold": 0.25,
    "iou_threshold": 0.45,
    "tracking_frame_stride": 1,
    "imgsz": 640,
    "allowed_gap_seconds": 0.5,
    "camera_motion": "unknown",
    "scene_cut_frames": []
  }
}
```

将请求发送到 `POST /api/v1/tasks/{task_id}/analysis-runs`。返回 202 和 `run_id`。`GET /api/v1/tasks/{task_id}/analysis-runs` 返回最近 100 个 Run，`GET /api/v1/analysis-runs/{run_id}` 返回状态、attempt、进度和摘要。kind 只接受 fish；配置禁止任意模型路径、设备、URL 和未知字段。

在独立终端执行：

```bash
python manage.py run_analysis_worker
# 只领取并执行一个 Run，或执行一次过期检查。
python manage.py run_analysis_worker --once
```

Worker 优先使用可用 CUDA，CUDA 不可用时使用 CPU，实际设备保存在摘要。每次处理一个 Run，检测权重缓存容量为一个。ByteTrack 连续处理全部帧；Run 前后重置追踪器。已知镜头切换帧通过递增且无重复的 `scene_cut_frames` 声明，切换处重置 tracker 并为后续 ID 增加命名空间偏移。轨迹保留原始 `tracker_track_id` 和 `segment_id`。未声明的镜头切换尚不自动识别。运行期禁止自动安装依赖，不下载额外权重。

## 恢复与产物

Worker 租约为 120 秒，每 10 帧刷新。新 Worker 启动或轮询时将过期 Run 标为 failed；不会自动重跑。`POST /api/v1/analysis-runs/{run_id}/retry` 只允许 failed，最多 3 次总执行机会，其余状态返回 409。旧 attempt token 无法发布完成状态。

产物写入 `ANALYSIS_ROOT/<run_uuid>/<attempt_token>/`，默认位于 `backend/.analysis/`，不通过媒体 URL 暴露。每次 attempt 保留独立的 `tracks.jsonl`、`summary.json` 和 `manifest.json`。manifest 记录输入和权重 hash、配置、框架版本及产物摘要。缺失或校验失败的产物不能发布 completed；保留失败目录供本地诊断。

Run 引用的源视频禁止通过旧任务接口删除或重命名，防止破坏复查。未被 Run 引用的 Task 保留旧操作。不要将 `ANALYSIS_ROOT` 配置到公开静态目录，也不要公开原始视频、权重或包含本地路径的诊断记录。

## 证据边界

轨迹 ID 只在一个 Run 内有效，轨迹数包含遮挡导致的重复计数。PTS 缺失时仅在 fps 有效的情况下回退到帧号时间；摘要记录回退帧数。没有人工真值时不输出 IDF1、IDSW 或独立测试精度。训练拼图和重复图片可验证运行兼容性，不能替代连续视频与人工 GT。

本切片提供注册、入队、Worker、详情与重试。分页轨迹、热图、同源统计导出、评估报告和前端接入按 [批准契约](../specs/0002-fish-analysis.md) 继续实现，尚不声明这些入口可用。
