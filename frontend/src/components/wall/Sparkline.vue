<template>
  <svg class="spark" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" aria-hidden="true">
    <rect v-if="band" :x="band[0]" y="0" :width="Math.max(0.5, band[1] - band[0])" :height="H" class="band" />
    <path :d="area" class="area" />
    <path :d="line" class="line" vector-effect="non-scaling-stroke" />
    <line v-if="head != null" :x1="head" :x2="head" y1="0" :y2="H" class="head" vector-effect="non-scaling-stroke" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

// Inline SVG keeps KPI trends off the ECharts chunk; values are [x, y] pairs on a shared x domain.
const props = defineProps({ points: { type: Array, default: () => [] }, domain: { type: Array, default: () => [0, 1] }, playhead: Number, window: Array })
const W = 120, H = 28
const sx = x => ((x - props.domain[0]) / ((props.domain[1] - props.domain[0]) || 1)) * W
const yMax = computed(() => Math.max(1e-9, ...props.points.map(p => p[1])))
const sy = y => H - 1 - (y / yMax.value) * (H - 3)
const line = computed(() => props.points.map((p, i) => `${i ? 'L' : 'M'}${sx(p[0]).toFixed(2)},${sy(p[1]).toFixed(2)}`).join(''))
const area = computed(() => props.points.length ? `${line.value}L${sx(props.points.at(-1)[0]).toFixed(2)},${H}L${sx(props.points[0][0]).toFixed(2)},${H}Z` : '')
const head = computed(() => props.playhead == null ? null : Math.min(W, Math.max(0, sx(props.playhead))))
const band = computed(() => props.window ? [sx(props.window[0]), sx(props.window[1])] : null)
</script>

<style scoped>
.spark { display: block; width: 100%; height: 28px; overflow: visible; }
.line { fill: none; stroke: var(--accent); stroke-width: 1.5; stroke-linejoin: round; }
.area { fill: var(--accent); opacity: 0.12; }
.head { stroke: var(--ink); stroke-width: 1; opacity: 0.7; }
.band { fill: var(--ink); opacity: 0.06; }
</style>
