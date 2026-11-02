<template>
  <section class="curves" aria-label="逐 epoch 训练与验证曲线">
    <div v-if="!rows.length" class="empty">
      <p class="empty-title">没有逐 epoch 数值</p>
      <p class="note">只从 results.csv 读取曲线，不从截图估算 loss 或精度。</p>
    </div>
    <template v-else>
      <div ref="host" class="plot" role="img" :aria-label="ariaText" />
      <p class="caption note">横轴为 epoch。精度来自训练期验证集，不是独立测试结果。拖动下方滑块，或按住 Ctrl 滚动来缩放。</p>
      <details class="raw">
        <summary>原始数值 <span class="tnum">{{ rows.length }}</span> 个 epoch</summary>
        <div class="table-wrap">
          <table class="table tnum">
            <thead>
              <tr><th>epoch</th><th v-for="col in columns" :key="col.key">{{ col.label }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.epoch" :class="{ best: bestEpochs.has(row.epoch) }">
                <td>{{ row.epoch }}<span v-if="bestEpochs.has(row.epoch)" class="tag tag-accent">{{ bestEpochs.get(row.epoch) }}</span></td>
                <td v-for="col in columns" :key="col.key" :class="{ missing: row[col.key] == null }">{{ row[col.key] ?? 'N/A' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </template>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useChart } from '../charts/useChart'

const props = defineProps({ rows: { type: Array, default: () => [] }, selection: { type: Object, default: () => ({}) } })

// One panel per measure on a shared epoch axis: never two y-scales in one panel.
const PANELS = [
  { title: '验证 mAP', kind: 'metric', series: [{ label: 'mAP50', key: 'metrics/mAP50(B)', best: 'best_map50_epoch' }, { label: 'mAP50-95', key: 'metrics/mAP50-95(B)', best: 'best_map50_95_epoch' }] },
  { title: '验证 Precision / Recall', kind: 'metric', series: [{ label: 'Precision', key: 'metrics/precision(B)' }, { label: 'Recall', key: 'metrics/recall(B)' }] },
  { title: 'box loss', kind: 'loss', series: [{ label: '训练', key: 'train/box_loss' }, { label: '验证', key: 'val/box_loss', dashed: true }] },
  { title: 'cls loss', kind: 'loss', series: [{ label: '训练', key: 'train/cls_loss' }, { label: '验证', key: 'val/cls_loss', dashed: true }] },
  { title: 'dfl loss', kind: 'loss', series: [{ label: '训练', key: 'train/dfl_loss' }, { label: '验证', key: 'val/dfl_loss', dashed: true }] }
]
const has = key => props.rows.some(r => r[key] != null)
const panels = computed(() => PANELS.map(p => ({ ...p, series: p.series.filter(s => has(s.key)) })).filter(p => p.series.length))
const columns = computed(() => panels.value.flatMap(p => p.series.map(s => ({ key: s.key, label: p.kind === 'loss' ? `${p.title.replace(' loss', '')} ${s.label}` : s.label }))))
const byEpoch = computed(() => new Map(props.rows.map(r => [r.epoch, r])))
const bestEpochs = computed(() => {
  const map = new Map()
  for (const [key, label] of [['best_map50_epoch', '最高 mAP50'], ['best_map50_95_epoch', '最高 mAP50-95']]) {
    const epoch = props.selection?.[key]
    if (epoch != null) map.set(epoch, map.has(epoch) ? `${map.get(epoch)} · ${label.slice(3)}` : label)
  }
  return map
})
const ariaText = computed(() => {
  const best = props.selection?.best_map50_epoch
  return `训练曲线，${props.rows.length} 个 epoch${best != null ? `，验证 mAP50 最高在 epoch ${best}` : ''}。数值见下方原始数值表。`
})

const host = ref(null)
let zoom = { start: 0, end: 100 }, listening = false
const measure = (() => { const ctx = document.createElement('canvas').getContext('2d'); return (text, size) => { ctx.font = `${size}px "Inter Variable", system-ui, sans-serif`; return ctx.measureText(text).width } })()
const tick = v => (v !== 0 && Math.abs(v) < 0.01 ? v.toExponential(1) : String(+v.toFixed(3)))
const soft = (rgb, a) => rgb.replace('rgb(', 'rgba(').replace(')', `, ${a})`)

const { render, chart } = useChart(host, (t, { width, height }) => {
  const list = panels.value
  if (!list.length) return null
  const narrow = width < 640
  const grid = narrow ? list.map(p => [p]) : [list.filter(p => p.kind === 'metric'), list.filter(p => p.kind === 'loss')].filter(r => r.length)
  const pad = { left: 46, right: 10, head: 26, axis: 22, colGap: 24, rowGap: 16, slider: 34 }
  const rowH = (height - pad.slider - (grid.length - 1) * pad.rowGap) / grid.length
  const grids = [], xAxis = [], yAxis = [], series = [], graphic = []
  const first = props.rows[0].epoch, last = props.rows.at(-1).epoch
  grid.forEach((row, r) => {
    const colW = (width - (row.length - 1) * pad.colGap) / row.length
    row.forEach((panel, c) => {
      const i = grids.length, x0 = c * (colW + pad.colGap), y0 = r * (rowH + pad.rowGap)
      grids.push({ left: x0 + pad.left, top: y0 + pad.head, width: colW - pad.left - pad.right, height: rowH - pad.head - pad.axis })
      xAxis.push({ gridIndex: i, type: 'value', min: first, max: last, minInterval: 1, axisLine: { lineStyle: { color: t.lineStrong } }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { color: t.ink3, fontSize: 11, hideOverlap: true } })
      yAxis.push({ gridIndex: i, type: 'value', scale: true, splitNumber: 3, axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: t.line } }, axisLabel: { color: t.ink3, fontSize: 11, formatter: tick } })
      graphic.push({ type: 'text', left: x0 + pad.left, top: y0 + 4, silent: true, style: { text: panel.title, fill: t.ink2, font: `600 12px "Inter Variable", system-ui, sans-serif` } })
      let right = x0 + colW - pad.right
      for (let j = panel.series.length - 1; j >= 0; j--) {
        const s = panel.series[j], w = measure(s.label, 11)
        right -= w
        graphic.push({ type: 'text', left: right, top: y0 + 5, silent: true, style: { text: s.label, fill: t.ink3, font: `11px "Inter Variable", system-ui, sans-serif` } })
        right -= 20
        graphic.push({ type: 'line', left: right, top: y0 + 11, silent: true, shape: { x1: 0, y1: 0, x2: 14, y2: 0 }, style: { stroke: t.series[j], lineWidth: 2, lineDash: s.dashed ? [4, 3] : null } })
        right -= 12
      }
      panel.series.forEach((s, j) => {
        const bestEpoch = s.best ? props.selection?.[s.best] : null
        const bestRow = bestEpoch != null ? byEpoch.value.get(bestEpoch) : null
        series.push({
          type: 'line', name: `${panel.title} · ${s.label}`, xAxisIndex: i, yAxisIndex: i, showSymbol: false, connectNulls: false, sampling: 'lttb', z: 3 - j,
          data: props.rows.map(row => [row.epoch, row[s.key] ?? null]),
          lineStyle: { width: 2, color: t.series[j], type: s.dashed ? [4, 3] : 'solid' }, itemStyle: { color: t.series[j] }, emphasis: { disabled: true },
          markPoint: bestRow?.[s.key] != null ? { silent: true, symbol: 'circle', symbolSize: 8, itemStyle: { color: t.series[j], borderColor: t.surface, borderWidth: 2 }, label: { show: true, position: 'top', distance: 4, formatter: `e${bestEpoch}`, color: t.ink2, fontSize: 11 }, data: [{ coord: [bestEpoch, bestRow[s.key]] }] } : undefined
        })
      })
    })
  })
  const all = grids.map((_, i) => i)
  return {
    animation: false,
    aria: { enabled: true, label: { description: ariaText.value } },
    grid: grids, xAxis, yAxis, series, graphic,
    axisPointer: { link: [{ xAxisIndex: 'all' }], lineStyle: { color: t.lineStrong }, label: { show: false } },
    tooltip: {
      trigger: 'axis', confine: true, backgroundColor: t.surface, borderColor: t.line, padding: [8, 10], textStyle: { color: t.ink, fontSize: 12 },
      formatter: params => {
        const epoch = params[0]?.value?.[0], row = byEpoch.value.get(epoch)
        if (!row) return ''
        const lines = list.map(p => `<div class="tt-row"><span class="tt-key">${p.title}</span>${p.series.map((s, j) => `<span class="tt-val"><i style="background:${t.series[j]}"></i>${s.label} ${row[s.key] ?? 'N/A'}</span>`).join('')}</div>`)
        return `<div class="tt"><strong>epoch ${epoch}</strong>${lines.join('')}</div>`
      }
    },
    dataZoom: [
      { type: 'slider', xAxisIndex: all, bottom: 4, height: 18, left: pad.left + 24, right: 40, start: zoom.start, end: zoom.end, brushSelect: false, borderColor: t.line, backgroundColor: 'transparent', fillerColor: soft(t.accent, 0.12), handleStyle: { color: t.surface, borderColor: t.lineStrong }, moveHandleSize: 0, textStyle: { color: t.ink3, fontSize: 11 }, labelFormatter: v => String(Math.round(v)), dataBackground: { lineStyle: { color: t.ink3, opacity: 0.5 }, areaStyle: { opacity: 0 } }, selectedDataBackground: { lineStyle: { color: t.accent }, areaStyle: { opacity: 0 } } },
      { type: 'inside', xAxisIndex: all, zoomOnMouseWheel: 'ctrl', moveOnMouseWheel: false, moveOnMouseMove: true, start: zoom.start, end: zoom.end }
    ]
  }
})

