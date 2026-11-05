<template>
  <figure class="figure">
    <figcaption>
      <h3>逐采样帧像素占比</h3>
      <span class="note legend">
        <span class="key"><span class="line" :style="{ background: color(1) }" />珊瑚像素</span>
        <span class="key"><span class="line dashed" :style="{ color: color(2) }" />白化像素</span>
      </span>
    </figcaption>
    <div ref="stage" class="stage">
      <div ref="host" class="plot" />
      <div
        class="overlay"
        role="slider"
        tabindex="0"
        aria-label="采样帧定位"
        :aria-valuemin="0"
        :aria-valuemax="Math.max(0, series.length - 1)"
        :aria-valuenow="Math.max(0, currentIndex)"
        :aria-valuetext="ariaValue"
        @pointermove="hover"
        @pointerleave="hoverIndex = -1"
        @click="seekHovered"
        @keydown="onKey"
      >
        <div class="playhead" :style="{ transform: `translateX(${x(currentTime)}px)` }" />
        <div v-if="hovered" class="tip" :class="{ flip: hoverPx > width / 2 }" :style="{ transform: `translateX(${hoverPx}px)` }">
          <span class="tnum">{{ (hovered.timestamp_ms / 1000).toFixed(1) }} s</span>
          <span><span class="dot" :style="{ background: color(1) }" />珊瑚 <span class="tnum">{{ hovered.coral_share == null ? '未分离背景' : pct(hovered.coral_share) }}</span></span>
          <span><span class="dot" :style="{ background: color(2) }" />白化 <span class="tnum">{{ pct(hovered.bleached_share) }}</span></span>
        </div>
      </div>
    </div>
    <p class="note">占比的分母是整帧像素。未分离背景的帧没有珊瑚像素值，线在这些帧断开。点击跳到该采样帧，方向键逐帧切换。</p>
  </figure>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useChart } from '../charts/useChart'
import { CORAL_CLASSES } from '../lib/palette'
import { isDark } from '../lib/theme'
import { sampleAt } from '../lib/coralMasks'

const props = defineProps({ series: { type: Array, default: () => [] }, duration: { type: Number, default: 1 }, currentTime: { type: Number, default: 0 } })
const emit = defineEmits(['seek'])
const host = ref(null), stage = ref(null), width = ref(0), hoverIndex = ref(-1), hoverPx = ref(0)
const PAD = { left: 40, right: 10, top: 8, bottom: 20 }

const color = id => isDark.value ? CORAL_CLASSES[id].ink : CORAL_CLASSES[id].paper
const pct = value => `${(value * 100).toFixed(value >= 0.1 ? 1 : 2)}%`
const span = computed(() => Math.max(props.duration || 0, (props.series.at(-1)?.timestamp_ms || 0) / 1000, 1))
const plotWidth = computed(() => Math.max(1, width.value - PAD.left - PAD.right))
const x = t => PAD.left + Math.min(1, Math.max(0, t / span.value)) * plotWidth.value
const currentIndex = computed(() => sampleAt(props.series, props.currentTime * 1000))
const hovered = computed(() => props.series[hoverIndex.value] || null)
const ariaValue = computed(() => {
  const p = props.series[currentIndex.value]
  return p ? `${(p.timestamp_ms / 1000).toFixed(1)} 秒，白化像素 ${pct(p.bleached_share)}${p.coral_share == null ? '，未分离背景' : `，珊瑚像素 ${pct(p.coral_share)}`}` : '没有采样帧'
})

const { render } = useChart(host, (t, size) => {
  width.value = size.width
  if (!props.series.length) return null
  const points = key => props.series.map(p => [p.timestamp_ms / 1000, p[key] == null ? null : p[key] * 100])
  const symbol = props.series.length <= 60
  const line = (key, id, dashed) => ({
    type: 'line', data: points(key), connectNulls: false, silent: true, showSymbol: symbol, symbol: 'circle', symbolSize: 6,
    lineStyle: { width: 2, color: color(id), type: dashed ? [4, 3] : 'solid' }, itemStyle: { color: color(id), borderColor: t.surface, borderWidth: 2 }
  })
  return {
    animation: false,
    grid: { left: PAD.left, right: PAD.right, top: PAD.top, bottom: PAD.bottom },
    xAxis: { type: 'value', min: 0, max: span.value, axisLine: { lineStyle: { color: t.line } }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { color: t.ink3, fontSize: 10, formatter: v => `${v}s` } },
    yAxis: { type: 'value', min: 0, splitNumber: 3, axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: t.line, opacity: 0.6 } }, axisLabel: { color: t.ink3, fontSize: 10, formatter: v => `${v}%` } },
    series: [line('coral_share', 1, false), line('bleached_share', 2, true)]
  }
})

function hover(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const t = Math.min(span.value, Math.max(0, (event.clientX - rect.left - PAD.left) / plotWidth.value * span.value))
  let best = -1, gap = Infinity
  props.series.forEach((p, i) => { const d = Math.abs(p.timestamp_ms / 1000 - t); if (d < gap) { gap = d; best = i } })
  hoverIndex.value = best
  hoverPx.value = best >= 0 ? x(props.series[best].timestamp_ms / 1000) : 0
}
function seekHovered() { if (hovered.value) emit('seek', hovered.value.timestamp_ms / 1000) }
function onKey(event) {
  const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key]
  if (!step || !props.series.length) return
  event.preventDefault()
  const next = Math.min(props.series.length - 1, Math.max(0, currentIndex.value + step))
  emit('seek', props.series[next].timestamp_ms / 1000)
}

watch(() => [props.series, props.duration], () => render())
let observer
onMounted(() => {
  render()
  observer = new ResizeObserver(entries => { width.value = entries[0].contentRect.width })
  observer.observe(stage.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<style scoped>
.figure { display: flex; flex-direction: column; gap: 6px; min-width: 0; margin: 0; }
figcaption { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.legend { display: inline-flex; gap: 10px; font-size: var(--text-caption); }
.key { display: inline-flex; align-items: center; gap: 5px; }
.line { width: 14px; height: 2px; border-radius: 1px; }
.line.dashed { background: repeating-linear-gradient(90deg, currentColor 0 4px, transparent 4px 7px); }
.stage { position: relative; height: 132px; }
.plot { position: absolute; inset: 0; }
.overlay { position: absolute; inset: 0; cursor: crosshair; outline-offset: -2px; }
.playhead { position: absolute; top: 8px; bottom: 20px; left: 0; width: 1px; background: var(--accent); pointer-events: none; will-change: transform; }
.tip { position: absolute; top: 8px; left: 0; display: flex; flex-direction: column; gap: 2px; padding: 5px 8px; margin-inline-start: 8px; border-radius: var(--radius-sm); font-size: var(--text-caption); color: var(--ink); background: var(--surface-3); box-shadow: 0 0 0 1px var(--line); white-space: nowrap; pointer-events: none; }
.tip.flip { translate: calc(-100% - 16px) 0; }
.dot { display: inline-block; width: 6px; height: 6px; margin-inline-end: 4px; border-radius: 50%; }
.note { font-size: var(--text-caption); line-height: 1.5; }
</style>
