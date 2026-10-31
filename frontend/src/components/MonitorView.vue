<template>
  <section class="wall-head" aria-label="鱼类活动监测">
    <div class="title-row">
      <div class="title">
        <h1>鱼类活动监测</h1>
        <p class="note" v-if="analysis?.run">
          <span class="truncate">{{ fileName }}</span>
          <span class="sep" />分析 <span class="mono">{{ shortId(analysis.runId) }}</span>
          <span class="sep" /><span class="mono">{{ analysis.run.config_snapshot.models.fish }}</span>
          <span class="sep" />更新于 <span class="tnum">{{ formatDateTime(analysis.run.updated_at) }}</span>
        </p>
        <p class="note" v-else>{{ fileName ? '等待分析结果' : '在工作台选择一个视频后，这里显示它的分析证据。' }}</p>
      </div>
      <div v-if="analysis?.run" class="layers" role="group" aria-label="画面图层">
        <button v-for="(title, key) in layerNames" :key="key" class="btn btn-sm" :class="{ 'is-on': analysis.layers[key] }" :aria-pressed="analysis.layers[key]" @click="emit('layer', key, !analysis.layers[key])">{{ title }}</button>
      </div>
    </div>

    <div v-if="analysis?.run" class="kpis">
      <div v-for="(meta, key) in metrics" :key="key" class="kpi" :class="{ missing: value(key) == null }">
        <span class="eyebrow">{{ meta.title }}</span>
        <strong class="tnum">{{ value(key) ?? 'N/A' }}</strong>
        <span class="note">{{ value(key) == null ? (MISSING_REASONS[analysis.summary?.metrics[key]?.reason] || (analysis.summary ? '—' : '正在计算')) : meta.unit }}</span>
      </div>
    </div>

    <div v-if="analysis?.run" class="notices">
      <span class="tag"><IconInfoCircle />鱼类画面位置热图 · 非海底真实地理密度</span>
      <span v-if="motion !== 'fixed'" class="tag tag-warn"><IconAlertTriangle />{{ motion === 'moving' ? '移动机位：画面坐标随镜头漂移' : '镜头运动未声明：画面坐标可能随镜头漂移' }}</span>
      <span class="tag">窗口 <span class="tnum">{{ windowText }}</span></span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { IconInfoCircle, IconAlertTriangle } from '@tabler/icons-vue'
import { metricValue, MISSING_REASONS, shortId, formatDateTime } from '../lib/format'

const props = defineProps({ analysis: { type: Object, default: null }, fileName: String })
const emit = defineEmits(['layer'])
const layerNames = { boxes: '检测框', tails: '尾迹', heatmap: '热图' }
const metrics = {
  observed_track_count: { title: '观测 ID 数', unit: '个 ID，非个体数', digits: 0 },
  tracked_observation_count: { title: '追踪观测次数', unit: '次', digits: 0 },
  track_seconds: { title: '累计停留', unit: 'track-s', digits: 1 },
  mean_confidence: { title: '平均置信度', unit: '模型输出，非准确率', digits: 3 },
  ap50: { title: '独立测试 AP50', unit: '', digits: 3 },
  coral_cover: { title: '珊瑚覆盖率', unit: '', digits: 3 }
}
const motion = computed(() => props.analysis?.run?.config_snapshot.settings.camera_motion || 'unknown')
const windowText = computed(() => {
  const w = props.analysis?.window || { start_ms: 0 }
  return `${(w.start_ms / 1000).toFixed(1)}–${w.end_ms == null ? '片尾' : `${(w.end_ms / 1000).toFixed(1)} s`}`
})
function value(key) { return metricValue(props.analysis?.summary?.metrics[key], metrics[key].digits) }
</script>

<style scoped>
.wall-head { display: flex; flex-direction: column; gap: 14px; padding: 4px 2px 0; }
.title-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.title { min-width: 0; }
h1 { font-size: var(--text-heading); font-weight: 600; letter-spacing: -0.01em; }
.title .note { display: flex; align-items: center; gap: 8px; margin-top: 2px; flex-wrap: wrap; }
.truncate { max-width: 32ch; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sep { width: 3px; height: 3px; border-radius: 50%; background: var(--ink-3); opacity: 0.6; }
.layers { display: flex; gap: 6px; }
.is-on { color: var(--accent); background: var(--accent-soft); box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--accent) 40%, transparent); }
.kpis { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 1px; border-radius: var(--radius-lg); overflow: hidden; background: var(--line); box-shadow: 0 0 0 1px var(--line); }
.kpi { display: flex; flex-direction: column; gap: 2px; padding: 12px 14px; background: var(--surface); min-width: 0; }
.kpi strong { font-size: var(--text-display); font-weight: 500; line-height: 1.1; letter-spacing: -0.02em; }
.kpi.missing strong { color: var(--ink-3); }
.kpi .note { font-size: var(--text-caption); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notices { display: flex; gap: 6px; flex-wrap: wrap; }
.notices .tabler-icon { --icon-size: 12px; }
@media (max-width: 1440px), (max-height: 820px) { .wall-head { gap: 10px; } .kpi { padding: 9px 12px; } .kpi strong { font-size: var(--text-figure); } }
@media (max-width: 1100px) { .kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
</style>
