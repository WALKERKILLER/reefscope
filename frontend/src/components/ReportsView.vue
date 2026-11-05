<template>
  <div ref="pageRef" class="reports page">
    <div class="page-inner">
      <header class="page-head">
        <div>
          <h1>观测报告</h1>
          <p class="note">按观测点归档视频分析结果。Agent 用平台工具取证、复核并起草报告，保存和排队分析前会请你批准；所有数值由平台计算。</p>
        </div>
        <div class="head-actions">
          <button class="btn" @click="agentDialogOpen = true"><IconSparkles />模型服务：{{ agentLabel }}</button>
          <button class="btn btn-primary" @click="openSite()"><IconPlus />新建观测点</button>
        </div>
      </header>

      <div v-if="loadError" class="ui-banner ui-banner-danger" role="alert"><IconAlertTriangle /><span>{{ loadError }}</span><button class="btn btn-sm" @click="loadSites">重试</button></div>
      <p v-else-if="loading" class="note" role="status">正在读取观测点…</p>

      <div v-else-if="!sites.length" class="ui-card empty">
        <p class="empty-title">还没有观测点</p>
        <p class="note">观测点用来归档同一位置的多次观测。创建观测点后，可以用已完成的鱼类和珊瑚分析生成报告。</p>
        <div><button class="btn btn-primary" @click="openSite()"><IconPlus />新建观测点</button></div>
      </div>

      <div v-else class="body">
        <nav class="ui-card sites" aria-label="观测点">
          <h2 class="eyebrow">观测点 <span class="tnum">{{ sites.length }}</span></h2>
          <ul>
            <li v-for="item in sites" :key="item.id">
              <button class="site" :aria-current="item.id === siteId ? 'true' : undefined" @click="selectSite(item.id)">
                <IconMapPin />
                <span class="site-text">
                  <span class="truncate" :title="item.name">{{ item.name }}</span>
                  <span class="note tnum">{{ item.report_count ? `${item.report_count} 份报告 · 最近 ${item.last_observed_on}` : '还没有报告' }}</span>
                </span>
              </button>
            </li>
          </ul>
        </nav>

        <div class="main">
          <ObservationReportViewer v-if="report" :report="report" @back="report = null" />
          <p v-else-if="reportLoading" class="note" role="status">正在打开报告…</p>

          <!-- Kept mounted while a report is open so an agent session and its polling survive the round trip. -->
          <div v-if="site" v-show="!report && !reportLoading" class="site-pane">
            <section class="ui-card" aria-labelledby="site-title">
              <header class="ui-card-head">
                <h2 id="site-title">{{ site.name }}</h2>
                <div class="card-actions">
                  <button class="btn btn-sm" @click="openSite(site)"><IconPencil />编辑</button>
                  <button class="btn btn-sm btn-danger" :disabled="site.report_count > 0" :title="site.report_count ? '已有报告的观测点不能删除' : undefined" @click="removeSite"><IconTrash />删除</button>
                </div>
              </header>
              <dl class="facts">
                <div><dt>水深</dt><dd class="tnum">{{ site.depth_m == null ? '未填写' : `${site.depth_m} m` }}</dd></div>
                <div><dt>坐标</dt><dd class="tnum">{{ site.latitude == null || site.longitude == null ? '未填写' : `${site.latitude}, ${site.longitude}` }}<span v-if="site.latitude != null" class="note">仅在平台内显示</span></dd></div>
                <div><dt>报告</dt><dd class="tnum">{{ site.report_count }}</dd></div>
              </dl>
              <p v-if="site.notes" class="prose">{{ site.notes }}</p>
            </section>

            <UiTabs v-model="tab" :items="tabs" aria-label="观测点工作区" class="site-tabs">
            <template #agent>
            <AgentWorkspace :site-id="site.id" :enabled="!!agentConfig?.enabled" @open-report="openReport" @report-saved="refreshSite" />
            </template>
            <template #manual>
            <section class="ui-card" aria-labelledby="new-report-title">
              <header class="ui-card-head">
                <h2 id="new-report-title">手动生成报告</h2>
                <span class="note tnum">已选 {{ selectedRuns.length }} / {{ MAX_RUNS }} 项分析</span>
              </header>
              <label class="field date"><span>观测日期</span><input v-model="form.observed_on" class="input tnum" type="date" required /></label>

              <fieldset class="group">
                <legend>视频分析</legend>
                <p v-if="!candidates.length" class="note">还没有已完成的分析。在工作台对视频运行鱼类或珊瑚分析后，再回来生成报告。</p>
                <template v-else>
                  <p class="note">每段视频取最新一次已完成的鱼类和珊瑚分析。</p>
                  <ul class="videos">
                    <li v-for="video in candidates" :key="video.task_id">
                      <span class="video-name truncate" :title="video.filename">{{ video.filename }}</span>
                      <label v-for="run in video.latest" :key="run.run_id" class="run-pick">
                        <input v-model="form.run_ids" type="checkbox" :value="run.run_id" :disabled="!form.run_ids.includes(run.run_id) && selectedRuns.length >= MAX_RUNS" />
                        <span>{{ KIND[run.kind] }}</span>
                        <span class="note mono truncate" :title="run.model_id">{{ run.model_id }}</span>
                        <span class="note tnum">{{ formatDateTime(run.created_at) }}</span>
                      </label>
                    </li>
                  </ul>
                </template>
              </fieldset>

              <details class="group env" :open="envOpen" @toggle="envOpen = $event.target.open">
                <summary>环境数据<span class="note">可选 · 用于 CRW 白化警报等级</span></summary>
                <div class="env-grid">
                  <label class="field"><span>海表温度 SST（°C）</span><input v-model="form.environment.sst_c" class="input tnum" type="number" step="0.01" inputmode="decimal" /></label>
                  <label class="field"><span>HotSpot（°C）</span><input v-model="form.environment.hotspot_c" class="input tnum" type="number" step="0.01" inputmode="decimal" /></label>
                  <label class="field"><span>DHW（°C-weeks）</span><input v-model="form.environment.dhw_c_weeks" class="input tnum" type="number" step="0.1" min="0" inputmode="decimal" /></label>
                  <label class="field"><span>原位水温（°C）</span><input v-model="form.environment.in_situ_temp_c" class="input tnum" type="number" step="0.01" inputmode="decimal" /></label>
                  <label class="field"><span>数据来源</span><input v-model="form.environment.source" class="input" maxlength="200" placeholder="例如 NOAA CRW 5km v3.1" /></label>
                  <label class="field"><span>产品日期</span><input v-model="form.environment.product_date" class="input tnum" type="date" /></label>
                </div>
                <p class="note">警报等级按 NOAA Coral Reef Watch 的规则计算：需要 HotSpot；HotSpot ≥ 1 °C 时还需要 DHW。可以在 <a class="ui-link" href="https://coralreefwatch.noaa.gov/product/5km/index.php" target="_blank" rel="noopener noreferrer">Coral Reef Watch 5km 产品页</a>查询所在网格的数值。</p>
              </details>

              <div class="toggle">
                <UiSwitch id="report-agent" v-model="form.use_agent" :disabled="!agentConfig?.enabled" />
                <label for="report-agent">附加 AI 解读</label>
                <span v-if="!agentConfig?.enabled" class="note">模型服务未启用。<button class="ui-link" @click="agentDialogOpen = true">配置模型服务</button></span>
                <span v-else class="note mono truncate">{{ agentConfig.model }}</span>
              </div>

              <p v-if="formError" class="error" role="alert">{{ formError }}</p>

              <div v-if="preview" class="ui-kpis preview" :style="{ '--kpi-cols': Math.min(previewKpis.length, 3) }" aria-label="数值预览">
                <div v-for="item in previewKpis" :key="item.key" class="ui-kpi" :class="{ missing: item.value == null }">
                  <span class="eyebrow">{{ item.label }}</span>
                  <strong class="tnum">{{ item.value == null ? 'N/A' : item.display }}</strong>
                  <span v-if="item.value == null" class="note">{{ item.reason_text }}</span>
                </div>
              </div>

              <div class="form-actions">
                <button class="btn" :disabled="!canSubmit || !!busy" @click="runPreview">{{ busy === 'preview' ? '正在计算…' : '预览数值' }}</button>
                <button class="btn btn-primary" :disabled="!canSubmit || !!busy" @click="generate">{{ busy === 'create' ? (form.use_agent ? '正在等待 AI 解读…' : '正在生成…') : '生成报告' }}</button>
                <span v-if="busy === 'create' && form.use_agent" class="note" role="status">最长约 {{ agentConfig.timeout_seconds }} 秒。数值部分不依赖 AI 服务。</span>
              </div>
            </section>
            </template>

            <template #history>
            <section class="ui-card" aria-labelledby="history-title">
              <header class="ui-card-head"><h2 id="history-title">报告记录</h2><span class="note">报告生成后不可修改</span></header>
              <p v-if="!history.length" class="note">这个观测点还没有报告。</p>
              <table v-else class="ui-table">
                <thead><tr><th>观测日期</th><th class="num">视频</th><th class="num">平均可见鱼数</th><th class="num">白化像素比例</th><th>解读</th><th><span class="sr-only">操作</span></th></tr></thead>
                <tbody>
                  <tr v-for="item in history" :key="item.id">
                    <td class="tnum">{{ item.observed_on }}</td>
                    <td class="num tnum">{{ item.video_count }}</td>
                    <td class="num tnum">{{ item.mean_count ?? '—' }}</td>
                    <td class="num tnum">{{ item.bleached_coral_fraction ?? '—' }}</td>
                    <td><span class="tag" :class="AGENT_TAG[item.agent_status].tone">{{ AGENT_TAG[item.agent_status].label }}</span></td>
                    <td class="action"><button class="btn btn-sm" @click="openReport(item.id)">打开<IconArrowRight /></button></td>
                  </tr>
                </tbody>
              </table>
            </section>
            </template>
            </UiTabs>
          </div>
        </div>
      </div>
    </div>

    <DialogRoot :open="siteDialog.open" @update:open="siteDialog.open = $event">
      <DialogPortal>
        <DialogOverlay class="ui-overlay" />
        <DialogContent class="ui-dialog site-dialog">
          <DialogTitle class="ui-dialog-title">{{ siteDialog.id ? '编辑观测点' : '新建观测点' }}</DialogTitle>
          <DialogDescription class="ui-dialog-desc">坐标只在平台内显示，生成 AI 解读时不会发送。</DialogDescription>
          <form class="site-form" novalidate @submit.prevent="saveSite">
            <label class="field"><span>名称</span><input v-model="siteDialog.name" class="input" maxlength="80" placeholder="例如 北礁 A 断面" required /></label>
            <div class="trio">
              <label class="field"><span>水深（m）</span><input v-model="siteDialog.depth_m" class="input tnum" type="number" min="0" max="200" step="0.1" inputmode="decimal" /></label>
              <label class="field"><span>纬度</span><input v-model="siteDialog.latitude" class="input tnum" type="number" min="-90" max="90" step="any" inputmode="decimal" /></label>
              <label class="field"><span>经度</span><input v-model="siteDialog.longitude" class="input tnum" type="number" min="-180" max="180" step="any" inputmode="decimal" /></label>
            </div>
            <label class="field"><span>备注</span><textarea v-model="siteDialog.notes" class="input notes" maxlength="2000" rows="3" placeholder="机位、断面或采样方式" /></label>
            <p v-if="siteDialog.error" class="error" role="alert">{{ siteDialog.error }}</p>
            <div class="ui-dialog-actions">
              <DialogClose type="button" class="btn btn-ghost">取消</DialogClose>
              <button class="btn btn-primary" :disabled="!siteDialog.name.trim() || siteDialog.saving">{{ siteDialog.id ? '保存' : '创建观测点' }}</button>
            </div>
          </form>
        </DialogContent>
      </DialogPortal>
    </DialogRoot>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import { IconAlertTriangle, IconArrowRight, IconMapPin, IconPencil, IconPlus, IconSparkles, IconTrash } from '@tabler/icons-vue'
