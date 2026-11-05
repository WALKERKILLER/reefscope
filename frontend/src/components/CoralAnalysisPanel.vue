<template>
  <aside class="inspector" aria-label="珊瑚白化分析">
    <header class="head">
      <div class="min-w-0">
        <h2>珊瑚白化分析</h2>
        <p class="note truncate" :title="fileName">{{ fileName }}</p>
      </div>
      <UiTooltip text="刷新模型与分析记录">
        <button class="btn btn-ghost btn-icon" @click="boot" :disabled="busy" aria-label="刷新模型与分析记录"><IconRefresh /></button>
      </UiTooltip>
    </header>

    <p v-if="error" class="banner danger" role="alert"><IconAlertTriangle /><span>{{ error }}</span><button class="link" @click="boot">重新连接</button></p>

    <section class="run" aria-label="分析记录">
      <div class="run-row">
        <div class="field grow">
          <span>分析记录</span>
          <UiSelect v-model="selectedId" :options="runOptions" :disabled="!runs.length" placeholder="还没有分析" aria-label="珊瑚分析记录" />
        </div>
        <UiTooltip text="新建分析">
          <button class="btn btn-icon" :class="{ 'is-on': createOpen }" :aria-expanded="createOpen" aria-controls="create-coral-run" aria-label="新建珊瑚分析" @click="createOpen = !createOpen"><IconPlus /></button>
        </UiTooltip>
      </div>

      <div v-if="run" class="status" aria-live="polite">
        <span class="state" :data-state="run.status"><span class="dot" />{{ states[run.status] || run.status }}</span>
        <span class="note tnum">第 {{ run.attempt }}/3 次尝试</span>
      </div>
      <div v-if="run && (run.status === 'queued' || run.status === 'running')" class="progress" role="progressbar" :aria-valuenow="run.progress" aria-valuemin="0" aria-valuemax="100" aria-label="分析进度"><span :style="{ width: `${run.progress}%` }" /></div>
      <p v-if="run?.status === 'queued'" class="note">等待珊瑚 Worker 领取。可以继续播放视频。</p>
      <p v-if="run?.status === 'running'" class="note tnum">正在分割采样帧 · {{ run.progress }}%</p>
      <div v-if="run?.status === 'failed'" class="failed">
        <p>{{ errorText(run.error_code) }}</p>
        <button v-if="run.attempt < 3" class="btn btn-sm" @click="retryRun" :disabled="busy"><IconRefresh />重试分析</button>
      </div>
      <dl v-if="run?.summary?.device" class="meta">
        <div><dt>设备 · 精度</dt><dd class="mono">{{ run.summary.device }} · {{ run.summary.precision }}</dd></div>
        <div><dt>采样帧</dt><dd class="tnum">{{ run.summary.sampled_frames }} · 每 {{ run.summary.sample_every_seconds }} s</dd></div>
        <div><dt>模型</dt><dd class="mono truncate" :title="run.config_snapshot.models.coral">{{ run.config_snapshot.models.coral }}</dd></div>
        <div><dt>每帧耗时</dt><dd class="tnum">{{ run.summary.seconds_per_sample?.toFixed(2) }} s</dd></div>
      </dl>

      <form v-if="createOpen || (!runs.length && !busy)" id="create-coral-run" class="create" @submit.prevent="createRun">
        <div class="field">
          <span>注册模型</span>
          <UiSelect v-model="modelId" :options="modelOptions" :disabled="busy" placeholder="选择模型" aria-label="珊瑚注册模型" />
        </div>
        <p v-if="!models.length && !busy" class="note">还没有注册珊瑚模型。在后端运行 register_coral_model 注册交付权重后刷新。</p>
        <div class="pair">
          <label class="field"><span>采样间隔（秒）</span><input class="input" v-model.number="interval" type="number" min="0.5" max="60" step="0.5" required /></label>
          <div class="field"><span>镜头</span><UiSelect v-model="motion" :options="motionOptions" aria-label="镜头运动" /></div>
        </div>
        <p v-if="estimate" class="note tnum">约 {{ estimate.samples }} 个采样帧{{ estimate.seconds ? ` · GPU 上约 ${estimate.seconds}` : '' }}</p>
        <button class="btn btn-primary btn-block" :disabled="busy || !modelId">{{ busy ? '正在提交…' : '开始分析' }}</button>
        <p class="note">每隔固定时间取一帧，由珊瑚 Worker 逐帧分割为背景、未白化、白化三类。优先使用 GPU 与 BF16，实际设备和精度会记录在结果里。</p>
      </form>
    </section>

    <UiTabs v-model="tab" :items="tabItems" aria-label="珊瑚分析视图" class="tabs">
      <template #layers>
        <div class="pane">
          <div class="layer">
            <UiSwitch id="coral-mask" v-model="layers.mask" :disabled="!frames.length" />
            <label for="coral-mask"><strong>珊瑚掩膜</strong><span class="note">播放头之前最近的采样帧，最多沿用一个采样间隔</span></label>
          </div>
          <div v-if="layers.mask" class="layer-extra display">
            <div class="field"><span>显示方式</span><UiSegmented v-model="layers.mode" :options="modeOptions" block aria-label="掩膜显示方式" /></div>
            <div class="field">
              <span>类别 · 当前采样帧占比</span>
              <div class="class-chips" role="group" aria-label="掩膜类别">
                <button v-for="chip in classChips" :key="chip.id" type="button" class="class-chip" :aria-pressed="layers[chip.key]" :title="layers[chip.key] ? `隐藏${chip.label}` : `显示${chip.label}`" @click="layers[chip.key] = !layers[chip.key]">
                  <span class="chip-swatch" :style="chip.swatch" /><span>{{ chip.label }}</span><span class="tnum chip-share">{{ chip.share }}</span>
                </button>
              </div>
              <p v-if="current && !current.background_separated" class="note warn-text">本帧未分离背景，未白化不绘制。</p>
            </div>
            <div v-if="layers.mode !== 'outline'" class="field"><span>填充不透明度 · <span class="tnum">{{ Math.round(layers.opacity * 100) }}%</span></span><UiSlider v-model="layers.opacity" :min="0.1" :max="1" :step="0.05" aria-label="掩膜填充不透明度" /></div>
            <div class="layer">
              <UiSwitch id="coral-compare" v-model="layers.compare" />
              <label for="coral-compare"><strong>对比原画面</strong><span class="note">拖动画面上的分隔线，左侧为掩膜，右侧为原画面</span></label>
            </div>
          </div>
          <p v-if="maskWarning" class="note warn-text">{{ maskWarning }}</p>

          <div class="block">
            <div class="block-head"><h3>当前采样帧</h3><span v-if="frames.length" class="note tnum">{{ currentIndex + 1 }} / {{ frames.length }}</span></div>
            <template v-if="current">
              <dl class="frame-facts">
                <div><dt>时间</dt><dd class="tnum">{{ (current.timestamp_ms / 1000).toFixed(2) }} s · 帧 {{ current.frame + 1 }}</dd></div>
                <div><dt>背景分离</dt><dd :class="{ 'warn-text': !current.background_separated }">{{ current.background_separated ? '已分离' : '未分离，背景计入未白化' }}</dd></div>
              </dl>
              <div class="composition" role="img" :aria-label="compositionText">
                <span v-for="part in composition.filter(item => item.share > 0)" :key="part.label" :class="part.kind" :style="{ flexGrow: part.share, background: part.color }" />
              </div>
              <p class="note tnum composition-key">{{ compositionText }}</p>
              <div class="row">
                <button class="btn btn-sm" :disabled="currentIndex <= 0" @click="step(-1)"><IconChevronLeft />上一采样帧</button>
                <button class="btn btn-sm" :disabled="currentIndex >= frames.length - 1" @click="step(1)">下一采样帧<IconChevronRight /></button>
              </div>
            </template>
            <p v-else class="note">{{ run?.status === 'completed' ? (frames.length ? '播放到第一个采样帧后显示。' : '正在读取采样帧…') : '分析完成后显示。' }}</p>
          </div>
        </div>
      </template>

      <template #stats>
        <div class="pane">
          <form class="filters" @submit.prevent="applyWindow">
            <div class="pair">
              <label class="field"><span>起点（秒）</span>
                <span class="with-action"><input class="input" v-model.number="filterStart" type="number" min="0" step="0.1" required /><UiTooltip text="设为当前时刻"><button type="button" class="btn btn-ghost btn-sm btn-icon" aria-label="起点设为当前时刻" @click="filterStart = Number(currentTime.toFixed(1))"><IconFocus2 /></button></UiTooltip></span>
              </label>
              <label class="field"><span>终点（秒）</span>
                <span class="with-action"><input class="input" v-model="filterEnd" type="number" min="0" step="0.1" placeholder="片尾" /><UiTooltip text="设为当前时刻"><button type="button" class="btn btn-ghost btn-sm btn-icon" aria-label="终点设为当前时刻" @click="filterEnd = Number(currentTime.toFixed(1))"><IconFocus2 /></button></UiTooltip></span>
              </label>
            </div>
            <button class="btn btn-primary btn-block" :disabled="run?.status !== 'completed' || statsLoading">{{ statsLoading ? '正在计算…' : dirty ? '应用窗口' : '重新计算' }}</button>
            <p class="note">窗口左闭右开，按采样帧时间筛选。</p>
          </form>

          <p v-if="summary" class="applied"><span class="eyebrow">已应用</span><span class="tnum">{{ appliedText }}</span></p>

          <div v-if="summary" class="kpis">
            <div v-for="(item, key) in primaryMetrics" :key="key" class="kpi" :title="summary.metrics[key]?.denominator">
              <span class="eyebrow">{{ item.title }}</span>
              <strong class="tnum">{{ kpiValue(key) ?? 'N/A' }}</strong>
              <span class="note">{{ summary.metrics[key]?.value == null ? MISSING_REASONS[summary.metrics[key]?.reason] || item.unit : item.unit }}</span>
            </div>
          </div>
          <p v-else class="note pad">{{ run?.status === 'completed' ? '正在读取统计…' : '分析完成后，这里显示采样帧的像素统计。缺失的数据不会补成 0。' }}</p>

          <div v-if="summary?.series.length" class="block">
            <CoralSeriesFigure :series="summary.series" :duration="duration || 1" :current-time="currentTime" @seek="t => emit('seek', t)" />
          </div>

          <div v-if="summary" class="block">
            <div class="block-head"><h3>需要真值或 ROI 的指标</h3></div>
            <dl class="na-list">
              <div v-for="(title, key) in truthMetrics" :key="key"><dt>{{ title }}</dt><dd><span class="tag">N/A</span><span class="note">{{ MISSING_REASONS[summary.metrics[key]?.reason] || summary.metrics[key]?.reason }}</span></dd></div>
            </dl>
          </div>

          <div class="block">
            <div class="block-head"><h3>导出</h3></div>
            <div class="exports">
              <button class="btn btn-sm" @click="download" :disabled="!summary"><IconDownload />统计 JSON</button>
            </div>
            <p class="note">导出沿用已应用的窗口，含逐采样帧数值与来源元数据。</p>
            <p v-if="message" class="note" role="status">{{ message }}</p>
          </div>
        </div>
      </template>

      <template #source>
        <div class="pane">
          <dl v-if="run" class="provenance">
            <div><dt>分析 ID</dt><dd><span class="mono">{{ run.run_id }}</span><UiTooltip text="复制"><button class="btn btn-ghost btn-sm btn-icon" aria-label="复制分析 ID" @click="copy(run.run_id)"><IconCopy /></button></UiTooltip></dd></div>
            <div><dt>模型</dt><dd class="mono">{{ run.config_snapshot.models.coral }}</dd></div>
            <div><dt>权重 SHA256</dt><dd><span class="mono hash">{{ run.config_snapshot.model_sha256 }}</span><UiTooltip text="复制"><button class="btn btn-ghost btn-sm btn-icon" aria-label="复制权重哈希" @click="copy(run.config_snapshot.model_sha256)"><IconCopy /></button></UiTooltip></dd></div>
            <div><dt>采样间隔 / 镜头</dt><dd class="tnum">{{ run.config_snapshot.settings.sample_every_seconds }} s · {{ motions[run.config_snapshot.settings.camera_motion] || run.config_snapshot.settings.camera_motion }}</dd></div>
            <div v-if="run.summary?.framework"><dt>运行时</dt><dd class="mono">torch {{ run.summary.framework.torch }} · transformers {{ run.summary.framework.transformers }}</dd></div>
            <div v-if="run.summary?.timestamp_fallback_frames"><dt>按帧号推算时间</dt><dd class="tnum">{{ run.summary.timestamp_fallback_frames }} 帧</dd></div>
          </dl>
          <p v-else class="note">选择一次分析后显示来源。</p>

          <div v-if="meta" class="block">
            <div class="block-head"><h3>模型构成</h3></div>
            <dl class="provenance">
              <div><dt>基础模型</dt><dd><span class="mono">{{ meta.source_model }}</span></dd></div>
              <div><dt>基础模型版本 · 许可</dt><dd><span class="mono" :title="meta.source_revision">{{ meta.source_revision?.slice(0, 12) }}</span> · {{ meta.source_model_license }}</dd></div>
              <div><dt>训练</dt><dd>基础权重冻结，只训练未白化头 · {{ meta.training?.epoch }} epoch · seed {{ meta.training?.seed }}</dd></div>
              <div><dt>推理</dt><dd class="tnum">裁块 {{ meta.inference?.crop }} px · 阈值 {{ meta.inference?.threshold }} · 交付精度 {{ meta.inference?.precision }}</dd></div>
              <div><dt>白化来源类</dt><dd>{{ meta.bleached_source_labels?.length }} 个上游白化类合并为“白化”</dd></div>
            </dl>
          </div>

          <div v-if="evidence" class="block">
            <div class="block-head"><h3>交付复核</h3><span class="tag">非新的独立测试</span></div>
            <table class="evidence tnum">
              <thead><tr><th>数据</th><th>类别</th><th>基础模型 IoU</th><th>交付模型 IoU</th></tr></thead>
              <tbody>
                <tr v-for="row in evidenceRows" :key="row.key"><td>{{ row.domain }}</td><td>{{ row.label }}</td><td>{{ row.baseline }}</td><td>{{ row.adapted }}</td></tr>
              </tbody>
            </table>
            <p class="note">数字来自组员交付的复核报告：开发期已查看过的测试集，换了图像守卫后重新计算，不能当作泛化证据。本地测试集没有白化真值。</p>
          </div>

          <div class="block">
            <div class="block-head"><h3>解读限制</h3></div>
            <ul class="limits">
              <li v-for="item in limitations" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </template>
    </UiTabs>
  </aside>