async function draw() {
  await nextTick()
  await render()
  const instance = chart()
  if (instance && !listening) {
    listening = true
    instance.on('datazoom', () => { const dz = instance.getOption().dataZoom?.[0]; if (dz) zoom = { start: dz.start, end: dz.end } })
  }
}
watch(() => [props.rows, props.selection], () => { zoom = { start: 0, end: 100 }; draw() }, { immediate: true })
</script>

<style scoped>
.curves { display: flex; flex-direction: column; gap: 8px; container-type: inline-size; }
.plot { width: 100%; height: 460px; }
@container (max-width: 639px) { .plot { height: 940px; } }
.caption { text-wrap: pretty; }
.empty { padding: 20px 0; }
.empty-title { font-weight: 500; margin-bottom: 4px; }
.raw summary { cursor: pointer; width: fit-content; font-size: var(--text-small); color: var(--ink-2); }
.raw summary:hover { color: var(--ink); }
.table-wrap { margin-top: 10px; max-height: 360px; overflow: auto; border-radius: var(--radius); box-shadow: 0 0 0 1px var(--line); }
.table { width: 100%; border-collapse: collapse; font-size: var(--text-small); white-space: nowrap; }
th { position: sticky; top: 0; z-index: 1; height: 30px; padding: 0 10px; text-align: end; font-size: var(--text-caption); font-weight: 500; color: var(--ink-3); background: var(--surface-2); }
td { height: 28px; padding: 0 10px; text-align: end; box-shadow: inset 0 1px 0 var(--line); }
th:first-child, td:first-child { text-align: start; }
td .tag { margin-inline-start: 6px; }
tr.best td { background: var(--accent-soft); }
td.missing { color: var(--ink-3); }
:deep(.tt) { display: grid; gap: 4px; min-width: 220px; }
:deep(.tt strong) { font-weight: 600; margin-bottom: 2px; }
:deep(.tt-row) { display: flex; gap: 10px; align-items: baseline; font-variant-numeric: tabular-nums; }
:deep(.tt-key) { min-width: 9em; color: var(--ink-3); font-size: 11px; }
:deep(.tt-val) { display: inline-flex; align-items: center; gap: 4px; }
:deep(.tt-val i) { width: 8px; height: 2px; border-radius: 1px; }
</style>
