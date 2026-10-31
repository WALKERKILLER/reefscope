<template>
  <aside class="inspector" aria-label="鱼类分析">
    <header class="head">
      <div class="min-w-0">
        <h2>鱼类分析</h2>
        <p class="note truncate" :title="fileName">{{ fileName }}</p>
      </div>
      <UiTooltip text="刷新模型与分析记录">
        <button class="btn btn-ghost btn-icon" @click="boot" :disabled="busy" aria-label="刷新模型与分析记录"><IconRefresh /></button>
      </UiTooltip>
    </header>

    <p v-if="demo" class="banner warn"><IconAlertTriangle />合成演示视频：画面由训练拼图重复生成，结果不代表真实场景精度。</p>
    <p v-if="error" class="banner danger" role="alert"><IconAlertTriangle /><span>{{ error }}</span><button class="link" @click="boot">重新连接</button></p>

    <section class="run" aria-label="分析记录">
      <div class="run-row">
        <div class="field grow">
          <span id="run-label">分析记录</span>
          <UiSelect v-model="selectedId" :options="runOptions" :disabled="!runs.length" placeholder="还没有分析" aria-label="分析记录" />
        </div>
        <UiTooltip text="新建分析">
          <button class="btn btn-icon" :class="{ 'is-on': createOpen }" :aria-expanded="createOpen" aria-controls="create-run" aria-label="新建分析" @click="createOpen = !createOpen"><IconPlus /></button>
        </UiTooltip>
      </div>

      <p v-if="pendingNewer" class="note pending"><IconClock />有 {{ pendingNewer }} 次更新的分析在排队或执行中，完成后可在分析记录中切换。</p>
      <div v-if="run" class="status" aria-live="polite">
        <span class="state" :data-state="run.status"><span class="dot" />{{ states[run.status] || run.status }}</span>
        <span class="note tnum">第 {{ run.attempt }}/3 次尝试</span>
      </div>
      <div v-if="run && (run.status === 'queued' || run.status === 'running')" class="progress" role="progressbar" :aria-valuenow="run.progress" aria-valuemin="0" aria-valuemax="100" aria-label="分析进度"><span :style="{ width: `${run.progress}%` }" /></div>
      <p v-if="run?.status === 'queued'" class="note">等待 Worker 领取。可以继续播放视频。</p>
      <p v-if="run?.status === 'running'" class="note tnum">正在逐帧追踪 · {{ run.progress }}%</p>
      <div v-if="run?.status === 'failed'" class="failed">
        <p>{{ errorText(run.error_code) }}</p>
        <button v-if="run.attempt < 3" class="btn btn-sm" @click="retryRun" :disabled="busy"><IconRefresh />重试分析</button>
      </div>
      <dl v-if="run?.summary?.device" class="meta">
        <div><dt>设备</dt><dd class="mono">{{ run.summary.device }}</dd></div>
        <div><dt>帧</dt><dd class="tnum">{{ run.summary.frame_count?.toLocaleString('zh-CN') }}<template v-if="run.summary.fps"> · {{ run.summary.fps.toFixed(1) }} fps</template></dd></div>
        <div><dt>模型</dt><dd class="mono truncate" :title="run.config_snapshot.models.fish">{{ run.config_snapshot.models.fish }}</dd></div>
        <div v-if="run.summary.processed_fps"><dt>处理速度</dt><dd class="tnum">{{ run.summary.processed_fps.toFixed(1) }} 帧/秒</dd></div>
      </dl>

      <form v-if="createOpen || (!runs.length && !busy)" id="create-run" class="create" @submit.prevent="createRun">
        <div class="field">
          <span>注册模型</span>
          <UiSelect v-model="modelId" :options="modelOptions" :disabled="busy" placeholder="选择模型" aria-label="注册模型" />
        </div>
        <p v-if="!models.length && !busy" class="note">还没有注册模型。在后端运行 register_fish_model 注册授权权重后刷新。</p>
        <div class="pair">
          <label class="field"><span>置信度阈值</span><input class="input" v-model.number="confidence" type="number" min="0.01" max="1" step="0.01" required /></label>
          <div class="field"><span>镜头</span><UiSelect v-model="motion" :options="motionOptions" aria-label="镜头运动" /></div>
        </div>
        <button class="btn btn-primary btn-block" :disabled="busy || !modelId">{{ busy ? '正在提交…' : '开始分析' }}</button>
        <p class="note">由独立 Worker 执行，优先使用 GPU；没有 CUDA 时使用 CPU，并记录实际设备。</p>
      </form>
    </section>

    <UiTabs v-model="tab" :items="tabItems" aria-label="分析视图" class="tabs">
      <template #layers>
        <div class="pane">
          <div class="layer">
            <UiSwitch id="layer-boxes" v-model="layers.boxes" />
            <label for="layer-boxes"><strong>检测框与 ID</strong><span class="note">颜色区分轨迹 ID；虚线框表示沿用上一观测</span></label>
          </div>
          <div class="layer">
            <UiSwitch id="layer-tails" v-model="layers.tails" />
            <label for="layer-tails"><strong>观测尾迹</strong><span class="note">越旧越淡；超过允许间隔即断开</span></label>
          </div>
          <UiSegmented v-if="layers.tails" class="layer-extra" v-model="layers.tailSeconds" :options="tailOptions" aria-label="尾迹时长" />
          <div class="layer">
            <UiSwitch id="layer-full" v-model="layers.fullTracks" />
            <label for="layer-full"><strong>全程轨迹</strong><span class="note">显示统计窗口内的全部轨迹</span></label>
          </div>
          <div class="layer">
            <UiSwitch id="layer-heat" v-model="layers.heatmap" />
            <label for="layer-heat"><strong>停留热图</strong><span class="note">画面相对占据度，非海底地理坐标</span></label>
          </div>
          <div v-if="layers.heatmap" class="layer-extra heat-extra">
            <div class="ramp" aria-hidden="true" />
            <div class="ramp-scale tnum"><span>0</span><span>峰值 {{ heatPeak }}</span></div>
            <div class="field"><span>不透明度 · <span class="tnum">{{ Math.round(layers.opacity * 100) }}%</span></span><UiSlider v-model="layers.opacity" :min="0.1" :max="1" :step="0.05" aria-label="热图不透明度" /></div>
          </div>
          <p v-if="trackLoading" class="note" role="status">正在加载播放窗口的轨迹…</p>
          <p v-if="trackWarning" class="note warn-text">{{ trackWarning }}</p>

          <div class="block">
            <div class="block-head"><h3>播放窗口内的轨迹</h3><span class="note tnum">{{ visibleTracks.length }}</span></div>
            <p v-if="!visibleTracks.length" class="note">{{ run?.status === 'completed' ? '这一段没有追踪观测。拖动进度条或在时间线上点选。' : '分析完成后显示。' }}</p>
            <div v-else class="chips">
              <button v-for="point in visibleTracks" :key="point.track_id" class="chip" @click="emit('seek', point.timestamp_ms / 1000)" :aria-label="`跳到 ${point.track_id} 号轨迹的 ${(point.timestamp_ms / 1000).toFixed(1)} 秒`">
                <span class="swatch" :style="{ background: trackColor(point.track_id) }" />#{{ point.track_id }}<span class="tnum faint">{{ (point.timestamp_ms / 1000).toFixed(1) }} s</span>
              </button>
            </div>
          </div>
        </div>
      </template>

      <template #stats>
        <div class="pane">
          <form class="filters" @submit.prevent="applyFilters">
            <div class="pair">
              <label class="field"><span>起点（秒）</span>
                <span class="with-action"><input class="input" v-model.number="filterStart" type="number" min="0" step="0.1" required /><UiTooltip text="设为当前时刻"><button type="button" class="btn btn-ghost btn-sm btn-icon" aria-label="起点设为当前时刻" @click="filterStart = Number(currentTime.toFixed(1))"><IconFocus2 /></button></UiTooltip></span>
              </label>
              <label class="field"><span>终点（秒）</span>
                <span class="with-action"><input class="input" v-model="filterEnd" type="number" min="0" step="0.1" placeholder="片尾" /><UiTooltip text="设为当前时刻"><button type="button" class="btn btn-ghost btn-sm btn-icon" aria-label="终点设为当前时刻" @click="filterEnd = Number(currentTime.toFixed(1))"><IconFocus2 /></button></UiTooltip></span>
              </label>
            </div>
            <div class="pair">
              <div class="field"><span>类别</span><UiSelect v-model="classId" :options="classOptions" aria-label="类别" /></div>
              <label class="field"><span>轨迹 ID</span><input class="input" v-model="trackId" type="number" min="0" step="1" placeholder="全部" /></label>
            </div>
            <div class="field">
              <span>画面 ROI</span>
              <UiSegmented v-model="roiPreset" :options="roiOptions" block aria-label="画面 ROI" />
            </div>
            <template v-if="roiPreset === 'custom'">
              <label class="field"><span>顶点（归一化坐标 JSON）</span><textarea class="input" v-model="roiText" rows="2" placeholder="[[0.1,0.2],[0.8,0.2],[0.5,0.9]]" /></label>
              <div class="row">
                <button type="button" class="btn btn-sm" :class="{ 'is-on': layers.roiEditing }" :aria-pressed="layers.roiEditing" @click="startRoi"><IconPointer />{{ layers.roiEditing ? '点选中，再按一次结束' : '在画面上点选' }}</button>
                <button type="button" class="btn btn-ghost btn-sm" @click="clearRoi">清空顶点</button>
                <span class="note tnum">{{ roiCount }} 个顶点</span>
              </div>
            </template>
            <button class="btn btn-primary btn-block" :disabled="run?.status !== 'completed' || statsLoading">{{ statsLoading ? '正在计算…' : dirty ? '应用筛选' : '重新计算' }}</button>
            <p class="note">窗口左闭右开。ROI 只筛选热图与统计，画面上的框和尾迹保持完整。</p>
          </form>

          <p v-if="summary" class="applied"><span class="eyebrow">已应用</span><span class="tnum">{{ appliedText }}</span></p>

          <div v-if="summary" class="kpis">
            <div v-for="(meta, key) in primaryMetrics" :key="key" class="kpi" :title="summary.metrics[key]?.denominator">
              <span class="eyebrow">{{ meta.title }}</span>
              <strong class="tnum">{{ metricValue(summary.metrics[key], meta.digits) ?? 'N/A' }}</strong>
              <span class="note">{{ meta.unit }}</span>
            </div>
          </div>
          <p v-else class="note pad">{{ run?.status === 'completed' ? '正在读取统计…' : '分析完成后，这里显示同源统计。缺失的数据不会补成 0。' }}</p>

          <div v-if="summary" class="block">
            <div class="block-head"><h3>需要真值的指标</h3></div>
            <dl class="na-list">
              <div v-for="(title, key) in truthMetrics" :key="key"><dt>{{ title }}</dt><dd><span class="tag">N/A</span><span class="note">{{ MISSING_REASONS[summary.metrics[key]?.reason] || summary.metrics[key]?.reason }}</span></dd></div>
            </dl>
          </div>

          <div v-if="classRows.length" class="block">
            <div class="block-head"><h3>类别观测次数</h3></div>
            <div v-for="row in classRows" :key="row.id" class="bar-row">
              <span class="truncate">{{ row.label }}</span>
              <span class="bar"><span :style="{ width: `${row.share * 100}%` }" /></span>
              <span class="tnum">{{ row.count.toLocaleString('zh-CN') }}</span>
            </div>
          </div>

          <div v-if="!wall && (heatmap || overview)" class="block figures">
            <HeatmapFigure v-if="heatmap" :heatmap="heatmap" :roi="applied.roi" :aspect="aspect" compact />
            <TrajectoryFigure v-if="overview" :spans="overview.spans" :window="applied" :roi="applied.roi" :aspect="aspect" :truncated="overview.truncated" compact />
          </div>

          <div class="block">
            <div class="block-head"><h3>导出</h3></div>
            <div class="exports">
              <button class="btn btn-sm" @click="download('summary', 'json')" :disabled="!summary"><IconDownload />统计 JSON</button>
              <button class="btn btn-sm" @click="download('heatmap', 'csv')" :disabled="!summary"><IconDownload />热图 CSV</button>
              <button class="btn btn-sm" @click="download('heatmap', 'json')" :disabled="!summary"><IconDownload />热图 JSON</button>
              <UiTooltip text="只包含当前播放缓存的观测"><button class="btn btn-sm" @click="exportTracks" :disabled="!tracks.length || !!trackWarning || trackLoading"><IconDownload />播放窗口 JSONL</button></UiTooltip>
            </div>
            <p class="note">导出沿用已应用的窗口与筛选，并附带来源元数据。</p>
            <p v-if="message" class="note" role="status">{{ message }}</p>
          </div>
        </div>
      </template>

      <template #source>
        <div class="pane">
          <dl v-if="run" class="provenance">
            <div><dt>分析 ID</dt><dd><span class="mono">{{ run.run_id }}</span><UiTooltip text="复制"><button class="btn btn-ghost btn-sm btn-icon" aria-label="复制分析 ID" @click="copy(run.run_id)"><IconCopy /></button></UiTooltip></dd></div>
            <div><dt>模型</dt><dd class="mono">{{ run.config_snapshot.models.fish }}</dd></div>
            <div><dt>权重 SHA256</dt><dd><span class="mono hash">{{ run.config_snapshot.model_sha256 }}</span><UiTooltip text="复制"><button class="btn btn-ghost btn-sm btn-icon" aria-label="复制权重哈希" @click="copy(run.config_snapshot.model_sha256)"><IconCopy /></button></UiTooltip></dd></div>
            <div><dt>置信度 / IoU 阈值</dt><dd class="tnum">{{ run.config_snapshot.settings.confidence_threshold }} / {{ run.config_snapshot.settings.iou_threshold }}</dd></div>
            <div><dt>允许观测间隔</dt><dd class="tnum">{{ run.config_snapshot.settings.allowed_gap_seconds }} s</dd></div>
            <div><dt>镜头运动</dt><dd>{{ motions[run.config_snapshot.settings.camera_motion] || run.config_snapshot.settings.camera_motion }}</dd></div>
            <div><dt>热图算法</dt><dd class="mono">{{ summary?.heatmap?.algorithm_version || '等待计算' }}</dd></div>
            <div v-if="run.summary?.timestamp_fallback_frames"><dt>按帧号推算时间</dt><dd class="tnum">{{ run.summary.timestamp_fallback_frames }} 帧</dd></div>
          </dl>
          <p v-else class="note">选择一次分析后显示来源。</p>
          <div class="block">
            <div class="block-head"><h3>解读限制</h3></div>
            <ul class="limits">
              <li>轨迹 ID 只在本次分析内有效；遮挡后重新出现会计为新 ID，不等于鱼类个体数。</li>
              <li>平均置信度是模型输出的描述统计，不是准确率。</li>
              <li>没有独立测试真值时，AP50、IDF1 与珊瑚覆盖率保持 N/A。</li>
              <li v-for="item in summary?.limitations || []" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </template>
    </UiTabs>
  </aside>