</template>

<script setup>
import { ref, reactive, computed, watch, onBeforeUnmount, shallowRef, markRaw } from 'vue'
import { listAnalysisModels, listAnalysisRuns, createAnalysisRun, getAnalysisRun, retryAnalysisRun, getAnalysisSummary, getCoralMasks, downloadAnalysis } from '../api'
import { IconRefresh, IconAlertTriangle, IconPlus, IconDownload, IconCopy, IconFocus2, IconChevronLeft, IconChevronRight } from '@tabler/icons-vue'
import UiSelect from './ui/UiSelect.vue'
import UiSwitch from './ui/UiSwitch.vue'
import UiSlider from './ui/UiSlider.vue'
import UiSegmented from './ui/UiSegmented.vue'
import UiTabs from './ui/UiTabs.vue'
import UiTooltip from './ui/UiTooltip.vue'
import CoralSeriesFigure from './CoralSeriesFigure.vue'
import { CORAL_CLASSES, coralCss } from '../lib/palette'
import { sampleAt } from '../lib/coralMasks'
import { MISSING_REASONS, formatDateTime } from '../lib/format'

const props = defineProps({ taskId: Number, currentTime: { type: Number, default: 0 }, fileName: String })
const emit = defineEmits(['coral', 'seek', 'toast'])

