<template>
  <aside class="wall-col" aria-label="分析证据">
    <template v-if="analysis?.run">
      <WallPanel code="B1" title="停留热图" meta="画面位置 · 非海底真实地理密度" class="grow">
        <HeatmapFigure v-if="analysis.heatmap" :heatmap="analysis.heatmap" :roi="analysis.roi" :aspect="analysis.aspect" fill bare />
        <p v-else class="note">{{ analysis.run.status === 'completed' ? '正在计算热图…' : '分析完成后显示热图。' }}</p>
      </WallPanel>
      <WallPanel code="B2" title="轨迹" :meta="trajectoryMeta" class="grow">
        <TrajectoryFigure v-if="analysis.overview" :spans="analysis.overview.spans" :window="analysis.window" :roi="analysis.roi" :aspect="analysis.aspect" :truncated="analysis.overview.truncated" fill bare />
        <p v-else class="note">{{ analysis.run.status === 'completed' ? '正在加载轨迹…' : '分析完成后显示轨迹图。' }}</p>
      </WallPanel>
      <WallPanel code="B3" title="证据边界" :meta="`${limits.length} 项`">
        <ul class="limits">
          <li v-for="item in limits" :key="item.text" :class="{ warn: item.warn }"><component :is="item.warn ? IconAlertTriangle : IconInfoCircle" />{{ item.text }}</li>
        </ul>
      </WallPanel>
    </template>
    <WallPanel v-else code="B0" title="还没有分析证据">
      <p class="note">在工作台打开视频并完成一次分析后，这里显示停留热图、轨迹图与证据边界。</p>
      <button class="btn btn-sm start" @click="emit('open-workspace')">前往工作台</button>
    </WallPanel>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { IconAlertTriangle, IconInfoCircle } from '@tabler/icons-vue'
import HeatmapFigure from './HeatmapFigure.vue'
import TrajectoryFigure from './TrajectoryFigure.vue'
import WallPanel from './wall/WallPanel.vue'

const props = defineProps({ analysis: { type: Object, default: null } })
const emit = defineEmits(['open-workspace'])

const LIMITATIONS = {
  'Track IDs are not unique biological individuals': '轨迹 ID 不等于生物个体，遮挡后重现会计为新 ID',
  'Image-plane coordinates only': '仅有画面坐标，不是海底地理坐标',
  'No independent ground truth evaluation': '未经独立真值评估，不报告精度',
  'Undeclared scene cuts are not automatically detected': '未声明的镜头切换不会被自动识别'
}
const limits = computed(() => {
  const run = props.analysis?.run
  const motion = run?.config_snapshot.settings.camera_motion
  const items = (run?.summary?.limitations || []).map(text => ({ text: LIMITATIONS[text] || text }))
  if (motion !== 'fixed') items.unshift({ text: motion === 'moving' ? '移动机位：画面坐标随镜头漂移' : '镜头运动未声明：画面坐标可能随镜头漂移', warn: true })
  if (run?.summary?.timestamp_fallback_frames > 0) items.unshift({ text: `${run.summary.timestamp_fallback_frames} 帧缺少时间戳，按帧号推算`, warn: true })
  if (props.analysis?.overview?.truncated) items.unshift({ text: '全片轨迹超过显示预算，轨迹图未画全', warn: true })
  return items
})
const trajectoryMeta = computed(() => {
  const n = props.analysis?.overview?.spans?.length
  return n ? '空心起点 · 实心终点' : ''
})
</script>

<style scoped>
.wall-col { display: flex; flex-direction: column; gap: 10px; height: 100%; min-height: 0; min-width: 0; }
.grow { flex: 1; }
.grow :deep(.panel-body) { padding: 6px 8px 8px; }
.limits { display: flex; flex-direction: column; gap: 6px; list-style: none; margin: 0; padding: 0; }
.limits li { display: flex; gap: 8px; align-items: flex-start; font-size: var(--text-small); line-height: 1.45; color: var(--ink-2); }
.limits .tabler-icon { flex: none; --icon-size: 14px; margin-top: 2px; color: var(--ink-3); }
.limits li.warn, .limits li.warn .tabler-icon { color: var(--warn); }
.start { align-self: flex-start; margin-top: 10px; }
@media (max-width: 900px) {
  .wall-col { height: auto; }
  .grow { flex: none; }
  .grow :deep(.plot) { flex: none; aspect-ratio: 16 / 10; }
}
</style>