import UiSwitch from './ui/UiSwitch.vue'
import UiTabs from './ui/UiTabs.vue'
import AgentWorkspace from './AgentWorkspace.vue'
import ObservationReportViewer from './ObservationReportViewer.vue'
import { listSites, createSite, updateSite, deleteSite, listSiteReports, listReportCandidates, previewObservationReport, createObservationReport, getObservationReport } from '../api'
import { agentConfig, agentDialogOpen, loadAgentConfig, requestedReport } from '../lib/reportAgent'
import { confirmDialog } from '../lib/dialogs'
import { formatDateTime } from '../lib/format'
import { toast } from '../lib/toast'

const MAX_RUNS = 8
const KIND = { fish: '鱼类', coral: '珊瑚' }
const AGENT_TAG = { agent_run: { label: 'Agent 起草', tone: 'tag-accent' }, generated: { label: '已生成', tone: 'tag-accent' }, failed: { label: '未生成', tone: 'tag-danger' }, disabled: { label: '未使用', tone: '' } }
const PREVIEW = ['site.fish.mean_count', 'site.fish.peak_count', 'site.fish.occupied_fraction', 'site.coral.coral_pixel_share', 'site.coral.bleached_coral_fraction', 'env.baa_level']
const ERRORS = {
  run_not_completed: '所选分析还没有完成。', run_artifacts_unavailable: '无法读取所选分析的结果文件。可以在工作台重新运行分析。',
  duplicate_run_kind_for_video: '每段视频的鱼类和珊瑚分析各选一项。', invalid_run_ids: `选择 1–${MAX_RUNS} 项已完成的分析。`,
  invalid_observed_on: '填写观测日期。', invalid_sst_c: '海表温度填写 -5–45 °C。', invalid_in_situ_temp_c: '原位水温填写 -5–45 °C。',
  invalid_hotspot_c: 'HotSpot 填写 -15–15 °C。', invalid_dhw_c_weeks: 'DHW 填写 0–100 °C-weeks。', invalid_product_date: '产品日期格式不正确。',
  agent_disabled: '模型服务未启用。关闭“附加 AI 解读”，或先配置模型服务。', unknown_site: '观测点不存在，刷新后重试。', unknown_run: '所选分析不存在，刷新后重试。'
}
const SITE_ERRORS = {
  site_name_taken: '已有同名观测点，换一个名称。', invalid_site_name: '名称填写 1–80 个字。', invalid_latitude: '纬度填写 -90–90。',
  invalid_longitude: '经度填写 -180–180。', invalid_depth_m: '水深填写 0–200 m。', invalid_notes: '备注不超过 2000 字。'
}

