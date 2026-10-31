<template>
  <aside class="wall-side" aria-label="分析证据">
    <template v-if="analysis?.run">
      <section class="card grow">
        <HeatmapFigure v-if="analysis.heatmap" :heatmap="analysis.heatmap" :roi="analysis.roi" :aspect="analysis.aspect" fill />
        <p v-else class="note">{{ analysis.run.status === 'completed' ? '正在计算热图…' : '分析完成后显示热图。' }}</p>
      </section>
      <section class="card grow">
        <TrajectoryFigure v-if="analysis.overview" :spans="analysis.overview.spans" :window="analysis.window" :roi="analysis.roi" :aspect="analysis.aspect" :truncated="analysis.overview.truncated" fill />
        <p v-else class="note">{{ analysis.run.status === 'completed' ? '正在加载轨迹…' : '分析完成后显示轨迹图。' }}</p>
      </section>
      <section v-if="classRows.length" class="card">
        <h3>类别观测次数</h3>
        <div v-for="row in classRows" :key="row.id" class="bar-row">
          <span class="truncate">{{ row.label }}</span>
          <span class="bar"><span :style="{ width: `${row.share * 100}%` }" /></span>
          <span class="tnum">{{ row.count.toLocaleString('zh-CN') }}</span>
        </div>
      </section>
    </template>
    <section v-else class="card empty">
      <h3>还没有分析证据</h3>
      <p class="note">在工作台打开视频并完成一次分析后，这里显示停留热图、轨迹图与类别构成。</p>
      <button class="btn btn-sm" @click="emit('open-workspace')">前往工作台</button>
    </section>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import HeatmapFigure from './HeatmapFigure.vue'
import TrajectoryFigure from './TrajectoryFigure.vue'

const props = defineProps({ analysis: { type: Object, default: null } })
const emit = defineEmits(['open-workspace'])
const classRows = computed(() => {
  const counts = props.analysis?.summary?.class_observation_counts || {}
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  return Object.entries(counts).map(([id, count]) => ({ id, count, label: props.analysis.labels?.[id] ?? `类别 ${id}`, share: total ? count / total : 0 })).sort((a, b) => b.count - a.count)
})
</script>

<style scoped>
.wall-side { flex: 1; display: flex; flex-direction: column; gap: 12px; min-height: 0; overflow-y: auto; }
.grow { flex: 1; min-height: 0; }
.card { display: flex; flex-direction: column; gap: 8px; padding: 14px; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.empty { align-items: flex-start; }
.bar-row { display: grid; grid-template-columns: minmax(0, 88px) 1fr auto; gap: 10px; align-items: center; font-size: var(--text-small); }
.bar { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--ink-3); }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 900px) {
  .wall-side { overflow: visible; }
  .grow { flex: none; }
  .wall-side :deep(.plot) { flex: none; aspect-ratio: 16 / 10; }
}
</style>