const models = ref([]), runs = ref([]), modelId = ref(''), selectedId = ref(''), run = ref(null)
const frames = shallowRef([]), summary = shallowRef(null)
const busy = ref(false), error = ref(''), message = ref(''), statsLoading = ref(false), maskWarning = ref('')
const interval = ref(2), motion = ref('unknown'), filterStart = ref(0), filterEnd = ref('')
const layers = reactive({ mask: true, nonBleached: true, bleached: true, opacity: 0.4, mode: 'both', compare: false })
const modeOptions = [{ value: 'both', label: '填充+轮廓' }, { value: 'fill', label: '填充' }, { value: 'outline', label: '轮廓' }]
const applied = ref({ start_ms: 0 })
const createOpen = ref(false), tab = ref('layers')

const states = { queued: '排队中', running: '分析中', completed: '已完成', failed: '失败' }
const motions = { unknown: '未知', fixed: '固定', moving: '移动' }
const motionOptions = Object.entries(motions).map(([value, label]) => ({ value, label }))
const tabItems = [{ value: 'layers', label: '图层' }, { value: 'stats', label: '统计' }, { value: 'source', label: '来源' }]
const primaryMetrics = {
  coral_pixel_share: { title: '珊瑚像素占比', unit: '已分离背景帧的全部像素' },
  bleached_coral_fraction: { title: '白化占珊瑚', unit: '已分离背景帧的珊瑚像素' },
  bleached_pixel_share: { title: '白化像素占比', unit: '全部采样帧像素' },
  background_separated_frames: { title: '背景分离帧', unit: '帧 / 采样帧' }
}
const truthMetrics = { coral_cover: '珊瑚覆盖率', bleaching_accuracy: '白化识别准确率' }

