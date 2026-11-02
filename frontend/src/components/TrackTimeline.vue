<template>
  <section class="timeline" aria-label="轨迹时间线">
    <header>
      <h3>轨迹时间线</h3>
      <span class="note tnum">{{ spans.length.toLocaleString('zh-CN') }} 个 ID · 峰值 {{ peakCount }} 个/帧</span>
      <span class="note legend"><span class="key count" />每帧观测数<span class="key lane" />每个 ID 的连续观测</span>
    </header>
    <div class="stage" ref="stage">
      <div ref="host" class="plot" />
      <div
        class="overlay"
        role="slider"
        tabindex="0"
        aria-label="时间线定位"
        :aria-valuemin="0"
        :aria-valuemax="Math.round(span)"
        :aria-valuenow="Math.round(currentTime)"
        :aria-valuetext="formatClock(currentTime)"
        @pointermove="hover"
        @pointerleave="hoverInfo = null"
        @click="seekFromEvent"
        @keydown="onKey"
      >
        <div v-if="windowBox" class="window" :style="windowBox" />
        <div class="playhead" :style="{ transform: `translateX(${x(currentTime)}px)` }"><span class="tnum">{{ formatClock(currentTime) }}</span></div>
        <div v-if="hoverInfo" class="hover" :style="{ transform: `translateX(${hoverInfo.px}px)` }">
          <span class="tnum">{{ formatClock(hoverInfo.t) }}<template v-if="hoverInfo.id != null"> · #{{ hoverInfo.id }}</template></span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useChart } from '../charts/useChart'
import { trackColor } from '../lib/palette'
import { formatClock } from '../lib/format'
import { isDark } from '../lib/theme'

const props = defineProps({
  spans: { type: Array, default: () => [] },
  frames: { type: Array, default: () => [] },
  duration: { type: Number, default: null },
  currentTime: { type: Number, default: 0 },
  window: { type: Object, default: null }
})
const emit = defineEmits(['seek'])
const host = ref(null), stage = ref(null)
const width = ref(0)
const hoverInfo = ref(null)
const PAD = { left: 28, right: 10, countTop: 4, countHeight: 26, laneTop: 36, bottom: 20 }

const span = computed(() => props.duration || Math.max(1, ...props.spans.map(s => s.last / 1000)))
const peakCount = computed(() => props.frames.reduce((m, f) => Math.max(m, f[1]), 0))
const plotWidth = computed(() => Math.max(1, width.value - PAD.left - PAD.right))
const x = t => PAD.left + Math.min(1, Math.max(0, t / span.value)) * plotWidth.value
const windowBox = computed(() => {
  const w = props.window
  if (!w || (!w.start_ms && w.end_ms == null)) return null
  const a = x((w.start_ms || 0) / 1000), b = x(w.end_ms == null ? span.value : w.end_ms / 1000)
  return { left: `${a}px`, width: `${Math.max(1, b - a)}px` }
})

const { render } = useChart(host, (t, size) => {
  width.value = size.width
  const surface = isDark.value ? 'video' : 'paper'
  const lanes = Math.max(1, props.spans.length)
  const laneArea = size.height - PAD.laneTop - PAD.bottom
  const bars = []
  props.spans.forEach((entry, lane) => {
    for (const s of entry.spans) bars.push([lane, s.start / 1000, s.end / 1000, entry.id])
  })
  const axisX = { type: 'value', min: 0, max: span.value, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
  return {
    animation: false,
    grid: [
      { left: PAD.left, right: PAD.right, top: PAD.countTop, height: PAD.countHeight },
      { left: PAD.left, right: PAD.right, top: PAD.laneTop, height: laneArea }
    ],
    xAxis: [
      { ...axisX, gridIndex: 0, axisLabel: { show: false } },
      { ...axisX, gridIndex: 1, splitNumber: 8, axisLabel: { color: t.ink3, fontSize: 10, formatter: v => formatClock(v).replace(/\.\d$/, '') }, splitLine: { show: true, lineStyle: { color: t.line, opacity: 0.6 } } }
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, min: 0, max: Math.max(1, peakCount.value), interval: Math.max(1, peakCount.value), axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: true, lineStyle: { color: t.line, opacity: 0.6 } }, axisLabel: { color: t.ink3, fontSize: 9, showMinLabel: false } },
      { type: 'value', gridIndex: 1, min: 0, max: lanes, inverse: true, show: false }
    ],
    series: [
      { type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: props.frames, step: 'end', showSymbol: false, silent: true, lineStyle: { width: 1, color: t.ink2 }, areaStyle: { color: t.ink3, opacity: 0.18 } },
      {
        type: 'custom', xAxisIndex: 1, yAxisIndex: 1, data: bars, silent: true, clip: true,
        renderItem: (_, api) => {
          const lane = api.value(0)
          const a = api.coord([api.value(1), lane]), b = api.coord([api.value(2), lane + 1])
          const h = Math.max(1, (b[1] - a[1]) * (lanes > 40 ? 1 : 0.7))
          return { type: 'rect', shape: { x: a[0], y: a[1] + ((b[1] - a[1]) - h) / 2, width: Math.max(1.5, b[0] - a[0]), height: h }, style: { fill: trackColor(api.value(3), surface) } }
        }
      }
    ]
  }
})

