<template>
  <section class="viewer" aria-labelledby="observation-report-title">
    <div class="viewer-bar">
      <button class="btn btn-ghost" @click="emit('back')"><IconArrowLeft />返回观测点</button>
      <span class="spacer" />
      <button class="btn" :disabled="downloading" @click="download"><IconDownload />{{ downloading ? '正在下载…' : '下载 Markdown' }}</button>
      <a class="btn" :href="observationPrintUrl(report.report_id)" target="_blank" rel="noopener"><IconPrinter />打开打印版</a>
    </div>

    <header class="viewer-head">
      <h2 id="observation-report-title">{{ report.title }}</h2>
      <div class="status-line">
        <span class="tag tag-warn"><IconEye />待人工审阅</span>
        <span class="tag" :class="AGENT_STATUS[agent.status].tone">{{ AGENT_STATUS[agent.status].label }}</span>
        <span class="note">生成于 <span class="tnum">{{ formatDateTime(report.created_at) }}</span> · <span class="mono">{{ shortId(report.report_id) }}</span></span>
      </div>
    </header>

    <div v-if="kpis.length" class="ui-kpis kpis" :style="{ '--kpi-cols': Math.min(kpis.length, 4) }">
      <div v-for="item in kpis" :key="item.key" class="ui-kpi" :class="{ missing: item.value == null }">
        <span class="eyebrow">{{ item.title }}</span>
        <strong class="tnum">{{ item.value == null ? 'N/A' : item.display }}</strong>
        <span class="note">{{ item.value == null ? item.reason_text : item.sub }}</span>
      </div>
    </div>

    <div class="ui-card">
      <div class="ui-report">
        <nav class="ui-toc" aria-label="报告章节">
          <ol>
            <li v-for="(section, index) in report.sections" :key="section.key"><a :href="`#obs-${section.key}`" @click.prevent="jump(section.key)"><span class="tnum">{{ index + 1 }}</span>{{ section.title }}</a></li>
          </ol>
        </nav>
        <div class="ui-chapters">
          <section v-for="(section, index) in report.sections" :id="`obs-${section.key}`" :key="section.key" class="ui-chapter">
            <h3><span class="num tnum">{{ String(index + 1).padStart(2, '0') }}</span>{{ section.title }}</h3>

            <template v-if="section.key === 'agent' && agent.status === 'generated'">
              <p class="note">以下内容由语言模型撰写，需要人工审阅。带下划虚线的数值由平台按指标填入；<mark class="legend">黄色标记</mark>的数字是模型自行写出的，没有经过核对。</p>
              <div v-if="auditNotes.length" class="ui-banner ui-banner-warn"><IconAlertTriangle /><span>{{ auditNotes.join(' ') }}</span></div>
              <p class="prose"><ReportSegments :parts="agent.narrative.summary" :metrics="metrics" /></p>
              <template v-for="group in narrativeGroups" :key="group.key">
                <h4>{{ group.title }}</h4>
                <ul class="ui-bullets"><li v-for="(entry, i) in group.items" :key="i"><ReportSegments :parts="entry" :metrics="metrics" /></li></ul>
              </template>
              <p class="note meta">{{ agentMeta }}</p>
            </template>
            <template v-else-if="section.key === 'agent' && agent.status === 'failed'">
              <div class="ui-banner ui-banner-warn"><IconAlertTriangle /><span>AI 解读未生成：{{ agent.error_text || agent.error_code }}上文的确定性结果不受影响。</span></div>
              <p class="note meta">{{ agentMeta }}</p>
            </template>
            <template v-else-if="section.key === 'references'">
              <ol class="refs">
                <li v-for="item in report.references" :id="`ref-${item.id}`" :key="item.id">
                  <span class="mono ref-id">[{{ item.id }}]</span>
                  <span>{{ item.authors }} ({{ item.year }}). <a class="ui-link wrap" :href="item.url" target="_blank" rel="noopener noreferrer">{{ item.title }}</a></span>
                </li>
              </ol>
            </template>
            <template v-else>
              <p v-for="paragraph in section.paragraphs" :key="paragraph" class="prose">
                <template v-for="(part, i) in cite(paragraph)" :key="i"><a v-if="part.ref" class="ui-link" :href="`#ref-${part.ref}`">[{{ part.ref }}]</a><template v-else>{{ part.text }}</template></template>
              </p>
              <dl v-if="section.rows.length" class="ui-rows">
                <div v-for="(row, i) in section.rows" :key="i">
                  <dt>{{ row[0] }}</dt>
                  <dd :class="{ missing: section.key === 'missing' || String(row[1]).startsWith('N/A') }">{{ row[1] }}</dd>
                </div>
              </dl>
            </template>
          </section>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { IconAlertTriangle, IconArrowLeft, IconDownload, IconEye, IconPrinter } from '@tabler/icons-vue'