</template>

<script setup>
import { ref, reactive, computed, watch, onBeforeUnmount, shallowRef, markRaw } from 'vue'
import { listAnalysisModels, listAnalysisRuns, createAnalysisRun, getAnalysisRun, retryAnalysisRun, getAnalysisTracks, getAnalysisHeatmap, getAnalysisSummary, downloadAnalysis } from '../api'
import { IconClock, IconRefresh, IconAlertTriangle, IconPlus, IconDownload, IconCopy, IconFocus2, IconPointer } from '@tabler/icons-vue'
import UiSelect from './ui/UiSelect.vue'
import UiSwitch from './ui/UiSwitch.vue'
import UiSlider from './ui/UiSlider.vue'
import UiSegmented from './ui/UiSegmented.vue'
import UiTabs from './ui/UiTabs.vue'
import UiTooltip from './ui/UiTooltip.vue'
import HeatmapFigure from './HeatmapFigure.vue'
import TrajectoryFigure from './TrajectoryFigure.vue'
import { trackColor } from '../lib/palette'
import { trackSpans, observationsPerFrame } from '../lib/tracks'
import { metricValue, MISSING_REASONS, formatDateTime } from '../lib/format'

const props = defineProps({ taskId: Number, currentTime: { type: Number, default: 0 }, fileName: String, wall: Boolean })
const emit = defineEmits(['analysis', 'seek', 'toast'])