const sites = ref([]), loading = ref(true), loadError = ref('')
const siteId = ref(null), history = ref([]), candidates = ref([])
const report = ref(null), reportLoading = ref(false)
const preview = ref(null), busy = ref(''), formError = ref(''), envOpen = ref(false)
const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)
const blankEnvironment = () => ({ sst_c: '', hotspot_c: '', dhw_c_weeks: '', in_situ_temp_c: '', source: '', product_date: '' })
const form = reactive({ observed_on: today(), run_ids: [], environment: blankEnvironment(), use_agent: false })

const site = computed(() => sites.value.find(item => item.id === siteId.value) || null)
const tab = ref('agent')
const tabs = computed(() => [{ value: 'agent', label: 'Agent 分析' }, { value: 'manual', label: '手动生成' }, { value: 'history', label: '报告记录', badge: history.value.length || null }])
const selectedRuns = computed(() => form.run_ids)
const canSubmit = computed(() => !!site.value && !!form.observed_on && form.run_ids.length > 0)
const agentLabel = computed(() => agentConfig.value?.enabled ? '已启用' : '未启用')
const previewKpis = computed(() => PREVIEW.filter(key => key in (preview.value?.metrics || {})).map(key => ({ key, ...preview.value.metrics[key] })))

watch(() => [form.run_ids.length, form.observed_on, JSON.stringify(form.environment)], () => { preview.value = null; formError.value = '' })
watch(() => agentConfig.value?.enabled, enabled => { if (!enabled) form.use_agent = false })
// Opening or leaving a report starts at its top rather than at the form's scroll position.
const pageRef = ref(null)
watch(report, () => nextTick(() => pageRef.value?.scrollTo({ top: 0 })))

