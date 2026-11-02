<template>
  <section class="research" aria-label="模型训练与质量报告">
    <div class="toolbar">
      <div class="field model"><span>注册模型</span><UiSelect v-model="modelId" :options="modelOptions" :disabled="!models.length" placeholder="选择模型" aria-label="注册模型" /></div>
      <div class="field report-pick"><span>报告版本</span><UiSelect v-model="reportId" :options="reportOptions" :disabled="!reportOptions.length" placeholder="选择报告" aria-label="报告版本" /></div>
      <div class="actions">
        <button class="btn" :disabled="!report || downloading" @click="download"><IconDownload />{{ downloading ? '正在下载…' : '下载 Markdown' }}</button>
        <a v-if="report" class="btn" :href="reportPrintUrl(report.report_id)" target="_blank" rel="noopener"><IconPrinter />打开打印版</a>
        <UiTooltip text="重新读取模型与报告"><button class="btn btn-ghost btn-icon" :disabled="loading" aria-label="刷新" @click="loadModels"><IconRefresh /></button></UiTooltip>
      </div>
    </div>

    <div v-if="error" class="banner danger" role="alert"><IconAlertTriangle /><span>{{ error }}</span><button class="btn btn-sm" @click="loadModels">重试</button></div>
    <p v-if="loading" class="note" role="status">正在读取模型记录…</p>

    <div v-else-if="!models.length && !error" class="card empty">
      <p class="empty-title">还没有注册模型</p>
      <p class="note">注册模型后，训练记录、独立评估和质量报告会按模型显示在这里。</p>
    </div>
    <div v-else-if="history && !history.reports.length" class="card empty">
      <p class="empty-title">这个模型还没有质量报告</p>
      <p class="note">维护者可用 <code class="mono">python manage.py import_fish_training</code> 从受控本地目录导入 results.csv。页面不接受服务器路径。</p>
    </div>

    <template v-if="report">
      <div class="status-line">
        <span class="tag tag-warn"><IconEye />{{ report.human_review_status === 'pending' ? '待人工审阅' : report.human_review_status }}</span>
        <span class="note">报告由冻结数值确定性生成，{{ report.ai_enabled ? '启用了 AI 解读' : '未调用 AI' }}。</span>
        <span class="spacer" />
        <span class="note">生成于 <span class="tnum">{{ formatDateTime(report.created_at) }}</span> · <span class="mono">{{ shortId(report.report_id) }}</span></span>
      </div>

      <div class="kpis">
        <div v-for="item in kpis" :key="item.title" class="kpi" :class="{ missing: item.value == null }">
          <span class="eyebrow">{{ item.title }}</span>
          <strong class="tnum">{{ item.value ?? 'N/A' }}</strong>
          <span class="note">{{ item.sub }}</span>
        </div>
      </div>

      <section class="card" aria-labelledby="curves-title">
        <header class="card-head"><h2 id="curves-title">训练曲线</h2><span class="note">来源 results.csv · {{ report.training_curves.length }} 个 epoch</span></header>
        <TrainingCurves :rows="report.training_curves" :selection="report.checkpoint_selection" />
      </section>

      <section class="card" aria-labelledby="report-title">
        <header class="card-head"><h2 id="report-title">质量报告</h2><span class="note">{{ report.template_version }}</span></header>
        <div class="report">
          <nav class="toc" aria-label="报告章节">
            <ol>
              <li v-for="(section, index) in report.sections" :key="section.title"><a :href="`#chapter-${index + 1}`" @click.prevent="jump(index)"><span class="tnum">{{ index + 1 }}</span>{{ section.title }}</a></li>
            </ol>
          </nav>
          <div class="chapters">
            <section v-for="(section, index) in report.sections" :id="`chapter-${index + 1}`" :key="section.title" class="chapter">
              <h3><span class="num tnum">{{ String(index + 1).padStart(2, '0') }}</span>{{ section.title }}</h3>
              <p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p>
              <dl v-if="section.rows.length" class="rows">
                <div v-for="(row, i) in section.rows" :key="i">
                  <dt>{{ row[0] }}</dt>
                  <dd v-if="codes(row[1])" class="codes"><span v-for="code in codes(row[1])" :key="code" class="tag" :title="code">{{ MISSING_INPUTS[code] || code }}</span></dd>
                  <dd v-else :class="{ missing: display(row[1]) === 'N/A', mono: isId(row[1]) }" :title="typeof row[1] === 'number' ? String(row[1]) : undefined">{{ display(row[1]) }}</dd>
                </div>
              </dl>
              <details v-if="section.evidence" class="evidence">
                <summary>来源数值与复现信息</summary>
                <pre class="mono">{{ JSON.stringify(section.evidence, null, 2) }}</pre>
              </details>
            </section>
          </div>
        </div>
      </section>
    </template>

    <section v-if="history && (history.training_runs.length || history.reports.length)" class="card" aria-labelledby="history-title">
      <header class="card-head"><h2 id="history-title">记录历史</h2><span class="note">训练 {{ history.training_runs.length }} · 独立评估 {{ history.evaluations.length }} · 报告 {{ history.reports.length }}</span></header>
      <table v-if="history.training_runs.length" class="table">
        <thead><tr><th>训练记录</th><th>导入时间</th><th class="num">epoch</th><th class="num">最高 mAP50</th><th>缺失项</th></tr></thead>
        <tbody>
          <tr v-for="run in history.training_runs" :key="run.id">
            <td><span class="mono">{{ shortId(run.id) }}</span><span v-if="run.id === report?.training_run_id" class="tag tag-accent">当前报告</span></td>
            <td class="tnum">{{ formatDateTime(run.created_at) }}</td>
            <td class="num tnum">{{ run.epochs }}</td>
            <td class="num tnum">{{ run.selection.best_map50_epoch ?? 'N/A' }}</td>
            <td class="codes"><span v-for="code in run.missing_inputs" :key="code" class="tag" :title="code">{{ MISSING_INPUTS[code] || code }}</span><span v-if="!run.missing_inputs.length" class="note">无</span></td>
          </tr>
        </tbody>
      </table>
      <div class="evaluations">
        <h3>独立评估</h3>
        <p v-if="!history.evaluations.length" class="note">N/A：还没有冻结真值上的评估记录。mAP 与 IDF1 不从训练曲线推导。</p>
        <details v-for="evaluation in history.evaluations" :key="evaluation.id" class="evidence">
          <summary><span class="mono">{{ evaluation.protocol_id }}</span> · {{ evaluation.dataset_version }} · <span class="tnum">{{ formatDateTime(evaluation.created_at) }}</span></summary>
          <pre class="mono">{{ JSON.stringify(evaluation.metrics, null, 2) }}</pre>
        </details>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { IconAlertTriangle, IconDownload, IconEye, IconPrinter, IconRefresh } from '@tabler/icons-vue'