const TRACK_BUDGET = 20000
const models = ref([]), runs = ref([]), modelId = ref(''), selectedId = ref(''), run = ref(null)
const tracks = shallowRef([]), heatmap = shallowRef(null), summary = shallowRef(null), overview = shallowRef(null)
const busy = ref(false), error = ref(''), message = ref(''), statsLoading = ref(false), trackLoading = ref(false), trackWarning = ref('')
const confidence = ref(0.25), motion = ref('unknown'), filterStart = ref(0), filterEnd = ref(''), classId = ref(''), trackId = ref(''), roiPreset = ref('all'), roiText = ref('[]')
const layers = reactive({ boxes: true, tails: true, heatmap: false, opacity: 0.6, tailSeconds: 10, roiEditing: false, fullTracks: false })
const applied = ref({ start_ms: 0 })
const createOpen = ref(false), tab = ref('layers')

const states = { queued: '排队中', running: '分析中', completed: '已完成', failed: '失败' }
const motions = { unknown: '未知', fixed: '固定', moving: '移动' }
const roiPresets = { all: '全画面', left: '左半', center: '中央', custom: '自定义' }
const primaryMetrics = {
  observed_track_count: { title: '观测 ID 数', unit: '个 ID，非个体数', digits: 0 },
  tracked_observation_count: { title: '追踪观测次数', unit: '次（同帧同 ID 去重）', digits: 0 },
  track_seconds: { title: '累计停留', unit: 'track-s', digits: 1 },
  mean_confidence: { title: '平均置信度', unit: '模型输出，非准确率', digits: 3 }
}
const tailOptions = [5, 10, 30].map(value => ({ value, label: `${value} 秒` }))
const motionOptions = Object.entries(motions).map(([value, label]) => ({ value, label }))
const roiOptions = Object.entries(roiPresets).map(([value, label]) => ({ value, label }))
const truthMetrics = { ap50: '独立测试 AP50', idf1: '人工真值 IDF1', coral_cover: '珊瑚覆盖率' }