import ReportSegments from './ReportSegments.vue'
import { downloadObservationReport, observationPrintUrl } from '../api'
import { formatDateTime, shortId } from '../lib/format'
import { toast } from '../lib/toast'

const props = defineProps({ report: { type: Object, required: true } })
const emit = defineEmits(['back'])
const AGENT_STATUS = {
  generated: { label: '含 AI 解读', tone: 'tag-accent' },
  failed: { label: 'AI 解读未生成', tone: 'tag-danger' },
  disabled: { label: '仅确定性结果', tone: '' }
}
const GROUPS = [['observations', '观察'], ['interpretation', '解释'], ['limitations', '限制'], ['next_steps', '建议']]
const KPI = [
  ['site.fish.mean_count', '平均可见鱼数', 'MeanCount，全部视频合并'],
  ['site.fish.peak_count', '画面峰值鱼数', '单帧最多，不是个体数'],
  ['site.coral.coral_pixel_share', '珊瑚像素占比', '画面统计，不是覆盖率'],
  ['site.coral.bleached_coral_fraction', '白化像素比例', '分母为珊瑚像素'],
  ['env.baa_level', 'CRW 警报等级', '用户录入的 HotSpot 与 DHW']
]

const metrics = computed(() => props.report.facts.metrics)
const agent = computed(() => props.report.agent)
const kpis = computed(() => KPI.filter(([key]) => key in metrics.value).map(([key, title, sub]) => ({ key, title, sub, ...metrics.value[key] })))
const narrativeGroups = computed(() => GROUPS.map(([key, title]) => ({ key, title, items: agent.value.narrative[key] })).filter(group => group.items.length))
const auditNotes = computed(() => {
  const audit = agent.value.audit, notes = []
  if (audit.unverified_numbers.length) notes.push(`模型自行写出了 ${audit.unverified_numbers.length} 个未核对的数字，审阅时请对照上文。`)
  if (audit.unknown_metrics.length || audit.unknown_citations.length) notes.push(`已移除 ${audit.unknown_metrics.length + audit.unknown_citations.length} 处不存在的指标或资料引用。`)
  return notes
})
const agentMeta = computed(() => {
  const a = agent.value
  const parts = [a.api_format === 'anthropic_messages' ? 'Anthropic Messages' : 'OpenAI 兼容', a.model, a.host]
  if (a.latency_ms != null) parts.push(`${(a.latency_ms / 1000).toFixed(1)} s`)
  if (a.usage?.input_tokens != null) parts.push(`输入 ${a.usage.input_tokens} / 输出 ${a.usage.output_tokens ?? '—'} tokens`)
  parts.push(a.prompt_version)
  return parts.filter(Boolean).join(' · ')
})

function cite(paragraph) {
  const known = new Set(props.report.references.map(item => item.id))
  return paragraph.split(/\[([A-Z0-9-]+)\]/).map((text, i) => i % 2 && known.has(text) ? { ref: text } : { text: i % 2 ? `[${text}]` : text })
}
function jump(key) {
  document.getElementById(`obs-${key}`)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
}

const downloading = ref(false)
async function download() {
  downloading.value = true
  try {
    const response = await downloadObservationReport(props.report.report_id)
    const url = URL.createObjectURL(response.data), a = document.createElement('a')
    a.href = url
    a.download = `observation-report-${props.report.observed_on}-${shortId(props.report.report_id)}.md`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    toast({ title: '已下载报告', desc: a.download, type: 'success' })
  } catch {
    toast({ title: '无法下载报告', desc: '检查后端连接后重试。', type: 'error' })
  } finally {
    downloading.value = false
  }
}
</script>

<style scoped>
.viewer { display: flex; flex-direction: column; gap: 16px; }
.viewer-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.viewer-bar > .btn-ghost { margin-inline-start: -10px; }
.spacer { flex: 1; }
.viewer-head { display: flex; flex-direction: column; gap: 8px; }
.viewer-head h2 { font-size: var(--text-heading); font-weight: 600; line-height: 1.25; text-wrap: balance; }
.status-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.status-line .tabler-icon { --icon-size: 13px; }
.kpis .ui-kpi { padding: 12px 14px; }
h4 { margin-top: 6px; font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.ui-bullets { font-size: var(--text-reading); line-height: 1.65; }
.legend { padding: 0 2px; border-radius: 3px; color: var(--warn); background: var(--warn-soft); }
.meta { overflow-wrap: anywhere; }
.refs { display: flex; flex-direction: column; gap: 8px; padding: 0; margin: 0; list-style: none; font-size: var(--text-small); line-height: 1.55; color: var(--ink-2); }
.refs li { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 10px; scroll-margin-top: 12px; }
.ref-id { color: var(--ink-3); }
.ui-link.wrap { white-space: normal; }
@media (max-width: 960px) {
  .kpis { --kpi-cols: 2 !important; }
}
</style>