async function loadSites() {
  loading.value = true
  loadError.value = ''
  try {
    sites.value = (await listSites()).data.items
    if (!site.value && sites.value.length) await selectSite(sites.value[0].id)
  } catch {
    loadError.value = '无法读取观测点。检查后端连接后重试。'
  } finally {
    loading.value = false
  }
}

async function loadCandidates() {
  try {
    const items = (await listReportCandidates()).data.items
    candidates.value = items.map(video => ({ ...video, latest: ['fish', 'coral'].map(kind => video.runs.find(run => run.kind === kind)).filter(Boolean) }))
  } catch {
    candidates.value = []
  }
}

async function selectSite(id) {
  siteId.value = id
  report.value = null
  form.run_ids = []
  history.value = (await listSiteReports(id)).data.items
}

function environmentPayload() {
  const env = form.environment, number = value => value === '' || value == null ? null : Number(value)
  const payload = { sst_c: number(env.sst_c), hotspot_c: number(env.hotspot_c), dhw_c_weeks: number(env.dhw_c_weeks), in_situ_temp_c: number(env.in_situ_temp_c),
    source: env.source.trim(), product_date: env.product_date || null }
  return ['sst_c', 'hotspot_c', 'dhw_c_weeks', 'in_situ_temp_c'].some(key => payload[key] != null) ? payload : null
}
const requestBody = () => ({ site_id: siteId.value, observed_on: form.observed_on, run_ids: [...form.run_ids], environment: environmentPayload() })
function explain(err) {
  const code = err.response?.data?.error?.code
  return ERRORS[code] || (code ? `无法完成：${code}` : '无法连接后端。检查连接后重试。')
}

