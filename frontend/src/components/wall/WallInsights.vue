<template>
  <aside class="wall-col" aria-label="运行与构成">
    <WallPanel code="A1" title="运行质量" :meta="run ? run.summary?.device || '' : ''">
      <dl v-if="run" class="facts">
        <div v-for="fact in facts" :key="fact.label" :class="{ wide: fact.wide }"><dt>{{ fact.label }}</dt><dd :class="{ mono: fact.mono, warn: fact.warn }" :title="fact.title">{{ fact.value }}</dd></div>
      </dl>
      <p v-else class="note">分析完成后显示设备、分辨率与追踪参数。</p>
    </WallPanel>

    <WallPanel code="A2" title="类别构成" meta="窗口内观测次数">
      <div v-if="classRows.length" class="bars">
        <div v-for="row in classRows" :key="row.id" class="bar-row">
          <span class="label">{{ row.label }}</span>
          <span class="bar"><span :style="{ width: `${row.share * 100}%` }" /></span>
          <span class="tnum count">{{ row.count.toLocaleString('zh-CN') }}</span>
          <span class="tnum share">{{ (row.share * 100).toFixed(1) }}%</span>
        </div>
      </div>
      <p v-else class="note">{{ analysis?.summary ? '窗口内没有观测。' : '正在计算…' }}</p>
    </WallPanel>

    <WallPanel code="A3" title="停留最长的 ID" class="grow" :meta="spans.length ? `共 ${spans.length} 个 ID · 按观测跨度` : ''">
      <ol v-if="ranked.length" class="rank" aria-label="点击跳到首次出现">
        <li v-for="(item, i) in ranked" :key="item.id">
          <button class="rank-row" :class="{ current: isOnScreen(item) }" :title="`跳到 #${item.id} 首次出现（${(item.first / 1000).toFixed(1)} s）`" @click="emit('seek', item.first / 1000)">
            <span class="pos tnum">{{ i + 1 }}</span>
            <span class="swatch" :style="{ background: color(item.id) }" />
            <span class="id tnum">#{{ item.id }}</span>
            <span class="lane" aria-hidden="true">
              <span v-for="(s, k) in item.spans" :key="k" class="seg" :style="segStyle(s, item.id)" />
              <span class="head" :style="{ left: `${pct(currentTime * 1000)}%` }" />
            </span>
            <span class="secs tnum">{{ item.seconds.toFixed(1) }} s</span>
          </button>
        </li>
      </ol>
      <p v-else class="note">{{ analysis?.run ? '正在加载全片轨迹…' : '分析完成后列出停留最长的 ID。' }}</p>
    </WallPanel>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import WallPanel from './WallPanel.vue'
import { trackColor } from '../../lib/palette'
import { longestStays } from '../../lib/tracks'
import { isDark } from '../../lib/theme'
import { shortId } from '../../lib/format'

const props = defineProps({ analysis: { type: Object, default: null }, currentTime: { type: Number, default: 0 } })
const emit = defineEmits(['seek'])
const run = computed(() => props.analysis?.run || null)
const spans = computed(() => props.analysis?.overview?.spans || [])
const ranked = computed(() => longestStays(spans.value, 30))
const durationMs = computed(() => (props.analysis?.duration || 1) * 1000)
const pct = ms => Math.min(100, Math.max(0, (ms / durationMs.value) * 100))
const color = id => trackColor(id, isDark.value ? 'video' : 'paper')
const segStyle = (s, id) => ({ left: `${pct(s.start)}%`, width: `max(2px, ${pct(s.end) - pct(s.start)}%)`, background: color(id) })
const isOnScreen = item => { const t = props.currentTime * 1000; return item.spans.some(s => t >= s.start && t <= s.end) }