import { listAnalysisModels, getModelResearch, getTrainingReport, downloadTrainingReport, reportPrintUrl } from '../api'
import { formatDateTime, shortId } from '../lib/format'
import { toast } from '../lib/toast'
import UiSelect from './ui/UiSelect.vue'
import UiTooltip from './ui/UiTooltip.vue'

const TrainingCurves = defineAsyncComponent(() => import('./TrainingCurves.vue'))
const MISSING_INPUTS = {
  framework_best_checkpoint_epoch: '框架 best checkpoint epoch',
  frozen_test_dataset: '冻结测试集',
  hardware_benchmark: '固定硬件 benchmark',
  independent_evaluation: '独立评估',
  manual_identity_ground_truth: '人工 ID 真值',
  training_dataset_hash: '训练数据 hash',
  numeric_training_curves: '数值训练曲线'
}

const models = shallowRef([]), modelId = ref(''), history = shallowRef(null), reportId = ref(''), report = shallowRef(null)
const loading = ref(false), error = ref(''), downloading = ref(false)
let modelsAbort, historyAbort, reportAbort, disposed = false
const cancelled = e => e?.code === 'ERR_CANCELED'

const modelOptions = computed(() => models.value.map(m => ({ value: m.id, label: m.id, hint: `权重 ${shortId(m.sha256)}` })))
const reportOptions = computed(() => (history.value?.reports || []).map((r, i) => ({ value: r.id, label: `${formatDateTime(r.created_at)} · ${shortId(r.id)}`, hint: [i === 0 && '最新', r.human_review_status === 'pending' ? '待审阅' : r.human_review_status].filter(Boolean).join(' · ') })))