const runOptions = computed(() => runs.value.map((item, index) => ({ value: item.run_id, label: `第 ${runs.value.length - index} 次 · ${states[item.status] || item.status}`, hint: formatDateTime(item.created_at) })))
const modelOptions = computed(() => models.value.map(model => ({ value: model.id, label: model.id })))
const selectedModel = computed(() => models.value.find(m => m.id === (run.value?.config_snapshot.models.coral || modelId.value)))
const meta = computed(() => selectedModel.value?.metadata || null)
const evidence = computed(() => meta.value?.delivery_evidence || null)
const duration = computed(() => run.value?.summary?.frame_count && run.value?.summary?.fps ? run.value.summary.frame_count / run.value.summary.fps : null)
const currentIndex = computed(() => sampleAt(frames.value, props.currentTime * 1000))
const current = computed(() => frames.value[currentIndex.value] || null)
const pct = value => value == null ? '—' : `${(value * 100).toFixed(value >= 0.1 ? 1 : 2)}%`
// Chips double as the legend: the swatch mirrors the display mode, the share is of the current frame's pixels.
const classChips = computed(() => {
  const p = current.value, area = p ? p.width * p.height : 0
  return [1, 2].map(id => {
    const cls = CORAL_CLASSES[id], on = layers[cls.key]
    const share = p && (id === 2 || p.background_separated) ? p.pixel_counts[id] / area : null
    const fill = layers.mode === 'outline' ? 0 : layers.mode === 'fill' ? 0.85 : 0.4
    return { id, key: cls.key, label: cls.label, share: p ? pct(share) : '',
             swatch: on ? { background: coralCss(id, fill), boxShadow: layers.mode === 'fill' ? 'none' : `inset 0 0 0 2px ${coralCss(id)}` } : {} }
  })
})
// One stacked bar per sampled frame; without background separation class 1 also holds background.
const composition = computed(() => {
  const p = current.value
  if (!p) return []
  const area = p.width * p.height, c = p.pixel_counts
  return p.background_separated
    ? [{ label: '未白化', share: c['1'] / area, color: coralCss(1) }, { label: '白化', share: c['2'] / area, color: coralCss(2) }, { label: '背景', share: c['0'] / area, kind: 'rest' }]
    : [{ label: '白化', share: c['2'] / area, color: coralCss(2) }, { label: '未白化或背景', share: c['1'] / area, kind: 'mixed' }]
})
const compositionText = computed(() => composition.value.map(part => `${part.label} ${pct(part.share)}`).join(' · '))
const evidenceRows = computed(() => {
  const domains = evidence.value?.domains || {}, names = { local: '本地', official: 'Coralscapes' }
  const iou = v => v == null ? 'N/A' : v.toFixed(3)
  return Object.entries(domains).flatMap(([name, d]) => [['1', '未白化'], ['2', '白化']].map(([cls, label]) => ({
    key: `${name}-${cls}`, domain: `${names[name] || name} · ${d.images} 张`, label,
    baseline: iou(d.full_image.baseline[cls].iou), adapted: iou(d.full_image.adapted[cls].iou)
  })))
})
// Known only once a Run of this video has reported its duration.
const estimate = computed(() => {
  const seconds = Number(interval.value), length = duration.value
  if (!length || !(seconds >= 0.5)) return null
  const samples = Math.floor(length / seconds) + 1
  const per = run.value?.summary?.seconds_per_sample
  return { samples, seconds: per ? `${Math.max(1, Math.round(samples * per))} 秒` : null }
})
const limitations = computed(() => summary.value?.limitations || [
  '只有背景、未白化、白化三类，尚无经评审的六类健康映射。',
  '像素占比基于画面平面，不等于底栖覆盖率。'
])
const appliedText = computed(() => {
  const a = applied.value
  const sampled = summary.value?.metrics.sampled_frames?.value
  return `${(a.start_ms / 1000).toFixed(1)}–${a.end_ms == null ? '片尾' : `${(a.end_ms / 1000).toFixed(1)} s`} · ${sampled ?? 0} 个采样帧`
})
const dirty = computed(() => {
  const next = draftWindow()
  return !next || JSON.stringify(next) !== JSON.stringify(applied.value)
})

