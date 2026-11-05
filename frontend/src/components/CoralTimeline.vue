<template>
  <section class="strip" aria-label="珊瑚采样帧时间线">
    <header>
      <h3>珊瑚采样帧</h3>
      <span class="note tnum count">{{ frames.length }} 帧 · 每 {{ intervalMs / 1000 }} s · 柱高按全片珊瑚像素峰值 {{ peakText }}</span>
      <span class="note legend">
        <span class="key"><span class="swatch" :style="{ background: coralCss(1) }" />未白化</span>
        <span class="key"><span class="swatch" :style="{ background: coralCss(2) }" />白化</span>
        <span class="key"><span class="swatch mixed" />未分离背景</span>
      </span>
    </header>
    <div ref="stage" class="stage">
      <svg class="plot" :width="width" :height="H" aria-hidden="true">
        <defs><pattern id="coral-strip-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" class="hatch-bg" /><rect width="2" height="5" class="hatch-line" /></pattern></defs>
        <line :x1="PAD.left" :x2="width - PAD.right" :y1="H - 0.5" :y2="H - 0.5" class="base" />
        <g v-for="bar in bars" :key="bar.frame" :class="{ current: bar.index === currentIndex }">
          <rect v-if="!bar.separated" :x="bar.x" y="2" :width="bar.w" :height="H - 3" fill="url(#coral-strip-hatch)" />
          <template v-else>
            <rect :x="bar.x" :y="H - 1 - bar.coralH" :width="bar.w" :height="bar.coralH" :fill="coralCss(1, 0.85)" />
            <rect :x="bar.x" :y="H - 1 - bar.coralH" :width="bar.w" :height="bar.bleachedH" :fill="coralCss(2)" />
          </template>
          <rect v-if="bar.bleachedOnly" :x="bar.x" :y="H - 1 - bar.bleachedH" :width="bar.w" :height="bar.bleachedH" :fill="coralCss(2)" />
        </g>
        <rect v-if="currentBar" :x="currentBar.x - 1" y="0.5" :width="currentBar.w + 2" :height="H - 1" rx="2" class="ring" />
      </svg>
      <div
        class="overlay"
        role="slider"
        tabindex="0"
        aria-label="珊瑚采样帧定位"
        :aria-valuemin="1"
        :aria-valuemax="frames.length"
        :aria-valuenow="currentIndex + 1"
        :aria-valuetext="ariaValue"
        @pointermove="hover"
        @pointerleave="hoverIndex = -1"
        @click="seekHovered"
        @keydown="onKey"
      >
        <div class="playhead" :style="{ transform: `translateX(${x(currentTime)}px)` }" />
        <div v-if="hovered" class="tip" :class="{ flip: hovered.px > width / 2 }" :style="{ transform: `translateX(${hovered.px}px)` }">
          <span class="tnum">{{ (hovered.timestamp_ms / 1000).toFixed(1) }} s · 帧 {{ hovered.frame + 1 }}</span>
          <span v-if="hovered.background_separated" class="tnum">珊瑚 {{ share(hovered, 'coral') }} · 白化 {{ share(hovered, '2') }}</span>
          <span v-else class="tnum">未分离背景 · 白化 {{ share(hovered, '2') }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { coralCss } from '../lib/palette'
import { sampleAt } from '../lib/coralMasks'

// Shares the fish track timeline's horizontal padding so both time axes line up when stacked.
const props = defineProps({ frames: { type: Array, default: () => [] }, intervalMs: { type: Number, default: 2000 }, duration: { type: Number, default: null }, currentTime: { type: Number, default: 0 } })
const emit = defineEmits(['seek'])
const PAD = { left: 28, right: 10 }
const H = ref(30) // follows the stage height, which CSS lowers on short screens
const stage = ref(null), width = ref(0), hoverIndex = ref(-1)

const area = p => p.width * p.height
const coralShare = p => (p.pixel_counts['1'] + p.pixel_counts['2']) / area(p)
const share = (p, key) => { const v = key === 'coral' ? coralShare(p) : p.pixel_counts[key] / area(p); return `${(v * 100).toFixed(v >= 0.1 ? 1 : 2)}%` }
const span = computed(() => Math.max(props.duration || 0, ((props.frames.at(-1)?.timestamp_ms || 0) + props.intervalMs) / 1000, 1))
const plotWidth = computed(() => Math.max(1, width.value - PAD.left - PAD.right))
const x = t => PAD.left + Math.min(1, Math.max(0, t / span.value)) * plotWidth.value
const peak = computed(() => Math.max(1e-9, ...props.frames.filter(p => p.background_separated).map(coralShare), ...props.frames.map(p => p.pixel_counts['2'] / area(p))))
const peakText = computed(() => `${(peak.value * 100).toFixed(1)}%`)
const currentIndex = computed(() => {
  const i = sampleAt(props.frames, props.currentTime * 1000)
  return i >= 0 && props.currentTime * 1000 - props.frames[i].timestamp_ms < props.intervalMs ? i : -1
})
const bars = computed(() => props.frames.map((p, index) => {
  const x0 = x(p.timestamp_ms / 1000), x1 = x((p.timestamp_ms + props.intervalMs) / 1000)
  const scale = h => Math.max(h > 0 ? 1.5 : 0, h / peak.value * (H.value - 3))
  const coralH = p.background_separated ? scale(coralShare(p)) : 0, bleachedH = scale(p.pixel_counts['2'] / area(p))
  return { index, frame: p.frame, x: x0, w: Math.max(1, x1 - x0 - 1), separated: p.background_separated, coralH, bleachedH, bleachedOnly: !p.background_separated && bleachedH > 0 }
}))
const currentBar = computed(() => bars.value[currentIndex.value] || null)
const hovered = computed(() => {
  const p = props.frames[hoverIndex.value]
  return p ? { ...p, px: x(p.timestamp_ms / 1000) } : null
})
const ariaValue = computed(() => {
  const p = props.frames[currentIndex.value]
  if (!p) return '当前没有采样掩膜'
  return `${(p.timestamp_ms / 1000).toFixed(1)} 秒，${p.background_separated ? `珊瑚 ${share(p, 'coral')}，` : '未分离背景，'}白化 ${share(p, '2')}`
})

function hover(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const t = (event.clientX - rect.left - PAD.left) / plotWidth.value * span.value
  hoverIndex.value = t < 0 ? -1 : sampleAt(props.frames, t * 1000)
}
function seekHovered() { if (hovered.value) emit('seek', hovered.value.timestamp_ms / 1000) }
function onKey(event) {
  const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key]
  if (!step || !props.frames.length) return
  event.preventDefault()
  const base = currentIndex.value < 0 ? sampleAt(props.frames, props.currentTime * 1000) : currentIndex.value
  const next = props.frames[Math.min(props.frames.length - 1, Math.max(0, base + step))]
  emit('seek', next.timestamp_ms / 1000)
}