const kpis = computed(() => {
  const r = report.value
  if (!r) return []
  const sel = r.checkpoint_selection || {}, rows = new Map(r.training_curves.map(row => [row.epoch, row]))
  const at = (epoch, key) => epoch == null ? null : rows.get(epoch)?.[key] ?? null
  const fixed = v => v == null ? null : Number(v).toFixed(3)
  return [
    { title: '最高验证 mAP50', value: fixed(at(sel.best_map50_epoch, 'metrics/mAP50(B)')), sub: sel.best_map50_epoch != null ? `epoch ${sel.best_map50_epoch} · 训练期验证集` : '没有验证曲线' },
    { title: '最高验证 mAP50-95', value: fixed(at(sel.best_map50_95_epoch, 'metrics/mAP50-95(B)')), sub: sel.best_map50_95_epoch != null ? `epoch ${sel.best_map50_95_epoch} · 训练期验证集` : '没有验证曲线' },
    { title: '框架 best fitness', value: fixed(sel.framework_best_fitness), sub: sel.framework_best_checkpoint_epoch != null ? `checkpoint epoch ${sel.framework_best_checkpoint_epoch}` : 'checkpoint epoch 未记录' },
    { title: '独立测试精度', value: r.evaluation_run_id ? '已关联' : null, sub: r.evaluation_run_id ? `评估 ${shortId(r.evaluation_run_id)} · 见第 2 章` : '缺少冻结测试集与真值' }
  ]
})

async function loadModels() {
  modelsAbort?.abort()
  const controller = new AbortController()
  modelsAbort = controller
  error.value = ''
  loading.value = true
  try {
    const response = await listAnalysisModels(controller.signal)
    if (controller.signal.aborted || disposed) return
    models.value = response.data.items
    if (!models.value.some(m => m.id === modelId.value)) modelId.value = models.value[0]?.id || ''
    else await loadHistory()
  } catch (e) {
    if (!cancelled(e)) error.value = '无法读取模型列表。确认本地后端正在运行后重试。'
  } finally {
    if (modelsAbort === controller) loading.value = false
  }
}

async function loadHistory() {
  historyAbort?.abort()
  reportAbort?.abort()
  const controller = new AbortController()
  historyAbort = controller
  history.value = null
  report.value = null
  reportId.value = ''
  if (!modelId.value) return
  try {
    const response = await getModelResearch(modelId.value, controller.signal)
    if (controller.signal.aborted || disposed) return
    history.value = response.data
    reportId.value = response.data.reports[0]?.id || ''
  } catch (e) {
    if (!cancelled(e)) error.value = '无法读取这个模型的记录，请重试。'
  }
}

watch(modelId, loadHistory)
watch(reportId, async id => {
  reportAbort?.abort()
  report.value = null
  if (!id) return
  const controller = new AbortController()
  reportAbort = controller
  try {
    const response = await getTrainingReport(id, controller.signal)
    if (!controller.signal.aborted && !disposed) report.value = response.data
  } catch (e) {
    if (!cancelled(e)) error.value = '无法读取这份报告，请重试。'
  }
})

function display(value) {
  if (value == null) return 'N/A'
  if (typeof value === 'object') return 'value' in value ? display(value.value) : JSON.stringify(value)
  if (typeof value === 'number' && !Number.isInteger(value)) return String(+value.toPrecision(6))
  return String(value)
}
const isId = value => typeof value === 'string' && /^[0-9a-f-]{16,}$/i.test(value)
function codes(value) {
  if (typeof value !== 'string') return null
  const parts = value.split(', ')
  return parts.length && parts.every(p => /^[a-z0-9_]+$/.test(p) && p.includes('_')) ? parts : null
}
function jump(index) {
  document.getElementById(`chapter-${index + 1}`)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
}

async function download() {
  downloading.value = true
  try {
    const response = await downloadTrainingReport(reportId.value)
    const url = URL.createObjectURL(response.data), a = document.createElement('a')
    a.href = url
    a.download = `training-report-${shortId(reportId.value)}.md`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    toast({ title: '已下载报告', desc: a.download, type: 'success' })
  } catch {
    toast({ title: '无法下载报告', desc: '检查后端连接后重试。', type: 'error' })
  } finally {
    downloading.value = false
  }
}

onMounted(loadModels)
onBeforeUnmount(() => { disposed = true; for (const c of [modelsAbort, historyAbort, reportAbort]) c?.abort() })
</script>