const facts = computed(() => {
  const r = run.value
  if (!r) return []
  const s = r.summary || {}, cfg = r.config_snapshot.settings || {}
  const seconds = s.frame_count && s.fps ? s.frame_count / s.fps : null
  return [
    { label: '模型', value: r.config_snapshot.models.fish, mono: true, wide: true },
    { label: '权重', value: shortId(r.config_snapshot.model_sha256), mono: true, title: r.config_snapshot.model_sha256 },
    { label: '分辨率', value: s.width ? `${s.width}×${s.height}` : '—' },
    { label: '时长', value: seconds ? `${seconds.toFixed(1)} s` : '—' },
    { label: '帧数', value: s.frame_count?.toLocaleString('zh-CN') ?? '—' },
    { label: '帧率', value: s.fps ? `${s.fps.toFixed(1)} fps` : '—' },
    { label: '处理速度', value: s.processed_fps ? `${s.processed_fps.toFixed(1)} 帧/秒` : '—' },
    { label: '置信度阈值', value: cfg.confidence_threshold ?? '—' },
    { label: 'IoU 阈值', value: cfg.iou_threshold ?? '—' },
    { label: '输入尺寸', value: cfg.imgsz ? `${cfg.imgsz} px` : '—' },
    { label: '断轨容差', value: cfg.allowed_gap_seconds != null ? `${cfg.allowed_gap_seconds} s` : '—' },
    { label: '时间戳回退', value: s.timestamp_fallback_frames != null ? `${s.timestamp_fallback_frames} 帧` : '—', warn: s.timestamp_fallback_frames > 0 },
    { label: '镜头切换', value: cfg.scene_cut_frames?.length ? `${cfg.scene_cut_frames.length} 处已声明` : '未声明' }
  ]
})

const classRows = computed(() => {
  const counts = props.analysis?.summary?.class_observation_counts || {}
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  return Object.entries(counts).map(([id, count]) => ({ id, count, label: props.analysis.labels?.[id] ?? `类别 ${id}`, share: total ? count / total : 0 })).sort((a, b) => b.count - a.count)
})
</script>

<style scoped>
.wall-col { display: flex; flex-direction: column; gap: 10px; height: 100%; min-height: 0; min-width: 0; }
.grow { flex: 1; }
.facts { container-type: inline-size; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 12px; }
.facts > div { display: flex; justify-content: space-between; gap: 8px; min-width: 0; font-size: var(--text-small); }
.facts > div.wide { grid-column: 1 / -1; }
.facts dt { flex: none; color: var(--ink-3); }
.facts dd { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: end; font-variant-numeric: tabular-nums; }
.facts dd.warn { color: var(--warn); }
/* Narrow columns (1280-wide walls) keep both fact columns by stepping down one text size. */
@container (max-width: 250px) { .facts > div { gap: 4px; font-size: var(--text-caption); } }
.bars { display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: grid; grid-template-columns: minmax(0, 64px) 1fr auto 44px; gap: 10px; align-items: center; font-size: var(--text-small); }
.label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; }
.bar > span { display: block; height: 100%; border-radius: 3px; background: var(--accent); }
.share { text-align: end; color: var(--ink-3); font-size: var(--text-caption); }
.grow :deep(.panel-body) { padding: 4px 6px 6px; }
.rank { flex: 1; min-height: 0; overflow-y: auto; list-style: none; margin: 0; padding: 0; mask-image: linear-gradient(180deg, #000 calc(100% - 24px), transparent); scrollbar-width: thin; }
.rank-row { display: grid; grid-template-columns: 18px 8px 44px minmax(0, 1fr) 46px; gap: 8px; align-items: center; width: 100%; height: 26px; padding: 0 6px; border: 0; border-radius: var(--radius-sm); background: none; font: inherit; font-size: var(--text-small); color: var(--ink-2); cursor: pointer; text-align: start; transition: background-color 120ms var(--ease); }
.rank-row:hover { background: var(--surface-2); color: var(--ink); }
.rank-row.current { color: var(--ink); }
.rank-row.current .id { color: var(--accent); }
.pos { font-size: var(--text-caption); color: var(--ink-3); text-align: end; }
.swatch { width: 8px; height: 8px; border-radius: 2px; }
.lane { position: relative; height: 10px; border-radius: 2px; background: var(--surface-2); overflow: hidden; }
.seg { position: absolute; top: 2px; bottom: 2px; border-radius: 1px; opacity: 0.9; }
.head { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--ink); opacity: 0.55; }
.secs { text-align: end; }
@media (max-width: 1200px) {
  .wall-col { flex-direction: row; height: auto; }
  .wall-col > * { flex: 1; }
  .rank { max-height: 240px; }
}
@media (max-width: 900px) { .wall-col { flex-direction: column; } }
</style>