const tabItems = computed(() => [{ value: 'layers', label: '图层' }, { value: 'stats', label: '统计' }, { value: 'source', label: '来源' }])
const runOptions = computed(() => runs.value.map((item, index) => ({ value: item.run_id, label: `第 ${runs.value.length - index} 次 · ${states[item.status] || item.status}`, hint: formatDateTime(item.created_at) })))
const modelOptions = computed(() => models.value.map(model => ({ value: model.id, label: model.id })))
const classOptions = computed(() => [{ value: '', label: '全部类别' }, ...Object.entries(selectedModel.value?.labels || {}).map(([value, label]) => ({ value, label }))])
const visibleTracks = computed(() => [...new Map(tracks.value.map(p => [p.track_id, p])).values()].slice(0, 24))
const pendingNewer = computed(() => {
  const index = runs.value.findIndex(r => r.run_id === selectedId.value)
  return index > 0 ? runs.value.slice(0, index).filter(r => r.status === 'queued' || r.status === 'running').length : 0
})
const demo = computed(() => /synthetic|合成|DEMO/i.test(props.fileName || ''))
const selectedModel = computed(() => models.value.find(m => m.id === (run.value?.config_snapshot.models.fish || modelId.value)))
const aspect = computed(() => run.value?.summary?.width && run.value?.summary?.height ? run.value.summary.width / run.value.summary.height : 16 / 9)
const heatPeak = computed(() => {
  const peak = heatmap.value ? Math.max(0, ...heatmap.value.values_raw.flat()) : 0
  return `${peak.toFixed(2)} track-s`
})
const roiCount = computed(() => { try { const v = JSON.parse(roiText.value); return Array.isArray(v) ? v.length : 0 } catch { return 0 } })
const classRows = computed(() => {
  const counts = summary.value?.class_observation_counts || {}
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  return Object.entries(counts).map(([id, count]) => ({ id, count, label: selectedModel.value?.labels?.[id] ?? `类别 ${id}`, share: total ? count / total : 0 })).sort((a, b) => b.count - a.count)
})
const appliedText = computed(() => {
  const a = applied.value
  const range = `${(a.start_ms / 1000).toFixed(1)}–${a.end_ms == null ? '片尾' : `${(a.end_ms / 1000).toFixed(1)} s`}`
  const label = a.class_id != null ? (selectedModel.value?.labels?.[a.class_id] ?? `类别 ${a.class_id}`) : '全部类别'
  const id = a.track_id != null ? `ID #${a.track_id}` : '全部 ID'
  const roi = a.roi ? `ROI ${a.roi.length} 点` : '全画面'
  return [range, label, id, roi].join(' · ')
})
const dirty = computed(() => {
  const next = draftParams()
  return !next || JSON.stringify(next) !== JSON.stringify(applied.value)
})

