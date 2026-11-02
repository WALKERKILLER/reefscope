<template>
  <section class="wall-head" aria-label="鱼类活动监测">
    <div class="title-bar">
      <div class="title">
        <span class="beacon" aria-hidden="true" />
        <h1>鱼类活动监测</h1>
        <p v-if="run" class="meta">
          <span class="file" :title="fileName">{{ fileName }}</span>
          <span class="sep" /><span>第 {{ analysis.ordinal ?? '—' }} 次分析</span>
          <span class="sep" /><span class="mono">{{ run.config_snapshot.models.fish }}</span>
          <template v-if="run.summary?.width"><span class="sep" /><span class="tnum">{{ run.summary.width }}×{{ run.summary.height }} · {{ run.summary.fps?.toFixed(0) }} fps</span></template>
        </p>
        <p v-else class="meta">{{ fileName ? '等待分析结果' : '在工作台打开视频并完成分析后，这里显示它的监测证据。' }}</p>
      </div>
      <div class="status">
        <span v-if="run" class="chip" :class="motion === 'fixed' ? 'ok' : 'warn'"><IconCamera />{{ motionText }}</span>
        <span v-if="isDemo" class="chip warn"><IconFlask />合成演示数据</span>
        <span v-if="run" class="chip"><IconRefresh />更新于 <span class="tnum">{{ formatDateTime(run.updated_at) }}</span></span>
        <time class="clock tnum" :datetime="now.toISOString()">{{ clock }}</time>
      </div>
    </div>

    <div v-if="run" class="kpis">
      <div class="group live">
        <span class="caption"><span class="live-dot" aria-hidden="true" />当前画面 · <span class="tnum">{{ formatClock(currentTime) }}</span></span>
        <div class="tiles">
          <div class="kpi">
            <span class="eyebrow">画面内 ID</span>
            <span class="value"><strong class="tnum">{{ liveCount ?? '—' }}</strong><span class="unit">个</span></span>
            <Sparkline v-if="visibleSeries.length" :points="visibleSeries" :domain="[0, duration]" :playhead="currentTime" />
            <span v-else class="note">正在加载全片轨迹</span>
          </div>
        </div>
      </div>
      <div class="group window">
        <span class="caption">窗口统计 · <span class="tnum">{{ windowText }}</span><template v-if="analysis.roi"> · ROI {{ analysis.roi.length }} 点</template></span>
        <div class="tiles">
          <div v-for="tile in windowTiles" :key="tile.key" class="kpi">
            <span class="eyebrow">{{ tile.title }}</span>
            <span class="value"><strong class="tnum">{{ tile.value ?? (analysis.summary ? 'N/A' : '…') }}</strong><span class="unit">{{ tile.unit }}</span></span>
            <Sparkline v-if="tile.spark" :points="tile.spark" :domain="[0, duration]" :window="windowRange" />
            <span v-else class="note" :title="tile.note">{{ tile.note }}</span>
          </div>
        </div>
      </div>
      <div class="group eval">
        <span class="caption">独立评估</span>
        <div class="tiles">
          <div v-for="tile in evalTiles" :key="tile.key" class="kpi missing">
            <span class="eyebrow">{{ tile.title }}</span>
            <span class="value"><strong class="tnum">{{ tile.value ?? 'N/A' }}</strong></span>
            <span class="note" :title="tile.note">{{ tile.note }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { IconCamera, IconFlask, IconRefresh } from '@tabler/icons-vue'
import Sparkline from './wall/Sparkline.vue'
import { formatClock, formatDateTime, metricValue, MISSING_REASONS } from '../lib/format'
import { newIdsCumulative, visibleAt, visiblePerSecond } from '../lib/tracks'

const props = defineProps({ analysis: { type: Object, default: null }, fileName: String, currentTime: { type: Number, default: 0 } })
const run = computed(() => props.analysis?.run || null)
const metrics = computed(() => props.analysis?.summary?.metrics || {})
const duration = computed(() => props.analysis?.duration || props.analysis?.overview?.frames.at(-1)?.[0] || 1)
const isDemo = computed(() => /synthetic|合成|DEMO/i.test(props.fileName || ''))
const motion = computed(() => run.value?.config_snapshot.settings.camera_motion || 'unknown')
const motionText = computed(() => ({ fixed: '固定机位', moving: '移动机位 · 画面坐标随镜头漂移' }[motion.value] || '机位未声明 · 坐标可能漂移'))

// Wall clock for the room, not a data timestamp.
const now = ref(new Date())
const timer = setInterval(() => { now.value = new Date() }, 1000)
onBeforeUnmount(() => clearInterval(timer))
const clock = computed(() => now.value.toLocaleString('zh-CN', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).replace(/\//g, '-'))

const frames = computed(() => props.analysis?.overview?.frames || [])
const visibleSeries = computed(() => frames.value.length ? visiblePerSecond(frames.value, duration.value) : [])
const idSeries = computed(() => props.analysis?.overview?.spans?.length ? newIdsCumulative(props.analysis.overview.spans, duration.value) : null)
const liveCount = computed(() => frames.value.length ? visibleAt(frames.value, props.currentTime, props.analysis?.fps) : null)

const windowRange = computed(() => {
  const w = props.analysis?.window
  return w ? [w.start_ms / 1000, w.end_ms == null ? duration.value : w.end_ms / 1000] : null
})
const windowText = computed(() => {
  const w = props.analysis?.window || { start_ms: 0 }
  return `${(w.start_ms / 1000).toFixed(1)}–${w.end_ms == null ? '片尾' : `${(w.end_ms / 1000).toFixed(1)} s`}`
})
const value = (key, digits) => metricValue(metrics.value[key], digits)
const windowTiles = computed(() => {
  const ids = metrics.value.observed_track_count?.value, seconds = metrics.value.track_seconds?.value
  const threshold = run.value?.config_snapshot.settings.confidence_threshold
  return [
    { key: 'ids', title: '观测 ID 数', value: value('observed_track_count', 0), unit: '个 · 非个体数', spark: idSeries.value },
    { key: 'obs', title: '追踪观测次数', value: value('tracked_observation_count', 0), unit: '次', note: '逐帧框级观测，同一 ID 多帧计多次' },
    { key: 'sec', title: '累计停留', value: value('track_seconds', 1), unit: 'track-s', note: ids && seconds != null ? `平均每个 ID ${(seconds / ids).toFixed(2)} s` : '有效轨迹段积分' },
    { key: 'conf', title: '平均置信度', value: value('mean_confidence', 3), unit: '', note: `模型输出，非准确率${threshold != null ? ` · 阈值 ${threshold}` : ''}` }
  ]
})
const reason = key => MISSING_REASONS[metrics.value[key]?.reason] || (props.analysis?.summary ? '缺少所需真值' : '正在计算')
const evalTiles = computed(() => [
  { key: 'ap50', title: '独立测试 AP50', value: value('ap50', 3), note: reason('ap50') },
  { key: 'coral', title: '珊瑚覆盖率', value: value('coral_cover', 3), note: reason('coral_cover') }
])
</script>

<style scoped>
.wall-head { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.title-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-width: 0; white-space: nowrap; }
.title { display: flex; align-items: baseline; gap: 12px; min-width: 0; }
.beacon { align-self: center; flex: none; width: 3px; height: 18px; border-radius: 2px; background: var(--accent); }
h1 { flex: none; font-size: var(--text-heading); font-weight: 600; letter-spacing: -0.01em; }
.meta { display: flex; align-items: center; gap: 8px; min-width: 0; overflow: hidden; font-size: var(--text-small); color: var(--ink-3); }
.file { min-width: 0; max-width: 28ch; overflow: hidden; text-overflow: ellipsis; color: var(--ink-2); }
.sep { flex: none; width: 3px; height: 3px; border-radius: 50%; background: var(--ink-3); opacity: 0.6; }
.status { display: flex; align-items: center; gap: 6px; flex: none; }
.chip { display: inline-flex; align-items: center; gap: 5px; height: 24px; padding: 0 9px; border-radius: 12px; font-size: var(--text-caption); color: var(--ink-2); background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); }
.chip .tabler-icon { --icon-size: 13px; color: var(--ink-3); }
.chip.ok .tabler-icon { color: var(--ok); }
.chip.warn { color: var(--warn); background: var(--warn-soft); box-shadow: none; }
.chip.warn .tabler-icon { color: currentColor; }
.clock { margin-inline-start: 6px; padding-inline-start: 12px; font-size: var(--text-title); font-weight: 500; color: var(--ink); box-shadow: inset 1px 0 0 var(--line); }

.kpis { display: flex; gap: 12px; min-width: 0; }
.group { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.live { flex: 1.15; }
.window { flex: 4; }
.eval { flex: 2; }
.caption { display: inline-flex; align-items: center; gap: 6px; font-size: var(--text-caption); font-weight: 500; color: var(--ink-3); white-space: nowrap; }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.tiles { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: 1px; flex: 1; border-radius: var(--radius); overflow: hidden; background: var(--line); box-shadow: 0 0 0 1px var(--line); }
.kpi { display: grid; grid-template-rows: auto auto 28px; align-content: space-between; gap: 2px; min-width: 0; padding: 10px 12px 8px; background: var(--surface); }
.live .kpi { background: linear-gradient(180deg, var(--accent-soft), transparent 70%), var(--surface); }
.value { display: flex; align-items: baseline; gap: 6px; min-width: 0; white-space: nowrap; }
.value strong { font-size: var(--text-display); font-weight: 500; line-height: 1.05; letter-spacing: -0.02em; }
.unit { min-width: 0; overflow: hidden; text-overflow: ellipsis; font-size: var(--text-caption); color: var(--ink-3); }
.kpi .note { align-self: end; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--text-caption); line-height: 1.4; }
.kpi :deep(.spark) { align-self: end; }
.missing strong { color: var(--ink-3); }

@media (max-width: 1600px), (max-height: 900px) { .value strong { font-size: var(--text-figure); } .kpi { padding: 8px 10px 6px; } }
/* Short walls (768p and below) trade sparkline height for plot area; values keep their size. */
@media (max-height: 800px) { .wall-head { gap: 6px; } .kpi { grid-template-rows: auto auto 20px; padding: 6px 10px 4px; } .kpi :deep(.spark) { height: 20px; } }
@media (max-width: 1360px) { .status .chip:not(.warn) { display: none; } .file { max-width: 18ch; } }
@media (max-width: 1100px) {
  .kpis { flex-wrap: wrap; }
  .window { flex-basis: 100%; order: -1; }
  .title-bar { flex-wrap: wrap; white-space: normal; }
}
@media (max-width: 640px) {
  .kpis { flex-direction: column; }
  .window .tiles { grid-auto-flow: row; grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