function timeAt(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const px = event.clientX - rect.left
  return { px: Math.min(PAD.left + plotWidth.value, Math.max(PAD.left, px)), t: Math.min(span.value, Math.max(0, (px - PAD.left) / plotWidth.value * span.value)), y: event.clientY - rect.top, height: rect.height }
}
function hover(event) {
  const { px, t, y, height } = timeAt(event)
  const laneArea = height - PAD.laneTop - PAD.bottom
  const lane = Math.floor((y - PAD.laneTop) / laneArea * props.spans.length)
  const entry = lane >= 0 && lane < props.spans.length ? props.spans[lane] : null
  const inside = entry && entry.spans.some(s => t * 1000 >= s.start - 50 && t * 1000 <= s.end + 50)
  hoverInfo.value = { px, t, id: inside ? entry.id : null }
}
function seekFromEvent(event) { emit('seek', timeAt(event).t) }
function onKey(event) {
  const step = event.shiftKey ? 5 : 1
  if (event.key === 'ArrowRight') { event.preventDefault(); emit('seek', Math.min(span.value, props.currentTime + step)) }
  if (event.key === 'ArrowLeft') { event.preventDefault(); emit('seek', Math.max(0, props.currentTime - step)) }
  if (event.key === 'Home') { event.preventDefault(); emit('seek', 0) }
}

watch(() => [props.spans, props.frames, props.duration], () => render())
let observer
onMounted(() => {
  render()
  observer = new ResizeObserver(entries => { width.value = entries[0].contentRect.width })
  observer.observe(stage.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<style scoped>
.timeline { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.legend { display: inline-flex; align-items: center; gap: 6px; margin-inline-start: auto; font-size: var(--text-caption); }
.key { display: inline-block; width: 10px; height: 6px; border-radius: 1px; }
.key.count { background: color-mix(in oklch, var(--ink-3) 40%, transparent); box-shadow: inset 0 1px 0 var(--ink-2); }
.key.lane { margin-inline-start: 8px; background: linear-gradient(90deg, #fda19a, #81d584, #6cc9fd); }
.stage { position: relative; height: 128px; }
.plot { position: absolute; inset: 0; }
.overlay { position: absolute; inset: 0; cursor: crosshair; outline-offset: -2px; }
.window { position: absolute; top: 0; bottom: 20px; background: var(--accent-soft); box-shadow: inset 1px 0 0 var(--accent), inset -1px 0 0 var(--accent); pointer-events: none; }
.playhead, .hover { position: absolute; top: 0; bottom: 20px; left: 0; width: 1px; pointer-events: none; will-change: transform; }
.playhead { background: var(--accent); }
.playhead span, .hover span { position: absolute; top: -1px; left: 4px; padding: 0 4px; border-radius: 3px; font-size: 11px; line-height: 16px; white-space: nowrap; }
.playhead span { color: var(--accent-ink); background: var(--accent); }
.hover { background: var(--ink-3); opacity: 0.8; }
.hover span { top: auto; bottom: 2px; color: var(--ink); background: var(--surface-3); }
</style>