function kpiValue(key) {
  const metrics = summary.value?.metrics || {}, value = metrics[key]?.value
  if (value == null) return null
  if (key === 'background_separated_frames') return `${value} / ${metrics.sampled_frames.value}`
  return `${(value * 100).toFixed(value >= 0.1 ? 1 : 2)}%`
}

let generation = 0, pollTimer, bootAbort, pollAbort, statsAbort, framesAbort, disposed = false
function cancelled(e) { return e?.code === 'ERR_CANCELED' || e?.name === 'AbortError' }

function errorText(code) {
  const messages = {
    invalid_settings: '参数无效。检查采样间隔后重试。', invalid_sample_interval: '采样间隔要在 0.5 到 60 秒之间。', invalid_camera_motion: '镜头运动取值无效。',
    unknown_model: '找不到该模型。刷新模型列表后重试。', model_kind_mismatch: '这个模型不是珊瑚模型。', retry_not_allowed: '这次分析当前不能重试，或已用完 3 次机会。',
    worker_lease_expired: 'Worker 心跳超时。确认珊瑚 Worker 已恢复后重试。', model_hash_mismatch: '权重与注册哈希不一致。请把新权重注册为新的模型版本。',
    invalid_video: '无法读取源视频。检查本地文件与权限。', video_decode_failed: '视频解码失败。检查 MP4 文件是否完整。', video_incomplete: '视频提前结束。检查源文件是否完整。',
    video_time_reversed: '视频时间戳倒退，已停止分析。', video_time_unavailable: '缺少可靠的时间戳与帧率，无法定位采样帧。',
    too_many_samples: '采样帧超过 1800 个。加大采样间隔后重试。', invalid_model_output: '模型输出不符合三类掩膜约定，已停止分析。',
    input_changed: '分析期间源视频发生变化，结果未发布。', analysis_failed: '分析失败。查看本地 Worker 的运行状态。', invalid_artifacts: '产物校验失败，未发布不完整的结果。'
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
  if (!run.value) { emit('coral', null); return }
  emit('coral', markRaw({
    runId: run.value.status === 'completed' ? run.value.run_id : null, run: run.value, ordinal: runOrdinal(), summary: summary.value,
    frames: frames.value, layers: { ...layers }, window: { ...applied.value }, model: selectedModel.value || null,
    intervalMs: (run.value.config_snapshot.settings.sample_every_seconds || 2) * 1000, fps: run.value.summary?.fps || 30, duration: duration.value
  }))
}
watch(layers, publish, { deep: true })

async function boot() {
  const version = ++generation
  clearTimeout(pollTimer)
  for (const c of [bootAbort, pollAbort, statsAbort, framesAbort]) c?.abort()
  bootAbort = new AbortController()
  run.value = null; selectedId.value = ''; frames.value = []; summary.value = null; runs.value = []; error.value = ''; busy.value = true
  publish()
  try {
    const [m, r] = await Promise.all([listAnalysisModels(bootAbort.signal), listAnalysisRuns(props.taskId, bootAbort.signal)])
    if (version !== generation || disposed) return
    models.value = m.data.items.filter(item => item.kind === 'coral'); runs.value = r.data.items.filter(item => item.kind === 'coral')
    modelId.value = models.value[0]?.id || ''
    selectedId.value = (runs.value.find(item => item.status === 'completed') || runs.value[0])?.run_id || ''
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
  for (const c of [pollAbort, statsAbort, framesAbort]) c?.abort()
  applied.value = { start_ms: 0 }; filterStart.value = 0; filterEnd.value = ''
  run.value = runs.value.find(item => item.run_id === id) || null
  frames.value = []; summary.value = null; maskWarning.value = ''
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
    runs.value = runs.value.map(item => item.run_id === run.value.run_id ? run.value : item)
    publish()
    if (run.value.status === 'completed') { await Promise.all([loadFrames(), loadStats()]); return }
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
    const response = await createAnalysisRun(task, { kind: 'coral', models: { coral: modelId.value }, settings: { sample_every_seconds: Number(interval.value), camera_motion: motion.value } })
    if (task !== props.taskId || disposed) return
    runs.value = [response.data, ...runs.value]; selectedId.value = response.data.run_id; createOpen.value = false
    emit('toast', { title: '珊瑚分析已排队', desc: '旧的分析结果会保留，可在分析记录中切换。' })
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

async function loadFrames() {
  framesAbort?.abort()
  const controller = new AbortController(); framesAbort = controller
  const id = selectedId.value
  try {
    const response = await getCoralMasks(id, controller.signal)
    if (controller.signal.aborted || id !== selectedId.value || disposed) return
    frames.value = markRaw(response.data.items); maskWarning.value = ''
    publish()
  } catch (e) {
    if (!cancelled(e)) maskWarning.value = `采样帧索引读取失败：${problem(e)}`
  }
}

function draftWindow() {
  const params = { start_ms: Number(filterStart.value) * 1000 }
  if (filterEnd.value !== '' && filterEnd.value != null) params.end_ms = Number(filterEnd.value) * 1000
  if (!Number.isFinite(params.start_ms) || params.start_ms < 0 || ('end_ms' in params && (!Number.isFinite(params.end_ms) || params.end_ms <= params.start_ms))) return null
  return params
}
function applyWindow() {
  const params = draftWindow()
  if (!params) { error.value = filterEnd.value !== '' && Number(filterEnd.value) <= Number(filterStart.value) ? '终点要大于起点。' : '时间用非负数。'; return }
  applied.value = params; error.value = ''
  loadStats()
}

async function loadStats() {
  if (run.value?.status !== 'completed') return
  statsAbort?.abort()
  const controller = new AbortController(); statsAbort = controller
  const id = selectedId.value
  statsLoading.value = true; summary.value = null; publish()
  try {
    const response = await getAnalysisSummary(id, applied.value, controller.signal)
    if (controller.signal.aborted || id !== selectedId.value || disposed) return
    summary.value = markRaw(response.data); error.value = ''
    publish()
  } catch (e) {
    if (!cancelled(e)) error.value = problem(e)
  } finally {
    if (statsAbort === controller) statsLoading.value = false
  }
}

function step(offset) {
  const next = frames.value[currentIndex.value + offset]
  if (next) emit('seek', next.timestamp_ms / 1000)
}
function setLayer(key, value) { if (key in layers) layers[key] = value }
defineExpose({ refresh: boot, setLayer })

async function download() {
  try {
    const response = await downloadAnalysis(selectedId.value, 'summary', { ...applied.value, export: 'json' })
    const url = URL.createObjectURL(response.data), a = document.createElement('a')
    a.href = url; a.download = 'coral_report.json'; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    message.value = '已导出。文件包含当前窗口、逐采样帧数值与来源元数据。'
  } catch {
    error.value = '导出失败。刷新后重试。'
  }
}
async function copy(text) {
  try { await navigator.clipboard.writeText(text); emit('toast', { title: '已复制', desc: text.slice(0, 24) + (text.length > 24 ? '…' : '') }) }
  catch { emit('toast', { title: '无法访问剪贴板', desc: '手动选中文本复制。', type: 'alert' }) }
}

onBeforeUnmount(() => {
  disposed = true; generation++
  clearTimeout(pollTimer)
  for (const c of [bootAbort, pollAbort, statsAbort, framesAbort]) c?.abort()
  emit('coral', null)
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
.banner.danger { color: var(--danger); background: var(--danger-soft); }
.link { margin-inline-start: auto; border: 0; background: none; font: inherit; color: inherit; text-decoration: underline; text-underline-offset: 2px; cursor: pointer; white-space: nowrap; }
.run { display: flex; flex-direction: column; gap: 10px; padding: 4px 16px 14px; }
.run-row { display: flex; align-items: flex-end; gap: 8px; }
.grow { flex: 1; }
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
.meta dt, .provenance dt, .frame-facts dt { font-size: var(--text-caption); color: var(--ink-3); }
.meta dd { font-size: var(--text-small); }
.create { display: flex; flex-direction: column; gap: 10px; padding: 12px; border-radius: var(--radius-lg); box-shadow: inset 0 0 0 1px var(--line); }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tabs { flex: none; }
.tabs :deep(.ui-tabs-list) { position: sticky; top: 0; z-index: 2; background: var(--surface); }
.is-on { color: var(--accent); background: var(--accent-soft); box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--accent) 40%, transparent); }
.pad { padding-top: 12px; }
.pane { display: flex; flex-direction: column; gap: 4px; padding: 12px 16px 24px; }
.layer { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; }
.layer .switch { margin-top: 2px; }
.layer label { display: flex; flex-direction: column; gap: 1px; cursor: pointer; }
.layer strong { display: inline-flex; align-items: center; gap: 6px; font-weight: 500; }
.layer-extra { margin: -2px 0 6px 38px; }
.display { display: flex; flex-direction: column; gap: 14px; margin-top: 2px; margin-bottom: 10px; }
.display .layer { padding: 0; }
.class-chips { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.class-chip { display: flex; align-items: center; gap: 8px; height: 32px; padding: 0 10px; border: 0; border-radius: var(--radius); font: inherit; font-size: var(--text-small); color: var(--ink); background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); cursor: pointer; transition-property: background-color, box-shadow, color, scale; transition-duration: 120ms; transition-timing-function: var(--ease); }
.class-chip:hover { background: var(--surface-3); }
.class-chip:active { scale: 0.96; }
.class-chip[aria-pressed=false] { color: var(--ink-3); background: transparent; box-shadow: inset 0 0 0 1px var(--line); }
.class-chip[aria-pressed=false] .chip-share { text-decoration: line-through; }
.chip-swatch { flex: none; width: 12px; height: 12px; border-radius: 3px; box-shadow: inset 0 0 0 1.5px var(--line-strong); }
.chip-share { margin-inline-start: auto; color: var(--ink-2); }
.composition { display: flex; gap: 2px; height: 10px; border-radius: 3px; overflow: hidden; }
.composition > span { min-width: 0; }
.composition .rest { background: var(--surface-3); }
.composition .mixed { background: repeating-linear-gradient(135deg, var(--surface-3) 0 4px, color-mix(in oklch, var(--ink-3) 35%, var(--surface-3)) 4px 6px); }
.composition-key { margin-top: -2px; font-size: var(--text-caption); }
.warn-text { color: var(--warn); }
.block { display: flex; flex-direction: column; gap: 8px; padding-top: 16px; }
.block-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.frame-facts { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px; }
.frame-facts dd { font-size: var(--text-small); }
.row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.filters { display: flex; flex-direction: column; gap: 12px; }
.with-action { display: flex; gap: 4px; align-items: center; }
.applied { display: flex; flex-direction: column; gap: 2px; margin-top: 14px; padding: 8px 10px; border-radius: var(--radius); background: var(--surface-2); font-size: var(--text-small); }
.kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin-top: 12px; border-radius: var(--radius-lg); overflow: hidden; background: var(--line); box-shadow: 0 0 0 1px var(--line); }
.kpi { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; background: var(--surface); min-width: 0; }
.kpi strong { font-size: var(--text-figure); font-weight: 500; line-height: 1.15; letter-spacing: -0.01em; }
.kpi .note { font-size: var(--text-caption); }
.na-list { display: flex; flex-direction: column; gap: 6px; }
.na-list div { display: grid; grid-template-columns: 96px 1fr; gap: 8px; align-items: baseline; font-size: var(--text-small); }
.na-list dt { color: var(--ink-2); }
.na-list dd { display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
.exports { display: flex; flex-wrap: wrap; gap: 6px; }
.provenance { display: flex; flex-direction: column; gap: 10px; }
.provenance dd { display: flex; align-items: flex-start; gap: 4px; flex-wrap: wrap; font-size: var(--text-small); overflow-wrap: anywhere; }
.hash { word-break: break-all; line-height: 1.5; }
.evidence { width: 100%; border-collapse: collapse; font-size: var(--text-caption); }
.evidence th { padding: 4px 6px; font-weight: 500; color: var(--ink-3); text-align: start; box-shadow: inset 0 -1px 0 var(--line); }
.evidence td { padding: 5px 6px; color: var(--ink-2); box-shadow: inset 0 -1px 0 var(--line); }
.evidence th:nth-child(n+3), .evidence td:nth-child(n+3) { text-align: end; }
.limits { display: flex; flex-direction: column; gap: 6px; padding-inline-start: 16px; list-style: disc; color: var(--ink-2); font-size: var(--text-small); line-height: 1.55; }
.limits li::marker { color: var(--ink-3); }
</style>
