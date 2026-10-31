<template>
  <figure class="figure" :class="{ fill }">
    <figcaption>
      <div class="cap-row">
        <h3 v-if="!bare">轨迹图</h3>
        <p v-else class="note"><span class="tnum">{{ shown.length.toLocaleString('zh-CN') }}</span> 条 · 窗口 {{ windowText }}</p>
        <label class="frame-toggle"><UiSwitch v-model="showFrame" />当前帧底图</label>
      </div>
      <p v-if="!bare" class="note">画面坐标 · <span class="tnum">{{ shown.length.toLocaleString('zh-CN') }}</span> 条轨迹（窗口 {{ windowText }}）· 空心点为起点，实心点为终点</p>
    </figcaption>
    <div ref="host" class="plot" role="img" :aria-label="`轨迹图，${shown.length} 条轨迹，画面坐标`" />
    <p v-if="truncated" class="note warn-text">观测超过显示上限，图中只含前 20,000 条。</p>
    <p v-if="!bare" class="note foot">颜色只用于区分相邻轨迹，以 # 编号为准；同一 ID 断开超过允许间隔后分段绘制。</p>
  </figure>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import UiSwitch from './ui/UiSwitch.vue'
import { useChart } from '../charts/useChart'
import { trackColor } from '../lib/palette'
import { captureFrame } from '../lib/playback'
import { isDark } from '../lib/theme'

const props = defineProps({ spans: { type: Array, default: () => [] }, window: { type: Object, default: () => ({ start_ms: 0 }) }, roi: { type: Array, default: null }, aspect: { type: Number, default: 16 / 9 }, truncated: Boolean, compact: Boolean, fill: Boolean, bare: Boolean })
const host = ref(null)
const showFrame = ref(false)
let frame = null

const shown = computed(() => {
  const start = props.window?.start_ms ?? 0, end = props.window?.end_ms ?? Infinity
  const out = []
  for (const entry of props.spans) {
    if (props.window?.track_id != null && entry.id !== props.window.track_id) continue
    const paths = entry.paths.map(path => path.filter(p => p[2] >= start && p[2] < end)).filter(path => path.length)
    if (paths.length) out.push({ ...entry, paths })
  }
  return out
})
const windowText = computed(() => `${((props.window?.start_ms ?? 0) / 1000).toFixed(1)}–${props.window?.end_ms == null ? '片尾' : `${(props.window.end_ms / 1000).toFixed(1)} s`}`)

const { render } = useChart(host, (t, size) => {
  const surface = isDark.value || frame ? 'video' : 'paper'
  const pad = { left: 30, right: 12, top: 6, bottom: 26 }
  const availW = size.width - pad.left - pad.right, availH = size.height - pad.top - pad.bottom
  const plotW = Math.min(availW, availH * props.aspect), plotH = plotW / props.aspect
  const left = pad.left + (availW - plotW) / 2
  const axis = { min: 0, max: 1, interval: 0.25, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: true, lineStyle: { color: t.line, width: 1 } }, axisLabel: { color: t.ink3, fontSize: 10, formatter: v => v === 0 ? '0' : v === 1 ? '1' : v.toFixed(2).replace(/^0/, '') } }
  const lines = [], starts = [], ends = []
  for (const entry of shown.value) {
    const color = trackColor(entry.id, surface)
    for (const path of entry.paths) {
      if (path.length > 1) lines.push({ coords: path.map(p => [p[0], p[1]]), id: entry.id, lineStyle: { color } })
    }
    const first = entry.paths[0][0], lastPath = entry.paths[entry.paths.length - 1], last = lastPath[lastPath.length - 1]
    starts.push({ value: [first[0], first[1]], id: entry.id, t: first[2], itemStyle: { borderColor: color } })
    ends.push({ value: [last[0], last[1]], id: entry.id, t: last[2], itemStyle: { color } })
  }
  const tip = p => {
    const entry = shown.value.find(e => e.id === p.data.id)
    if (!entry) return ''
    return `<b>#${entry.id}</b> · ${entry.label ?? ''}<br>${(entry.first / 1000).toFixed(2)}–${(entry.last / 1000).toFixed(2)} s · ${entry.count} 次观测`
  }
  return {
    animation: false,
    aria: { enabled: true },
    grid: { left, top: pad.top, width: plotW, height: plotH },
    xAxis: { type: 'value', ...axis },
    yAxis: { type: 'value', inverse: true, ...axis },
    graphic: frame ? [{ type: 'image', left, top: pad.top, z: -1, silent: true, style: { image: frame, width: plotW, height: plotH, opacity: 0.5 } }] : [],
    tooltip: { trigger: 'item', confine: true, backgroundColor: t.surface, borderColor: t.line, textStyle: { color: t.ink, fontSize: 12 }, formatter: tip },
    series: [
      { type: 'lines', coordinateSystem: 'cartesian2d', polyline: true, data: lines, lineStyle: { width: 1.25, opacity: 0.85 }, emphasis: { lineStyle: { width: 2.5, opacity: 1 } }, progressive: 400, z: 2 },
      { type: 'scatter', data: starts, symbolSize: 6, itemStyle: { color: 'transparent', borderWidth: 1.25 }, z: 3 },
      { type: 'scatter', data: ends, symbolSize: 5, z: 4 },
      ...(props.roi ? [{ type: 'line', data: [...props.roi, props.roi[0]], showSymbol: false, silent: true, lineStyle: { color: t.warn, width: 1.5, type: [4, 3] }, z: 5 }] : [])
    ]
  }
})

function refresh() {
  frame = showFrame.value ? captureFrame(720) : null
  render()
}
watch(() => [shown.value, props.roi, props.aspect, showFrame.value], refresh)
onMounted(refresh)
</script>

<style scoped>
.figure { display: flex; flex-direction: column; gap: 6px; margin: 0; }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.cap-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.cap-row .note { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--text-caption); }
.frame-toggle { flex: none; white-space: nowrap; display: inline-flex; align-items: center; gap: 6px; font-size: var(--text-caption); color: var(--ink-3); cursor: pointer; }
.plot { width: 100%; aspect-ratio: 16 / 10; min-height: 160px; }
.foot { font-size: var(--text-caption); }
.fill { flex: 1; min-height: 0; }
.fill .plot { flex: 1; aspect-ratio: auto; min-height: 88px; }
.warn-text { color: var(--warn); }
</style>