let generation = 0, pollTimer, bootAbort, pollAbort, statsAbort, trackAbort, overviewAbort, disposed = false
function cancelled(e) { return e?.code === 'ERR_CANCELED' || e?.name === 'AbortError' }

function errorText(code) {
  const messages = {
    invalid_settings: '参数无效。检查阈值与图像尺寸后重试。', unknown_model: '找不到该模型。刷新模型列表后重试。',
    retry_not_allowed: '这次分析当前不能重试，或已用完 3 次机会。', worker_lease_expired: 'Worker 心跳超时。确认 Worker 已恢复后重试。',
    model_hash_mismatch: '权重与注册哈希不一致。请把新权重注册为新的模型版本。', invalid_video: '无法读取源视频。检查本地文件与权限。',
    video_decode_failed: '视频解码失败。检查 MP4 文件是否完整。', video_incomplete: '视频提前结束。检查源文件是否完整。',
    video_time_reversed: '视频时间戳倒退，已停止分析以保护轨迹时间。', video_time_unavailable: '缺少可靠的时间戳与帧率，无法生成轨迹。',
    analysis_failed: '分析失败。查看本地 Worker 的运行状态。', invalid_artifacts: '产物校验失败，未发布不完整的结果。'
  }
  return messages[code] || code || '分析失败。'
}
function problem(e) {
  if (e?.response?.data?.error?.code) return errorText(e.response.data.error.code)
  return e?.response ? `请求失败（HTTP ${e.response.status}）。刷新后重试。` : '无法连接本地后端。确认服务已启动后重新连接。'
}

function runOrdinal() {
  const index = runs.value.findIndex(item => item.run_id === run.value?.run_id)
  return index < 0 ? null : runs.value.length - index
}
function publish() {
  emit('analysis', markRaw({
    runId: run.value?.run_id, run: run.value, ordinal: runOrdinal(), summary: summary.value, tracks: tracks.value, heatmap: heatmap.value,
    overview: overview.value, layers: { ...layers }, roi: applied.value.roi || null, roiDraft: layers.roiEditing ? roiDraft() : null, window: { ...applied.value },
    labels: selectedModel.value?.labels || {}, aspect: aspect.value,
    allowedGap: run.value?.config_snapshot.settings.allowed_gap_seconds || 0.5, fps: run.value?.summary?.fps || 30,
    duration: run.value?.summary?.frame_count && run.value?.summary?.fps ? run.value.summary.frame_count / run.value.summary.fps : null
  }))
}
watch(layers, publish, { deep: true })
watch(roiText, () => { if (layers.roiEditing) publish() })
function roiDraft() { try { const v = JSON.parse(roiText.value); return Array.isArray(v) ? v.filter(p => Array.isArray(p) && p.length === 2) : [] } catch { return [] } }

async function boot() {
  const version = ++generation
  clearTimeout(pollTimer)
  for (const c of [bootAbort, pollAbort, statsAbort, trackAbort, overviewAbort]) c?.abort()
  bootAbort = new AbortController()
  run.value = null; selectedId.value = ''; tracks.value = []; heatmap.value = null; summary.value = null; overview.value = null; runs.value = []; error.value = ''; busy.value = true
  publish()
  try {
    const [m, r] = await Promise.all([listAnalysisModels(bootAbort.signal), listAnalysisRuns(props.taskId, bootAbort.signal)])
    if (version !== generation || disposed) return
    models.value = m.data.items; runs.value = r.data.items
    modelId.value = models.value[0]?.id || ''
    selectedId.value = (runs.value.find(r => r.status === 'completed') || runs.value[0])?.run_id || ''
  } catch (e) {
    if (!cancelled(e) && version === generation) error.value = problem(e)
  } finally {
    if (version === generation) busy.value = false
  }
}
watch(() => props.taskId, boot, { immediate: true })

