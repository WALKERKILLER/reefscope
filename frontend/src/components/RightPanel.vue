<template>
  <aside class="w-full flex flex-col h-full z-10 overflow-hidden bg-m3-surface/50 border-l border-m3-outline-variant/30 transition-colors duration-200">
    <!-- Panel Header -->
    <div class="px-4 py-3 shrink-0 flex items-center justify-between border-b border-m3-outline-variant/30 text-[11px] uppercase tracking-widest text-m3-on-surface-variant font-medium">
      <span>指标与时间轴</span>
    </div>

    <div class="flex-1 flex flex-col min-h-0">
      <!-- Live Stats -->
      <div
        class="overflow-y-auto p-4 shrink-0"
        :style="{ height: `${topPanelHeight}%` }"
      >
        <h3 class="text-[11px] font-medium text-m3-on-surface-variant mb-3 uppercase tracking-widest">已识别实体 ({{ boxes.length }})</h3>
        <div class="space-y-1.5 mt-1">
          <div v-if="stats.length > 0">
            <div
              v-for="(stat, idx) in stats"
              :key="idx"
              class="flex justify-between items-center text-[12px] px-3 py-2 rounded-lg hover:bg-m3-surface-container cursor-pointer transition-colors"
            >
              <span class="text-m3-on-surface">{{ stat.name }}</span>
              <span class="text-m3-on-primary-container font-mono bg-m3-primary/10 px-2 py-0.5 rounded text-[11px] font-medium">{{ stat.val }}</span>
            </div>
          </div>
          <div v-else class="text-[12px] text-m3-on-surface-variant opacity-70 py-4">等待数据流...</div>
        </div>
      </div>

      <!-- Divider -->
      <div
        ref="separatorRef"
        class="h-1.5 w-full shrink-0 cursor-row-resize relative group"
        @mousedown="startResize"
      >
        <div class="absolute top-1/2 left-0 right-0 h-px -translate-y-1/2 bg-m3-outline-variant/30 group-hover:bg-m3-primary transition-colors"></div>
      </div>

      <!-- Timeline -->
      <div ref="timelineListRef" class="overflow-y-auto p-4 flex-1 min-h-0">
        <h3 class="text-[11px] font-medium text-m3-on-surface-variant mb-3 uppercase tracking-widest leading-none">事件日志</h3>
        <div class="flex-1 pr-1 space-y-1.5">
          <div
            v-for="box in sortedBoxes"
            :key="box.id"
            :ref="(el) => setTimelineItemRef(box.id, el)"
            @click="$emit('timeline-click', box.start_time)"
            class="flex flex-col py-2 px-3 cursor-pointer rounded-lg transition-colors border"
            :class="[
              isActive(box)
                ? (box.type === 'alert' ? 'bg-m3-error/10 border-m3-error/20' : 'bg-m3-primary/10 border-m3-primary/20')
                : 'border-transparent hover:bg-m3-surface-container'
            ]"
          >
            <div class="flex justify-between items-center mb-1">
              <span class="text-[11px] font-mono tracking-wider" :class="isActive(box) ? 'text-m3-on-surface opacity-90' : 'text-m3-on-surface-variant'">
                {{ formatTime(box.start_time) }}
              </span>
              <span
                class="text-[10px] px-1.5 py-0.5 rounded tracking-wide"
                :class="confidenceClass(box)"
              >
                {{ (box.confidence * 100).toFixed(0) }}%
              </span>
            </div>
            <div class="text-[12px] truncate" :class="isActive(box) ? 'text-m3-on-surface' : 'text-m3-on-surface-variant'">
              {{ box.type === 'alert' ? '\u26A0\uFE0F ' : '' }}{{ box.label }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  boxes: {
    type: Array,
    default: () => []
  },
  currentTime: {
    type: Number,
    default: 0
  }
})

defineEmits(['timeline-click'])

const topPanelHeight = ref(30)
const separatorRef = ref(null)
const timelineListRef = ref(null)
const timelineItemRefs = new Map()
let stopResizeListener = null
let lastActiveTimelineId = null

const stats = computed(() => {
  const counts = {}
  props.boxes.forEach(b => {
    counts[b.label] = (counts[b.label] || 0) + 1
  })
  return Object.entries(counts).map(([name, val]) => ({ name, val }))
})

const sortedBoxes = computed(() => {
  return [...props.boxes].sort((a, b) => a.start_time - b.start_time)
})

const currentBucket = computed(() => Math.round((props.currentTime || 0) * 5) / 5)

function setTimelineItemRef(id, el) {
  if (el) {
    timelineItemRefs.set(String(id), el)
    return
  }
  timelineItemRefs.delete(String(id))
}

function isActive(box) {
  return currentBucket.value >= box.start_time && currentBucket.value <= box.end_time
}

function scrollActiveTimelineItemIntoView() {
  const activeBox = sortedBoxes.value.find(box => isActive(box))
  const activeElement = activeBox ? timelineItemRefs.get(String(activeBox.id)) : null
  const activeId = activeBox ? String(activeBox.id) : null
  if (!activeElement || activeId === lastActiveTimelineId) return

  lastActiveTimelineId = activeId

  activeElement.scrollIntoView({
    block: 'nearest',
    inline: 'nearest',
    behavior: 'auto'
  })
}

watch(currentBucket, () => {
  nextTick(() => {
    scrollActiveTimelineItemIntoView()
  })
}, { immediate: true })

function confidenceClass(box) {
  const isActiveBox = isActive(box)
  if (box.type === 'alert') return 'bg-m3-error/20 text-m3-error'
  if (isActiveBox) return 'bg-m3-primary/20 text-m3-primary'
  return 'bg-m3-success/20 text-m3-success'
}

function formatTime(sec) {
  if (!sec || isNaN(sec)) return '00:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function stopResize() {
  if (stopResizeListener) {
    stopResizeListener()
    stopResizeListener = null
  }
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

function startResize(event) {
  const aside = event.currentTarget?.parentElement
  if (!aside) return

  const rect = aside.getBoundingClientRect()
  const handleMouseMove = (moveEvent) => {
    const nextPercent = ((moveEvent.clientY - rect.top) / rect.height) * 100
    topPanelHeight.value = clamp(nextPercent, 10, 70)
  }

  const handleMouseUp = () => {
    stopResize()
    window.removeEventListener('mousemove', handleMouseMove)
    window.removeEventListener('mouseup', handleMouseUp)
  }

  stopResize()
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'row-resize'
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('mouseup', handleMouseUp)
  stopResizeListener = () => {
    window.removeEventListener('mousemove', handleMouseMove)
    window.removeEventListener('mouseup', handleMouseUp)
  }
}

onBeforeUnmount(() => {
  stopResize()
  timelineItemRefs.clear()
  lastActiveTimelineId = null
})
</script>

<style scoped>
</style>