let observer
onMounted(() => {
  observer = new ResizeObserver(entries => { const r = entries[0].contentRect; width.value = Math.round(r.width); H.value = Math.round(r.height) || 30 })
  observer.observe(stage.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<style scoped>
.strip { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.legend { display: inline-flex; align-items: center; gap: 10px; margin-inline-start: auto; font-size: var(--text-caption); }
.key { display: inline-flex; align-items: center; gap: 5px; }
.swatch { width: 10px; height: 8px; border-radius: 2px; }
.swatch.mixed { background: repeating-linear-gradient(135deg, var(--surface-3) 0 3px, color-mix(in oklch, var(--ink-3) 45%, var(--surface-3)) 3px 5px); }
.hatch-bg { fill: var(--surface-3); }
.hatch-line { fill: color-mix(in oklch, var(--ink-3) 45%, var(--surface-3)); }
.stage { position: relative; height: 30px; }
.plot { position: absolute; inset: 0; overflow: visible; }
.base { stroke: var(--line); }
.ring { fill: none; stroke: var(--ink); stroke-width: 1.5; }
.overlay { position: absolute; inset: 0; cursor: pointer; outline-offset: 2px; border-radius: 2px; }
.playhead { position: absolute; top: -2px; bottom: -2px; left: 0; width: 1px; background: var(--accent); pointer-events: none; will-change: transform; }
.tip { position: absolute; bottom: calc(100% + 6px); left: 0; display: flex; flex-direction: column; gap: 1px; padding: 5px 8px; margin-inline-start: 8px; border-radius: var(--radius-sm); font-size: var(--text-caption); color: var(--ink); background: var(--surface-3); box-shadow: 0 0 0 1px var(--line), 0 4px 12px oklch(0 0 0 / 0.18); white-space: nowrap; pointer-events: none; z-index: 3; }
.tip.flip { translate: calc(-100% - 16px) 0; }
/* Short screens give the video the height; the legend and bars stay. */
@media (max-height: 800px) { .count { display: none; } .stage { height: 22px; } }
</style>