watch(selectedId, async id => {
  if (!id) return
  const version = ++generation
  clearTimeout(pollTimer)
  for (const c of [pollAbort, statsAbort, trackAbort, overviewAbort]) c?.abort()
  applied.value = { start_ms: 0 }; filterStart.value = 0; filterEnd.value = ''; classId.value = ''; trackId.value = ''; roiPreset.value = 'all'; layers.roiEditing = false
  run.value = runs.value.find(r => r.run_id === id) || null
  tracks.value = []; heatmap.value = null; summary.value = null; overview.value = null; trackWarning.value = ''
  publish()
  if (disposed) return
  await poll(version)
})

async function poll(version) {
  if (version !== generation || disposed) return
  pollAbort = new AbortController()
  try {
    const response = await getAnalysisRun(selectedId.value, pollAbort.signal)
    if (version !== generation || disposed) return
    run.value = response.data; error.value = ''
    runs.value = runs.value.map(r => r.run_id === run.value.run_id ? run.value : r)
    publish()
    if (run.value.status === 'completed') { await Promise.all([loadStats(), loadTracks(), loadOverview()]); return }
    if (run.value.status === 'failed') return
  } catch (e) {
    if (!cancelled(e) && version === generation) error.value = problem(e)
  }
  if (version === generation && !disposed) pollTimer = setTimeout(() => poll(version), 1500)
}

async function createRun() {
  if (busy.value) return
  busy.value = true; error.value = ''
  const task = props.taskId
  try {
    const response = await createAnalysisRun(task, { kind: 'fish', models: { fish: modelId.value }, settings: { confidence_threshold: confidence.value, camera_motion: motion.value } })
    if (task !== props.taskId || disposed) return
    runs.value = [response.data, ...runs.value]; selectedId.value = response.data.run_id; createOpen.value = false
    emit('toast', { title: '分析已排队', desc: '旧的分析结果会保留，可在分析记录中切换。' })
  } catch (e) {
    error.value = problem(e)
  } finally {
    busy.value = false
  }
}

async function retryRun() {
  if (busy.value) return
  busy.value = true
  const id = selectedId.value
  try {
    const response = await retryAnalysisRun(id)
    if (id !== selectedId.value || disposed) return
    run.value = response.data
    poll(generation)
  } catch (e) {
    error.value = problem(e)
  } finally {
    busy.value = false
  }
}

function draftParams() {
  const params = { start_ms: Number(filterStart.value) * 1000 }
  if (filterEnd.value !== '' && filterEnd.value != null) params.end_ms = Number(filterEnd.value) * 1000
  if (!Number.isFinite(params.start_ms) || params.start_ms < 0 || ('end_ms' in params && (!Number.isFinite(params.end_ms) || params.end_ms <= params.start_ms))) return null
  for (const [key, value] of [['class_id', classId.value], ['track_id', trackId.value]]) {
    if (value === '' || value == null) continue
    if (!Number.isInteger(Number(value)) || Number(value) < 0) return null
    params[key] = Number(value)
  }
  let roi = null
  if (roiPreset.value === 'left') roi = [[0, 0], [0.5, 0], [0.5, 1], [0, 1]]
  if (roiPreset.value === 'center') roi = [[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75]]
  if (roiPreset.value === 'custom') {
    try {
      roi = JSON.parse(roiText.value)
      if (!Array.isArray(roi) || roi.length < 3 || roi.length > 64 || roi.some(p => !Array.isArray(p) || p.length !== 2 || p.some(v => typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > 1))) return null
    } catch { return null }
  }
  if (roi) params.roi = roi
  return params
}

function applyFilters() {
  const params = draftParams()
  if (!params) {
    const end = filterEnd.value === '' ? null : Number(filterEnd.value)
    if (end != null && end <= Number(filterStart.value)) error.value = '终点要大于起点。'
    else if (roiPreset.value === 'custom') error.value = 'ROI 需要 3–64 个顶点，坐标在 0 到 1 之间。'
    else error.value = '时间用非负数，ID 用非负整数。'
    return
  }
  layers.roiEditing = false; applied.value = params; error.value = ''
  loadStats(); loadTracks()
}

function queryParams() { return { ...applied.value, ...(applied.value.roi ? { roi: JSON.stringify(applied.value.roi) } : {}) } }

async function loadStats() {
  if (run.value?.status !== 'completed') return
  statsAbort?.abort()
  const controller = new AbortController(); statsAbort = controller
  const id = selectedId.value
  statsLoading.value = true; summary.value = null; heatmap.value = null; publish()
  try {
    const [h, s] = await Promise.all([getAnalysisHeatmap(id, queryParams(), controller.signal), getAnalysisSummary(id, queryParams(), controller.signal)])
    if (controller.signal.aborted || id !== selectedId.value || disposed) return
    heatmap.value = markRaw(h.data); summary.value = markRaw(s.data); error.value = ''
    publish()
  } catch (e) {
    if (!cancelled(e)) error.value = problem(e)
  } finally {
    if (statsAbort === controller) statsLoading.value = false
  }
}

async function fetchAll(id, params, signal) {
  let cursor = null
  const result = []
  do {
    const response = await getAnalysisTracks(id, { ...params, ...(cursor ? { cursor } : {}) }, signal)
    if (signal.aborted || id !== selectedId.value || disposed) return null
    result.push(...response.data.items)
    cursor = response.data.next_cursor
  } while (cursor && result.length < TRACK_BUDGET)
  return { items: result, truncated: Boolean(cursor) }
}

