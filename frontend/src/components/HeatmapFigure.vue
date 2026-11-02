<template>
  <figure class="figure" :class="{ compact, fill }">
    <figcaption>
      <div class="cap-row">
        <h3 v-if="!bare">停留热图</h3>
        <p v-else class="note tnum" :title="`每格停留时间（track-s），颜色按窗口峰值线性映射`">{{ heatmap.width }}×{{ heatmap.height }} 格 · 峰值 {{ peak.toFixed(2) }} · 合计 {{ heatmap.track_seconds_total.toFixed(1) }} track-s</p>
        <label class="frame-toggle"><UiSwitch v-model="showFrame" />当前帧底图</label>
      </div>
      <p v-if="!bare" class="note">画面坐标 {{ heatmap.width }}×{{ heatmap.height }} 格 · 每格停留时间（track-s）· 合计 <span class="tnum">{{ heatmap.track_seconds_total.toFixed(1) }}</span> track-s</p>
    </figcaption>
    <div ref="host" class="plot" role="img" :aria-label="`停留热图，峰值 ${peak.toFixed(2)} track-s，合计 ${heatmap.track_seconds_total.toFixed(1)} track-s，画面坐标而非地理坐标`" />
    <p v-if="!bare" class="note foot">空白格为 0。颜色按窗口峰值线性映射（inferno），非海底地理密度。</p>
  </figure>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import UiSwitch from './ui/UiSwitch.vue'
import { useChart } from '../charts/useChart'
import { INFERNO } from '../lib/palette'
import { captureFrame } from '../lib/playback'

const props = defineProps({ heatmap: { type: Object, required: true }, roi: { type: Array, default: null }, aspect: { type: Number, default: 16 / 9 }, compact: Boolean, fill: Boolean, bare: Boolean })
const host = ref(null)
const showFrame = ref(true)
const peak = computed(() => Math.max(0, ...props.heatmap.values_raw.flat()))
let frame = null

const { render } = useChart(host, (t, size) => {
  const { width: W, height: H, values_raw: raw, track_seconds_total: total } = props.heatmap
  const data = []
  raw.forEach((row, y) => row.forEach((v, x) => { if (v > 0) data.push([x, y, v]) }))
  const pad = { left: 30, right: 54, top: 6, bottom: 26 }
  const availW = size.width - pad.left - pad.right, availH = size.height - pad.top - pad.bottom
  const plotW = Math.min(availW, availH * props.aspect), plotH = plotW / props.aspect
  const left = pad.left + (availW - plotW) / 2
  const axis = { min: 0, max: 1, interval: 0.25, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { color: t.ink3, fontSize: 10, formatter: v => v === 0 ? '0' : v === 1 ? '1' : v.toFixed(2).replace(/^0/, '') } }
  return {
    animation: false,
    aria: { enabled: true },
    grid: { left, top: pad.top, width: plotW, height: plotH },
    xAxis: { type: 'value', ...axis },
    yAxis: { type: 'value', inverse: true, ...axis },
    visualMap: { type: 'continuous', min: 0, max: peak.value || 1, dimension: 2, seriesIndex: 0, calculable: false, orient: 'vertical', left: left + plotW + 10, top: pad.top, itemWidth: 8, itemHeight: Math.max(40, plotH - 30), text: [peak.value.toFixed(2), '0'], textGap: 4, textStyle: { color: t.ink3, fontSize: 10 }, inRange: { color: INFERNO } },
    graphic: frame ? [{ type: 'image', left, top: pad.top, z: -1, silent: true, style: { image: frame, width: plotW, height: plotH, opacity: 0.55 } }] : [{ type: 'rect', left, top: pad.top, z: -1, silent: true, shape: { width: plotW, height: plotH }, style: { fill: t.surface2 } }],
    tooltip: {
      trigger: 'item', confine: true, backgroundColor: t.surface, borderColor: t.line, textStyle: { color: t.ink, fontSize: 12 },
      formatter: p => p.seriesIndex === 0 ? `x ${(p.value[0] / W).toFixed(3)}–${((p.value[0] + 1) / W).toFixed(3)}<br>y ${(p.value[1] / H).toFixed(3)}–${((p.value[1] + 1) / H).toFixed(3)}<br><b>${p.value[2].toFixed(3)} track-s</b> · 占合计 ${total ? (p.value[2] / total * 100).toFixed(1) : 0}%` : 'ROI'
    },
    series: [
      {
        type: 'custom', data, encode: { x: 0, y: 1 }, clip: true,
        renderItem: (_, api) => {
          const x = api.value(0), y = api.value(1)
          const a = api.coord([x / W, y / H]), b = api.coord([(x + 1) / W, (y + 1) / H])
          return { type: 'rect', shape: { x: a[0], y: Math.min(a[1], b[1]), width: b[0] - a[0] + 0.4, height: Math.abs(b[1] - a[1]) + 0.4 }, style: { fill: api.visual('color') }, emphasis: { style: { stroke: t.ink, lineWidth: 1 } } }
        }
      },
      ...(props.roi ? [{ type: 'line', data: [...props.roi, props.roi[0]], showSymbol: false, silent: true, lineStyle: { color: t.warn, width: 1.5, type: [4, 3] }, z: 5 }] : [])
    ]
  }
})

function refresh() {
  frame = showFrame.value ? captureFrame(720) : null
  render()
}
watch(() => [props.heatmap, props.roi, props.aspect, showFrame.value], refresh)
onMounted(refresh)
</script>

<style scoped>
.figure { display: flex; flex-direction: column; gap: 6px; margin: 0; }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.cap-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.cap-row .note { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--text-caption); }
.frame-toggle { flex: none; white-space: nowrap; display: inline-flex; align-items: center; gap: 6px; font-size: var(--text-caption); color: var(--ink-3); cursor: pointer; }
.plot { width: 100%; aspect-ratio: 16 / 10; min-height: 160px; }
.compact .plot { aspect-ratio: 16 / 11; }
.foot { font-size: var(--text-caption); }
.fill { flex: 1; min-height: 0; }
.fill .plot { flex: 1; aspect-ratio: auto; min-height: 88px; }
</style>