<style scoped>
.research { display: flex; flex-direction: column; gap: 16px; }
.toolbar { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.model { width: 220px; }
.report-pick { width: 260px; }
.actions { display: flex; gap: 8px; margin-inline-start: auto; }
.banner { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: var(--radius); font-size: var(--text-small); }
.banner span { flex: 1; }
.banner.danger { color: var(--danger); background: var(--danger-soft); }
.card { display: flex; flex-direction: column; gap: 14px; padding: 16px 18px; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); }
.card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
h2 { font-size: var(--text-title); font-weight: 600; }
.empty-title { font-weight: 500; }
.empty .note code { font-size: 0.95em; color: var(--ink-2); }
.status-line { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.status-line .tabler-icon { --icon-size: 13px; }
.spacer { flex: 1; }
.kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; border-radius: var(--radius-lg); overflow: hidden; background: var(--line); box-shadow: 0 0 0 1px var(--line); }
.kpi { display: flex; flex-direction: column; gap: 2px; padding: 12px 14px; background: var(--surface); min-width: 0; }
.kpi strong { font-size: var(--text-figure); font-weight: 500; line-height: 1.15; letter-spacing: -0.01em; }
.kpi.missing strong { color: var(--ink-3); }
.kpi .note { font-size: var(--text-caption); }
.report { display: grid; grid-template-columns: 176px minmax(0, 1fr); gap: 28px; align-items: start; }
.toc { position: sticky; top: 0; }
.toc ol { display: flex; flex-direction: column; gap: 2px; list-style: none; padding: 0; margin: 0; }
.toc a { display: flex; gap: 8px; padding: 5px 8px; border-radius: var(--radius); font-size: var(--text-small); color: var(--ink-2); text-decoration: none; transition: color 120ms var(--ease), background-color 120ms var(--ease); }
.toc a span { min-width: 1em; color: var(--ink-3); }
.toc a:hover { color: var(--ink); background: var(--surface-2); }
.chapters { display: flex; flex-direction: column; gap: 28px; max-width: 72ch; }
.chapter { display: flex; flex-direction: column; gap: 8px; scroll-margin-top: 12px; }
h3 { display: flex; align-items: baseline; gap: 10px; font-size: var(--text-title); font-weight: 600; }
.num { font-size: var(--text-small); font-weight: 500; color: var(--ink-3); }
.chapter p { font-size: var(--text-body); line-height: 1.65; color: var(--ink-2); text-wrap: pretty; }
.rows { display: flex; flex-direction: column; margin-top: 4px; border-radius: var(--radius); box-shadow: 0 0 0 1px var(--line); overflow: hidden; }
.rows > div { display: grid; grid-template-columns: minmax(0, 13em) minmax(0, 1fr); gap: 16px; padding: 7px 12px; font-size: var(--text-small); }
.rows > div + div { box-shadow: inset 0 1px 0 var(--line); }
.rows dt { color: var(--ink-3); }
.rows dd { margin: 0; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.rows dd.missing { color: var(--ink-3); }
.codes { display: flex; flex-wrap: wrap; gap: 4px; }
.evidence summary { cursor: pointer; width: fit-content; font-size: var(--text-small); color: var(--ink-3); }
.evidence summary:hover { color: var(--ink); }
.evidence pre { margin-top: 8px; padding: 10px 12px; max-height: 320px; overflow: auto; border-radius: var(--radius); font-size: var(--text-caption); line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--ink-2); background: var(--surface-2); }
.table { width: 100%; border-collapse: collapse; font-size: var(--text-small); }
.table th { height: 30px; padding: 0 10px; text-align: start; font-size: var(--text-caption); font-weight: 500; color: var(--ink-3); background: var(--surface-2); }
.table td { padding: 7px 10px; vertical-align: top; box-shadow: inset 0 1px 0 var(--line); }
.table td .tag-accent { margin-inline-start: 8px; }
.table .num { text-align: end; }
.evaluations { display: flex; flex-direction: column; gap: 6px; }
.evaluations h3 { font-size: var(--text-small); color: var(--ink-2); }
@media (max-width: 960px) {
  .report { grid-template-columns: 1fr; }
  .toc { display: none; }
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .model, .report-pick { width: 100%; }
  .actions { margin-inline-start: 0; flex-wrap: wrap; }
  .table th:nth-child(2), .table td:nth-child(2), .table th:nth-child(5), .table td:nth-child(5) { display: none; }
}
</style>