async function loadTracks() {
  if (run.value?.status !== 'completed') return
  trackAbort?.abort()
  const controller = new AbortController(); trackAbort = controller
  const id = selectedId.value
  const start = Math.max(applied.value.start_ms, layers.fullTracks ? 0 : Math.floor(props.currentTime / 4) * 4000 - layers.tailSeconds * 1000)
  const end = Math.min(applied.value.end_ms ?? Infinity, layers.fullTracks ? Infinity : Math.floor(props.currentTime / 4) * 4000 + 4500)
  trackWarning.value = ''; trackLoading.value = true
  if (end <= start) { tracks.value = []; trackLoading.value = false; publish(); return }
  const params = { start_ms: start, limit: 2000 }
  if (Number.isFinite(end)) params.end_ms = end
  for (const key of ['class_id', 'track_id']) if (key in applied.value) params[key] = applied.value[key]
  try {
    const result = await fetchAll(id, params, controller.signal)
    if (!result) return
    if (result.truncated) trackWarning.value = `这一段超过 ${TRACK_BUDGET.toLocaleString('zh-CN')} 条观测。缩短尾迹或按类别筛选；播放窗口导出已停用。`
    tracks.value = markRaw(result.items); publish()
  } catch (e) {
    if (!cancelled(e)) { trackWarning.value = problem(e); tracks.value = []; publish() }
  } finally {
    if (trackAbort === controller) trackLoading.value = false
  }
}

// Whole-run observations for the timeline and trajectory figures; display only, same budget as playback.
async function loadOverview() {
  if (run.value?.status !== 'completed') return
  overviewAbort?.abort()
  const controller = new AbortController(); overviewAbort = controller
  const id = selectedId.value
  try {
    const result = await fetchAll(id, { start_ms: 0, limit: 2000 }, controller.signal)
    if (!result) return
    const gap = run.value.config_snapshot.settings.allowed_gap_seconds || 0.5
    overview.value = markRaw({ spans: trackSpans(result.items, gap), frames: observationsPerFrame(result.items), truncated: result.truncated, count: result.items.length })
    publish()
  } catch (e) {
    if (!cancelled(e)) overview.value = null
  }
}

watch([() => layers.fullTracks ? -1 : Math.floor(props.currentTime / 4), () => layers.tailSeconds, () => layers.fullTracks], loadTracks)

function startRoi() { roiPreset.value = 'custom'; layers.roiEditing = !layers.roiEditing; if (layers.roiEditing) message.value = '' }
function clearRoi() { roiText.value = '[]' }
function addRoiPoint(point) {
  if (!layers.roiEditing) return
  let points = []
  try { points = JSON.parse(roiText.value) } catch { /* reset malformed draft */ }
  if (!Array.isArray(points)) points = []
  if (points.length < 64) { points.push(point); roiText.value = JSON.stringify(points) }
}
function setLayer(key, value) { if (key in layers) layers[key] = value }
defineExpose({ addRoiPoint, refresh: boot, setLayer })

function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob), a = document.createElement('a')
  a.href = url; a.download = name; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
async function download(resource, format) {
  try {
    const response = await downloadAnalysis(selectedId.value, resource, { ...queryParams(), export: format })
    saveBlob(response.data, `${resource === 'summary' ? 'analysis_report' : 'heatmap'}.${format}`)
    message.value = '已导出。文件包含当前窗口、筛选与来源元数据。'
  } catch {
    error.value = '导出失败。刷新后重试。'
  }
}
function exportTracks() {
  saveBlob(new Blob([tracks.value.map(p => JSON.stringify(p)).join('\n') + '\n'], { type: 'application/x-ndjson' }), 'playback-window-tracks.jsonl')
  message.value = '已导出当前播放缓存内的真实观测，不含全片轨迹。'
}
async function copy(text) {
  try { await navigator.clipboard.writeText(text); emit('toast', { title: '已复制', desc: text.slice(0, 24) + (text.length > 24 ? '…' : '') }) }
  catch { emit('toast', { title: '无法访问剪贴板', desc: '手动选中文本复制。', type: 'alert' }) }
}

onBeforeUnmount(() => {
  disposed = true; generation++
  clearTimeout(pollTimer)
  for (const c of [bootAbort, pollAbort, statsAbort, trackAbort, overviewAbort]) c?.abort()
})
</script>