async function runPreview() {
  busy.value = 'preview'
  formError.value = ''
  try {
    preview.value = (await previewObservationReport(requestBody())).data
  } catch (err) {
    formError.value = explain(err)
  } finally {
    busy.value = ''
  }
}

async function generate() {
  busy.value = 'create'
  formError.value = ''
  try {
    const created = (await createObservationReport({ ...requestBody(), use_agent: form.use_agent })).data
    const failed = created.agent.status === 'failed'
    toast({ title: failed ? '已生成报告，AI 解读未生成' : '已生成报告', desc: failed ? created.agent.error_text : created.title, type: failed ? 'alert' : 'success' })
    await refreshSite()
    report.value = created
    form.run_ids = []
  } catch (err) {
    formError.value = explain(err)
  } finally {
    busy.value = ''
  }
}

async function refreshSite() {
  const id = siteId.value
  sites.value = (await listSites()).data.items
  history.value = (await listSiteReports(id)).data.items
}

async function openReport(id) {
  reportLoading.value = true
  try {
    report.value = (await getObservationReport(id)).data
  } catch {
    toast({ title: '无法打开报告', desc: '检查后端连接后重试。', type: 'error' })
  } finally {
    reportLoading.value = false
  }
}

const siteDialog = reactive({ open: false, id: null, name: '', depth_m: '', latitude: '', longitude: '', notes: '', error: '', saving: false })
function openSite(item = null) {
  Object.assign(siteDialog, { open: true, id: item?.id || null, name: item?.name || '', depth_m: item?.depth_m ?? '', latitude: item?.latitude ?? '',
    longitude: item?.longitude ?? '', notes: item?.notes || '', error: '', saving: false })
}
async function saveSite() {
  const number = value => value === '' || value == null ? null : Number(value)
  const payload = { name: siteDialog.name.trim(), depth_m: number(siteDialog.depth_m), latitude: number(siteDialog.latitude), longitude: number(siteDialog.longitude), notes: siteDialog.notes }
  siteDialog.saving = true
  siteDialog.error = ''
  try {
    const saved = siteDialog.id ? (await updateSite(siteDialog.id, payload)).data : (await createSite(payload)).data
    siteDialog.open = false
    sites.value = (await listSites()).data.items
    await selectSite(saved.id)
    toast({ title: siteDialog.id ? '已保存观测点' : '已创建观测点', desc: saved.name, type: 'success' })
  } catch (err) {
    const code = err.response?.data?.error?.code
    siteDialog.error = SITE_ERRORS[code] || (code ? `无法保存：${code}` : '无法连接后端。检查连接后重试。')
  } finally {
    siteDialog.saving = false
  }
}
async function removeSite() {
  const ok = await confirmDialog({ title: `删除观测点“${site.value.name}”？`, description: '这个观测点还没有报告，删除后不能恢复。', confirmLabel: '删除观测点', danger: true })
  if (!ok) return
  try {
    await deleteSite(site.value.id)
    siteId.value = null
    sites.value = (await listSites()).data.items
    if (sites.value.length) await selectSite(sites.value[0].id)
    toast({ title: '已删除观测点', type: 'success' })
  } catch (err) {
    toast({ title: '无法删除观测点', desc: err.response?.data?.error?.code === 'site_has_reports' ? '已有报告的观测点不能删除。' : '检查后端连接后重试。', type: 'error' })
  }
}