<style scoped>
.inspector { height: 100%; overflow-y: auto; overflow-x: hidden; background: var(--surface); display: flex; flex-direction: column; }
.head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 16px 10px; }
h2 { font-size: var(--text-title); font-weight: 600; }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.min-w-0 { min-width: 0; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.banner { display: flex; gap: 8px; align-items: flex-start; margin: 0 16px 10px; padding: 8px 10px; border-radius: var(--radius); font-size: var(--text-small); line-height: 1.5; }
.banner .tabler-icon { --icon-size: 14px; margin-top: 2px; }
.banner.warn { color: var(--warn); background: var(--warn-soft); }
.banner.danger { color: var(--danger); background: var(--danger-soft); }
.link { margin-inline-start: auto; border: 0; background: none; font: inherit; color: inherit; text-decoration: underline; text-underline-offset: 2px; cursor: pointer; white-space: nowrap; }
.run { display: flex; flex-direction: column; gap: 10px; padding: 4px 16px 14px; }
.run-row { display: flex; align-items: flex-end; gap: 8px; }
.grow { flex: 1; }
.pending { display: flex; gap: 6px; align-items: flex-start; }
.pending .tabler-icon { --icon-size: 14px; margin-top: 2px; color: var(--info); }
.status { display: flex; align-items: center; justify-content: space-between; }
.state { display: inline-flex; align-items: center; gap: 6px; font-weight: 500; color: var(--ink-2); }
.state[data-state=completed] .dot { color: var(--ok); }
.state[data-state=running] .dot, .state[data-state=queued] .dot { color: var(--info); }
.state[data-state=failed] { color: var(--danger); }
.progress { height: 3px; border-radius: 2px; background: var(--surface-3); overflow: hidden; }
.progress > span { display: block; height: 100%; background: var(--info); transition: width 300ms var(--ease); }
.failed { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; color: var(--danger); font-size: var(--text-small); line-height: 1.5; }
.meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px; padding: 10px 12px; border-radius: var(--radius); background: var(--surface-2); }
.meta div { min-width: 0; }
.meta dt, .provenance dt { font-size: var(--text-caption); color: var(--ink-3); }
.meta dd { font-size: var(--text-small); }
.create { display: flex; flex-direction: column; gap: 10px; padding: 12px; border-radius: var(--radius-lg); box-shadow: inset 0 0 0 1px var(--line); }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tabs { flex: none; }
.tabs :deep(.ui-tabs-list) { position: sticky; top: 0; z-index: 2; background: var(--surface); }
.is-on { color: var(--accent); background: var(--accent-soft); box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--accent) 40%, transparent); }
.pad { padding-top: 12px; }
.figures { gap: 16px; }
.pane { display: flex; flex-direction: column; gap: 4px; padding: 12px 16px 24px; }
.layer { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; }
.layer .switch { margin-top: 2px; }
.layer label { display: flex; flex-direction: column; gap: 1px; cursor: pointer; }
.layer strong { font-weight: 500; }
.layer-extra { margin: -2px 0 6px 38px; }
.heat-extra { display: flex; flex-direction: column; gap: 4px; margin-inline-end: 0; }
.ramp { height: 8px; border-radius: 2px; background: linear-gradient(90deg, #000004, #160b39, #420a68, #6a176e, #932667, #bc3754, #dd513a, #f37819, #fca50a, #f6d746, #fcffa4); }
.ramp-scale { display: flex; justify-content: space-between; font-size: var(--text-caption); color: var(--ink-3); margin-bottom: 6px; }
.warn-text { color: var(--warn); }
.block { display: flex; flex-direction: column; gap: 8px; padding-top: 16px; }
.block-head { display: flex; align-items: baseline; justify-content: space-between; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; align-items: center; gap: 6px; height: 24px; padding: 0 8px; border: 0; border-radius: var(--radius-sm); font: inherit; font-size: var(--text-caption); color: var(--ink); background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); cursor: pointer; transition: background-color 120ms var(--ease); }
.chip:hover { background: var(--surface-3); }
.swatch { width: 8px; height: 8px; border-radius: 2px; }
.faint { color: var(--ink-3); }
.filters { display: flex; flex-direction: column; gap: 12px; }
.with-action { display: flex; gap: 4px; align-items: center; }
.row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.applied { display: flex; flex-direction: column; gap: 2px; margin-top: 14px; padding: 8px 10px; border-radius: var(--radius); background: var(--surface-2); font-size: var(--text-small); }
.kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin-top: 12px; border-radius: var(--radius-lg); overflow: hidden; background: var(--line); box-shadow: 0 0 0 1px var(--line); }
.kpi { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; background: var(--surface); min-width: 0; }
.kpi strong { font-size: var(--text-figure); font-weight: 500; line-height: 1.15; letter-spacing: -0.01em; }
.kpi .note { font-size: var(--text-caption); }
.na-list { display: flex; flex-direction: column; gap: 6px; }
.na-list div { display: grid; grid-template-columns: 96px 1fr; gap: 8px; align-items: baseline; font-size: var(--text-small); }
.na-list dt { color: var(--ink-2); }
.na-list dd { display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
.bar-row { display: grid; grid-template-columns: minmax(0, 72px) 1fr auto; gap: 10px; align-items: center; font-size: var(--text-small); }
.bar { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--ink-3); }
.exports { display: flex; flex-wrap: wrap; gap: 6px; }
.provenance { display: flex; flex-direction: column; gap: 10px; }
.provenance dd { display: flex; align-items: flex-start; gap: 4px; font-size: var(--text-small); overflow-wrap: anywhere; }
.hash { word-break: break-all; line-height: 1.5; }
.limits { display: flex; flex-direction: column; gap: 6px; padding-inline-start: 16px; list-style: disc; color: var(--ink-2); font-size: var(--text-small); line-height: 1.55; }
.limits li::marker { color: var(--ink-3); }
</style>