onMounted(() => { loadSites(); loadCandidates(); if (!agentConfig.value) loadAgentConfig() })
watch(requestedReport, async id => {
  if (!id) return
  requestedReport.value = null
  await openReport(id)
  if (siteId.value) refreshSite()
}, { immediate: true })
</script>

<style scoped>
.head-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.empty { align-items: flex-start; gap: 8px; }
.body { display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 16px; align-items: start; }
.sites { position: sticky; top: 0; gap: 8px; padding: 12px 8px; }
.sites h2 { padding-inline: 8px; }
.sites ul { display: flex; flex-direction: column; gap: 2px; list-style: none; padding: 0; margin: 0; }
.site { display: flex; align-items: flex-start; gap: 8px; width: 100%; padding: 7px 8px; border: 0; border-radius: var(--radius); font: inherit; text-align: start; color: var(--ink-2); background: transparent; cursor: pointer; transition: background-color 120ms var(--ease), color 120ms var(--ease); }
.site:hover { color: var(--ink); background: var(--surface-2); }
.site[aria-current=true] { color: var(--ink); background: var(--accent-soft); }
.site > .tabler-icon { --icon-size: 15px; flex: none; margin-top: 2px; color: var(--ink-3); }
.site[aria-current=true] > .tabler-icon { color: var(--accent); }
.site-text { display: flex; flex-direction: column; gap: 1px; min-width: 0; font-weight: 500; }
.site-text .note { font-size: var(--text-caption); font-weight: 400; }
.main, .site-pane { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.site-tabs :deep(.ui-tabs-list) { padding: 0 2px; }
.site-tabs :deep(.ui-tab-panel) { display: flex; flex-direction: column; gap: 16px; padding-top: 16px; }
.site-tabs :deep(.ui-tab-panel[hidden]) { display: none; }
.card-actions { display: flex; gap: 6px; }
.facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.facts > div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.facts dt { font-size: var(--text-caption); color: var(--ink-3); }
.facts dd { display: flex; flex-direction: column; gap: 1px; margin: 0; font-size: var(--text-body); }
.facts dd .note { font-size: var(--text-caption); }
.date { width: 180px; }
.group { display: flex; flex-direction: column; gap: 8px; min-width: 0; margin: 0; padding: 0; border: 0; }
.group legend, .env summary { padding: 0; margin-bottom: 4px; font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.videos { display: flex; flex-direction: column; list-style: none; padding: 0; margin: 0; border-radius: var(--radius); box-shadow: 0 0 0 1px var(--line); }
.videos li { display: grid; grid-template-columns: minmax(0, 1fr); gap: 4px; padding: 8px 12px; }
.videos li + li { box-shadow: inset 0 1px 0 var(--line); }
.video-name { font-weight: 500; }
.run-pick { display: grid; grid-template-columns: auto 3em minmax(0, 1fr) auto; align-items: center; gap: 8px; font-size: var(--text-small); cursor: pointer; }
.run-pick input { margin: 0; accent-color: var(--accent); }
.env summary { display: flex; align-items: baseline; gap: 8px; width: fit-content; cursor: pointer; }
.env summary .note { font-weight: 400; }
.env-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px 12px; }
.toggle { display: flex; align-items: center; gap: 8px; min-width: 0; font-size: var(--text-small); }
.toggle label { cursor: pointer; }
.error { font-size: var(--text-small); color: var(--danger); }
.preview .ui-kpi { padding: 10px 12px; }
.form-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ui-table td.action { text-align: end; }
.site-dialog { width: min(480px, calc(100vw - 32px)); }
.site-form { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.trio { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.notes { min-height: 68px; font-family: inherit; }
@media (max-width: 960px) {
  .body { grid-template-columns: 1fr; }
  .sites { position: static; }
  .env-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .facts, .trio, .env-grid { grid-template-columns: 1fr; }
  .date { width: 100%; }
  .run-pick { grid-template-columns: auto 3em minmax(0, 1fr); }
  .run-pick > :last-child { display: none; }
  .ui-table th:nth-child(2), .ui-table td:nth-child(2), .ui-table th:nth-child(4), .ui-table td:nth-child(4) { display: none; }
}
</style>
