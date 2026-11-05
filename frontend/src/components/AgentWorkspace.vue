<template>
  <section class="agent" :class="dock ? 'dock' : 'ui-card'" :aria-labelledby="dock ? undefined : `${uid}-title`" :aria-label="dock ? '观测助手' : undefined">
    <header class="ui-card-head">
      <h2 v-if="!dock" :id="`${uid}-title`">Agent 分析</h2>
      <div class="session-bar">
        <div v-if="sessions.length" class="session-select" :title="session?.title"><UiSelect :model-value="sessionId || ''" :options="sessionOptions" aria-label="选择会话" placeholder="选择会话" @update:model-value="openSession" /></div>
        <button class="btn btn-sm" :disabled="!sessionId" @click="newSession"><IconPlus />新会话</button>
        <button v-if="session" class="btn btn-sm btn-ghost btn-icon" :disabled="active" :title="active ? '运行中的会话不能删除' : '删除会话'" aria-label="删除会话" @click="removeSession"><IconTrash /></button>
      </div>
      <div v-if="taskId != null" class="filing">
        <span class="note" aria-hidden="true">归档到观测点</span>
        <div class="filing-select" :title="siteLabel"><UiSelect :model-value="filedSite" :options="siteOptions" aria-label="归档到观测点" placeholder="不归档" @update:model-value="fileTo" /></div>
      </div>
    </header>

    <div v-if="!enabled" class="ui-banner ui-banner-info"><IconSparkles /><span>Agent 需要一个支持工具调用的模型服务。<button class="ui-link" @click="agentDialogOpen = true">配置模型服务</button></span></div>

    <div class="layout">
      <div ref="threadRef" class="thread">
        <div v-if="!session" class="intro">
          <p class="note">{{ taskId != null ? '就正在看的这段视频提问：Agent 会读取当前画面和分析结果，回答里带 ▶ 的时刻可以点击跳转。保存报告前需要归档到观测点。' : 'Agent 会先列计划，再调用平台工具取数、复核和比对。正文中的每个数值都来自工具结果并经过平台审计；排队分析、保存报告之前会请你批准。' }}</p>
          <ul class="starters" aria-label="示例任务">
            <li v-for="item in starters" :key="item"><button class="starter" :disabled="!enabled || sending" @click="draft = item">{{ item }}</button></li>
          </ul>
        </div>

        <article v-for="run in session?.runs || []" :key="run.id" class="run" :aria-label="`任务：${run.goal}`">
          <p class="goal"><span class="eyebrow">你</span><span>{{ run.goal }}</span></p>
          <ol class="trace">
            <li v-for="step in run.steps.filter(s => s.kind !== 'answer')" :key="step.index" class="step" :class="[`kind-${step.kind}`, `status-${step.status}`]">
              <span class="step-icon" aria-hidden="true"><component :is="stepIcon(step)" /></span>

              <div v-if="step.kind === 'approval'" class="approval">
                <div class="approval-head">
                  <strong>{{ step.title }}</strong>
                  <span class="tag" :class="DECISION[step.status].tone">{{ DECISION[step.status].label }}</span>
                </div>
                <template v-if="step.payload.tool === 'propose_observation_report'">
                  <p class="note tnum">指标集 {{ step.payload.proposal.metrics_set }} · 观测日期 {{ step.payload.proposal.observed_on }} · {{ step.payload.proposal.run_ids.length }} 项分析</p>
                  <div class="draft">
                    <p><ReportSegments :parts="step.payload.proposal.narrative.summary" :metrics="scoped(run, step.payload.proposal.metrics_set)" :seek-task="seekTask" @seek="emit('seek', $event)" /></p>
                    <template v-for="name in SECTIONS" :key="name">
                      <template v-if="step.payload.proposal.narrative[name]?.length">
                        <h4>{{ SECTION_LABEL[name] }}</h4>
                        <ul><li v-for="(parts, i) in step.payload.proposal.narrative[name]" :key="i"><ReportSegments :parts="parts" :metrics="scoped(run, step.payload.proposal.metrics_set)" :seek-task="seekTask" @seek="emit('seek', $event)" /></li></ul>
                      </template>
                    </template>
                  </div>
                  <p v-if="auditCount(step.payload.proposal.audit)" class="ui-banner ui-banner-warn"><IconAlertTriangle /><span>草稿仍有 {{ auditCount(step.payload.proposal.audit) }} 处未通过审计，已在上方标出。可以拒绝并说明修改要求。</span></p>
                </template>
                <p v-else class="prose">为{{ videoName(step.payload.proposal) }}排队一次{{ KIND[step.payload.proposal.kind] }}分析，使用模型 <span class="mono">{{ step.payload.proposal.model_id }}</span> 和默认参数。</p>

                <div v-if="step.status === 'pending' && run.status === 'awaiting_approval'" class="decide">
                  <label class="field"><span>备注（可选，会发给 Agent）</span><input v-model="notes[step.payload.tool_call_id]" class="input" maxlength="500" placeholder="例如 先补充环境数据再保存" /></label>
                  <div class="decide-actions">
                    <button class="btn btn-primary" :disabled="!!deciding" @click="decide(run, step, true)">{{ deciding === step.payload.tool_call_id + 'approve' ? '正在执行…' : APPROVE[step.payload.tool] }}</button>
                    <button class="btn" :disabled="!!deciding" @click="decide(run, step, false)">拒绝</button>
                  </div>
                </div>
                <p v-else-if="step.payload.outcome?.report_id" class="outcome"><button class="btn btn-sm" @click="emit('open-report', step.payload.outcome.report_id)"><IconFileText />打开报告</button></p>
                <p v-else-if="step.payload.outcome?.run_id" class="note">分析已排队，完成后可以在工作台查看。</p>
                <p v-else-if="step.payload.note" class="note">你的备注：{{ step.payload.note }}</p>
              </div>

              <details v-else-if="step.kind === 'tool'" class="tool">
                <summary>
                  <span class="step-title">{{ step.title }}</span>
                  <span class="note truncate">{{ step.status === 'error' ? toolError(step) : step.payload.summary }}</span>
                  <span v-if="step.duration_ms != null" class="note tnum dur">{{ formatMs(step.duration_ms) }}</span>
                </summary>
                <div class="tool-body">
                  <span class="eyebrow">参数</span>
                  <pre class="mono">{{ JSON.stringify(step.payload.arguments, null, 2) }}</pre>
                  <template v-if="step.payload.metric_ids?.length">
                    <span class="eyebrow">返回的指标 <span class="tnum">{{ step.payload.metric_ids.length }}</span></span>
                    <ul class="ledger-list">
                      <li v-for="id in step.payload.metric_ids.slice(0, 12)" :key="id"><span class="mono truncate" :title="id">{{ id }}</span>
                        <button v-if="seekable(run.ledger[id])" type="button" class="seek tnum" :title="`跳到 ${metricText(run, id)}`" @click="emit('seek', run.ledger[id].seek_s)"><IconPlayerPlay aria-hidden="true" />{{ metricText(run, id) }}</button>
                        <span v-else class="tnum">{{ metricText(run, id) }}</span></li>
                    </ul>
                    <span v-if="step.payload.metric_ids.length > 12" class="note">其余 {{ step.payload.metric_ids.length - 12 }} 项见右侧证据</span>
                  </template>
                </div>
              </details>

              <div v-else-if="step.kind === 'review'" class="line">
                <span class="step-title">{{ step.title }}</span>
                <span v-if="step.payload.audit" class="note">{{ auditText(step.payload.audit) }}</span>
                <span v-if="step.payload.round" class="note tnum">第 {{ step.payload.round }} / {{ run.limits.revisions }} 次</span>
              </div>
              <div v-else-if="step.kind === 'plan'" class="line"><span class="step-title">{{ step.title }}</span><span class="note tnum">{{ step.payload.summary }}</span></div>
              <AgentMarkdown v-else-if="step.kind === 'message'" class="message" :parts="[{ text: step.payload.text }]" />
              <div v-else-if="step.kind === 'error'" class="line"><span class="step-title">{{ step.title }}</span><span class="note">{{ step.payload.error_text || RUN_ERRORS[step.payload.error] || step.payload.error }}</span></div>
              <div v-else class="line"><span class="step-title">{{ step.title }}</span></div>
            </li>
          </ol>

          <div v-if="run.answer" class="answer">
            <span class="eyebrow">Agent</span>
            <AgentMarkdown class="answer-text" :parts="run.answer.segments" :metrics="run.ledger" :seek-task="seekTask" @seek="emit('seek', $event)" />
            <p v-if="run.answer.audit.unverified_numbers.length" class="note">有 {{ run.answer.audit.unverified_numbers.length }} 处数字没有对应的平台指标，已标出，请勿直接引用。</p>
          </div>

          <footer class="run-foot">
            <span v-if="ACTIVE.includes(run.status)" class="status" role="status"><IconLoader2 v-if="run.status !== 'awaiting_approval'" class="spin" />{{ STATUS[run.status] }}</span>
            <span v-else-if="run.status === 'failed'" class="status failed">{{ RUN_ERRORS[run.error_code] || `未完成：${run.error_code}` }}</span>
            <span v-else-if="run.status === 'cancelled'" class="status">已停止</span>
            <span class="note tnum">{{ usageText(run) }}</span>
            <button v-if="ACTIVE.includes(run.status)" class="btn btn-sm" :disabled="stopping" @click="stop(run)"><IconPlayerStop />停止</button>
          </footer>
          <p v-if="stalled && run === lastRun" class="ui-banner ui-banner-warn"><IconAlertTriangle /><span>任务还在排队，Agent Worker 可能没有运行。在后端目录运行 <code class="mono">python manage.py run_agent_worker</code> 后会自动继续。</span></p>
        </article>

      </div>

      <form class="composer" @submit.prevent="send">
        <div class="composer-box" :class="{ disabled: !enabled || active }">
          <label class="sr-only" :for="`${uid}-input`">{{ session ? '继续提问' : '描述任务' }}</label>
          <textarea :id="`${uid}-input`" ref="inputRef" v-model="draft" class="composer-input" :rows="dock ? 2 : 3" maxlength="4000" :disabled="!enabled || active"
                    :placeholder="placeholder" @keydown.enter.ctrl.prevent="send" @keydown.enter.meta.prevent="send" />
          <div class="composer-foot">
            <span class="note">Ctrl + Enter 发送</span>
            <button class="btn btn-primary btn-sm" :disabled="!enabled || active || sending || !draft.trim()"><IconSend />{{ session ? '发送' : '开始任务' }}</button>
          </div>
        </div>
        <p v-if="sendError" class="error" role="alert">{{ sendError }}</p>
      </form>

      <component :is="dock ? 'details' : 'aside'" class="rail" aria-label="任务上下文">
        <summary v-if="dock" class="rail-summary"><IconListCheck aria-hidden="true" /><span class="truncate">{{ planSummary }}</span><span class="note tnum">证据 {{ evidenceCount || 0 }}</span></summary>
        <section>
          <h3 class="eyebrow">计划</h3>
          <ol v-if="plan.length" class="plan">
            <li v-for="(item, i) in plan" :key="i" :class="`plan-${item.status}`"><component :is="PLAN_ICON[item.status]" aria-hidden="true" /><span>{{ item.title }}</span><span class="sr-only">（{{ PLAN_LABEL[item.status] }}）</span></li>
          </ol>
          <p v-else class="note">开始任务后，Agent 的计划会显示在这里。</p>
        </section>
        <section>
          <h3 class="eyebrow">证据 <span class="tnum">{{ evidenceCount }}</span></h3>
          <p v-if="!evidence.length" class="note">工具返回的指标会登记为证据，回答只能引用这些 ID。</p>
          <details v-for="group in evidence" :key="group.prefix" class="evidence">
            <summary><span class="mono">{{ group.prefix }}</span><span>{{ group.label }}</span><span class="note tnum">{{ group.items.length }}</span></summary>
            <ul class="ledger-list">
              <li v-for="item in group.items" :key="item.id"><span class="truncate" :title="`${item.id} · ${item.label}`">{{ item.label }}</span>
                <button v-if="seekable(item.metric)" type="button" class="seek tnum" :title="`跳到 ${item.text}`" @click="emit('seek', item.metric.seek_s)"><IconPlayerPlay aria-hidden="true" />{{ item.text }}</button>
                <span v-else class="tnum">{{ item.text }}</span></li>
            </ul>
          </details>
        </section>
        <section v-if="lastRun">
          <h3 class="eyebrow">本轮预算</h3>
          <dl class="budget tnum">
            <div><dt>模型轮次</dt><dd>{{ lastRun.usage.turns || 0 }} / {{ lastRun.limits.turns }}</dd></div>
            <div><dt>工具调用</dt><dd>{{ lastRun.usage.tool_calls || 0 }} / {{ lastRun.limits.tool_calls }}</dd></div>
            <div><dt>审计退回</dt><dd>{{ lastRun.usage.revisions || 0 }} / {{ lastRun.limits.revisions }}</dd></div>
          </dl>
        </section>
      </component>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, useId, watch } from 'vue'
import { IconAlertCircle, IconAlertTriangle, IconCircleCheck, IconCircleDashed, IconCircleDot, IconCircleMinus, IconCircleX, IconFileText, IconListCheck, IconLoader2,
  IconMessage2, IconPlayerPlay, IconPlayerStop, IconPlus, IconSend, IconShieldCheck, IconSparkles, IconTool, IconTrash, IconUserCheck } from '@tabler/icons-vue'
import UiSelect from './ui/UiSelect.vue'
import ReportSegments from './ReportSegments.vue'
import AgentMarkdown from './AgentMarkdown.vue'
import { listAgentSessions, createAgentSession, listTaskAgentSessions, createTaskAgentSession, getAgentSession, updateAgentSession, deleteAgentSession, sendAgentMessage,
  getAgentRun, decideAgentProposal, cancelAgentRun, listSites } from '../api'
import { agentDialogOpen } from '../lib/reportAgent'
import { confirmDialog } from '../lib/dialogs'
import { formatDateTime } from '../lib/format'
import { toast } from '../lib/toast'

// A site session lives on the reports page; a task session docks beside the monitoring wall's video,
// sends the playback context with every message and can seek the video.
const props = defineProps({ siteId: String, taskId: Number, context: Function, dock: Boolean, enabled: Boolean })
const emit = defineEmits(['open-report', 'report-saved', 'seek'])

const STARTERS = ['分析最近一次观测，指出鱼类最活跃的时段和值得人工复核的珊瑚帧', '检查哪些视频还缺少鱼类或珊瑚分析，需要的话提议补跑', '用已完成的分析起草一份观测报告，提交给我审阅']
const WALL_STARTERS = ['现在画面里有多少鱼？和整段视频相比算多吗？', '这段视频鱼类最活跃的是哪段时间？带我跳过去看', '当前画面附近的珊瑚有白化吗？哪些采样帧值得复核？']
const ACTIVE = ['queued', 'running', 'awaiting_approval', 'applying']
const STATUS = { queued: '排队中', running: 'Agent 正在工作', awaiting_approval: '等待你批准', applying: '正在执行你批准的操作' }
const KIND = { fish: '鱼类', coral: '珊瑚' }
const SECTIONS = ['observations', 'interpretation', 'limitations', 'next_steps']
const SECTION_LABEL = { observations: '观测', interpretation: '解读', limitations: '限制', next_steps: '下一步' }
const APPROVE = { propose_observation_report: '保存报告', propose_analysis_run: '排队分析' }
const DECISION = { pending: { label: '待批准', tone: 'tag-warn' }, approved: { label: '已批准', tone: 'tag-accent' }, rejected: { label: '已拒绝', tone: '' }, failed: { label: '执行失败', tone: 'tag-danger' } }
const PLAN_ICON = { pending: IconCircleDashed, in_progress: IconCircleDot, done: IconCircleCheck, skipped: IconCircleMinus }
const PLAN_LABEL = { pending: '待办', in_progress: '进行中', done: '已完成', skipped: '已跳过' }
const NAMESPACE = { S: '观测指标', T: '活动时间线', W: '时间窗', C: '采样帧复核', E: 'CRW 警报', H: '历史报告', V: '视频', SITE: '观测点' }
const RUN_ERRORS = {
  agent_budget_exhausted: '达到步骤上限，Agent 没能给出回答。缩小任务范围后重试。', cancelled_by_user: '已停止。', worker_lease_expired: 'Agent Worker 中断，任务没有完成。重新发送即可。',
  agent_disabled: '模型服务未启用。', agent_output_truncated: '回答超过输出长度上限。调高最大输出 tokens 或缩小任务范围。', agent_internal_error: 'Agent 运行出错。查看后端日志后重试。',
  unknown_tool: '模型调用了不存在的工具，已告知模型。', invalid_arguments: '模型给出的参数不是有效 JSON，已告知模型。'
}
const SEND_ERRORS = { agent_disabled: '模型服务未启用。', run_in_progress: '当前任务还没结束。', invalid_message: '任务描述填写 1–4000 字。', invalid_context: '无法读取当前画面，刷新页面后重试。', unknown_site: '所选观测点不存在，重新选择。' }

const sessions = ref([]), sessionId = ref(null), session = ref(null)
const draft = ref(''), sending = ref(false), sendError = ref(''), deciding = ref(''), stopping = ref(false)
// The reports page and the wall can both keep a workspace mounted, so element IDs are per instance.
const uid = useId()
const notes = reactive({}), stalled = ref(false), threadRef = ref(null), inputRef = ref(null)
const sites = ref([]), pendingSite = ref('')
let timer = null, queuedSince = 0

const placeholder = computed(() => active.value ? '等待当前任务完成…'
  : props.taskId != null ? (session.value ? '继续追问，例如 那 30 秒之后呢？' : '例如 现在画面里的鱼比平时多吗？')
  : session.value ? '继续追问，例如 换成 10 秒一段再看一次' : '例如 分析最近一次观测，指出值得人工复核的时段')
const starters = computed(() => props.taskId != null ? WALL_STARTERS : STARTERS)
const seekTask = computed(() => props.taskId ?? null)
const seekable = item => props.taskId != null && item?.seek_s != null && item.task_id === props.taskId
const filedSite = computed(() => session.value ? session.value.site_id || '' : pendingSite.value)
const siteOptions = computed(() => [{ value: '', label: '不归档' }, ...sites.value.map(item => ({ value: item.id, label: item.name }))])
const siteLabel = computed(() => siteOptions.value.find(o => o.value === filedSite.value)?.label)
const planSummary = computed(() => {
  if (!plan.value.length) return '计划与证据'
  const current = plan.value.find(item => item.status === 'in_progress') || plan.value.findLast(item => item.status === 'done') || plan.value[0]
  return `${plan.value.filter(item => item.status === 'done').length}/${plan.value.length} · ${current.title}`
})
const sessionOptions = computed(() => sessions.value.map(item => ({ value: item.id, label: item.title, hint: formatDateTime(item.updated_at) })))
const lastRun = computed(() => session.value?.runs.at(-1) || null)
const active = computed(() => !!lastRun.value && ACTIVE.includes(lastRun.value.status))
const plan = computed(() => [...(session.value?.runs || [])].reverse().find(run => run.plan?.length)?.plan || [])
const evidence = computed(() => {
  const groups = {}
  for (const [id, item] of Object.entries(lastRun.value?.ledger || {})) {
    const prefix = id.split('.')[0]
    ;(groups[prefix] ||= { prefix, label: NAMESPACE[prefix.replace(/\d+$/, '')] || '', items: [] }).items.push({ id, label: item.label, text: valueText(item), metric: item })
  }
  return Object.values(groups)
})
const evidenceCount = computed(() => evidence.value.reduce((sum, group) => sum + group.items.length, 0) || '')

const valueText = item => item.value == null ? 'N/A' : (item.user_display || item.display)
const metricText = (run, id) => run.ledger[id] ? valueText(run.ledger[id]) : ''
function scoped(run, prefix) {
  return Object.fromEntries(Object.entries(run.ledger).filter(([id]) => id.startsWith(prefix + '.')).map(([id, item]) => [id.slice(prefix.length + 1), item]))
}
const videoName = proposal => proposal.filename ? `“${proposal.filename}”` : `视频 #${proposal.video_id} `
const auditCount = audit => audit.unknown_metrics.length + audit.unknown_citations.length + audit.unverified_numbers.length
function auditText(audit) {
  return [audit.unknown_metrics.length && `${audit.unknown_metrics.length} 个未知指标`, audit.unknown_citations.length && `${audit.unknown_citations.length} 个未知引用`,
    audit.unverified_numbers.length && `${audit.unverified_numbers.length} 处裸数字`].filter(Boolean).join('、')
}
const toolError = step => step.payload.detail || RUN_ERRORS[step.payload.error] || step.payload.error
const formatMs = ms => ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
function usageText(run) {
  const u = run.usage || {}
  if (!u.turns) return ''
  return `${u.turns} 轮 · ${u.tool_calls} 次工具调用` + (u.input_tokens ? ` · ${(u.input_tokens + u.output_tokens).toLocaleString('zh-CN')} tokens` : '')
}
function stepIcon(step) {
  if (step.status === 'error') return IconAlertCircle
  if (step.kind === 'review') return step.status === 'warning' ? IconAlertTriangle : IconShieldCheck
  if (step.kind === 'approval') return step.status === 'rejected' ? IconCircleX : IconUserCheck
  return { plan: IconListCheck, tool: IconTool, message: IconMessage2, resume: IconPlayerPlay, error: IconAlertCircle }[step.kind] || IconCircleDot
}

function explain(err, table) {
  const code = err.response?.data?.error?.code
  return table[code] || (code ? `无法完成：${code}` : '无法连接后端。检查连接后重试。')
}

async function loadSessions() {
  try {
    sessions.value = (await (props.taskId != null ? listTaskAgentSessions(props.taskId) : listAgentSessions(props.siteId))).data.items
  } catch {
    sessions.value = []
  }
}

async function openSession(id) {
  stopPolling()
  sessionId.value = id
  session.value = id ? (await getAgentSession(id)).data : null
  poll()
}

function newSession() {
  stopPolling()
  sessionId.value = null
  session.value = null
  draft.value = ''
}

async function send() {
  const text = draft.value.trim()
  if (!text || active.value || sending.value) return
  sending.value = true
  sendError.value = ''
  try {
    const context = props.context?.()
    if (session.value) {
      session.value.runs.push((await sendAgentMessage(session.value.id, text, context)).data)
    } else {
      const created = (props.taskId != null
        ? await createTaskAgentSession(props.taskId, { text, context, site_id: pendingSite.value || null })
        : await createAgentSession(props.siteId, text)).data
      await loadSessions()
      sessionId.value = created.id
      session.value = created
    }
    draft.value = ''
    scrollToEnd(true)
    poll()
  } catch (err) {
    sendError.value = explain(err, SEND_ERRORS)
  } finally {
    sending.value = false
  }
}

function stopPolling() {
  clearTimeout(timer)
  timer = null
  stalled.value = false
}

// Active runs are polled for new steps only; an approval pause waits for the person instead.
function poll() {
  stopPolling()
  const run = lastRun.value
  if (!run || !['queued', 'running'].includes(run.status)) return
  timer = setTimeout(async () => {
    try {
      const fresh = (await getAgentRun(run.id, run.steps.at(-1)?.index || 0)).data
      const steps = fresh.steps
      const follow = nearEnd()
      Object.assign(run, { ...fresh, steps: run.steps.concat(steps) })
      if (steps.length || fresh.answer) scrollToEnd(follow)
      if (run.status === 'queued') queuedSince ||= Date.now()
      else queuedSince = 0
      if (run.status === 'completed' || run.status === 'failed') loadSessions()
    } catch {
      // A transient error keeps the last known state; the next tick retries.
    }
    poll()
    stalled.value = run.status === 'queued' && queuedSince > 0 && Date.now() - queuedSince > 15000
  }, 1000)
}

// The docked thread follows new steps unless the observer has scrolled up to read.
function nearEnd() {
  const el = threadRef.value
  return !!el && el.scrollHeight - el.scrollTop - el.clientHeight < 120
}
function scrollToEnd(follow) {
  if (props.dock && follow) nextTick(() => threadRef.value?.scrollTo({ top: threadRef.value.scrollHeight }))
}

async function fileTo(siteId) {
  if (!session.value) { pendingSite.value = siteId; return }
  try {
    session.value = { ...session.value, ...(await updateAgentSession(session.value.id, { site_id: siteId || null })).data }
    toast({ title: siteId ? '已归档到观测点' : '已取消归档', desc: siteId ? siteLabel.value : undefined, type: 'success' })
  } catch {
    toast({ title: '无法归档会话', desc: '检查后端连接后重试。', type: 'error' })
  }
}

async function decide(run, step, approve) {
  const id = step.payload.tool_call_id
  deciding.value = id + (approve ? 'approve' : 'reject')
  try {
    const result = (await decideAgentProposal(run.id, { tool_call_id: id, decision: approve ? 'approve' : 'reject', note: notes[id] || '' })).data
    Object.assign(run, result.run)
    if (result.outcome.report_id) {
      toast({ title: '已保存报告', desc: result.outcome.title, type: 'success' })
      emit('report-saved')
    } else if (result.outcome.error) {
      toast({ title: '操作没有执行成功', desc: '已告知 Agent，它会说明下一步。', type: 'alert' })
    }
    queuedSince = 0
    poll()
  } catch (err) {
    toast({ title: '无法提交决定', desc: explain(err, { no_pending_proposal: '这项提议已经处理过。刷新会话查看最新状态。' }), type: 'error' })
  } finally {
    deciding.value = ''
  }
}

async function stop(run) {
  stopping.value = true
  try {
    Object.assign(run, (await cancelAgentRun(run.id)).data)
    poll()
  } catch (err) {
    toast({ title: '无法停止任务', desc: explain(err, { run_not_active: '任务已经结束。' }), type: 'error' })
  } finally {
    stopping.value = false
  }
}

async function removeSession() {
  const ok = await confirmDialog({ title: `删除会话“${session.value.title}”？`, description: '会话中的计划、工具记录和回答会一起删除；已保存的报告不受影响。', confirmLabel: '删除会话', danger: true })
  if (!ok) return
  try {
    await deleteAgentSession(session.value.id)
    newSession()
    await loadSessions()
  } catch {
    toast({ title: '无法删除会话', desc: '检查后端连接后重试。', type: 'error' })
  }
}

watch(() => [props.siteId, props.taskId], async () => {
  newSession()
  await loadSessions()
  if (sessions.value.length) await openSession(sessions.value[0].id)
  scrollToEnd(true)
}, { immediate: true })
watch(() => props.taskId, async id => { if (id != null && !sites.value.length) sites.value = (await listSites().catch(() => ({ data: { items: [] } }))).data.items }, { immediate: true })
// Opening the docked assistant puts the cursor in the composer once it accepts input.
watch(() => props.dock && props.enabled, ready => { if (ready) nextTick(() => inputRef.value?.focus()) }, { immediate: true })
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.agent { container: agent / inline-size; }
.session-bar { display: flex; align-items: center; gap: 6px; min-width: 0; }
.filing { display: flex; align-items: center; gap: 8px; min-width: 0; }
.filing > .note { flex: none; }
.filing-select { flex: 1; min-width: 0; max-width: 240px; }
.session-select { width: 240px; min-width: 0; }
.session-bar > .btn { flex: none; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 248px; grid-template-areas: "thread rail" "composer rail"; gap: 18px 20px; align-items: start; }
.thread { grid-area: thread; }
.composer { grid-area: composer; }
.rail { grid-area: rail; }
.thread { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.intro { display: flex; flex-direction: column; gap: 10px; }
.intro .note { max-width: 68ch; }
.starters { display: flex; flex-direction: column; gap: 6px; list-style: none; padding: 0; margin: 0; }
.starter { width: 100%; padding: 8px 10px; border: 0; border-radius: var(--radius); font: inherit; font-size: var(--text-small); text-align: start; color: var(--ink-2); background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); cursor: pointer; transition: background-color 120ms var(--ease), color 120ms var(--ease); }
.starter:hover:not(:disabled) { color: var(--ink); background: var(--surface-3); }
.starter:disabled { cursor: not-allowed; opacity: 0.6; }
.run { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.run + .run { padding-top: 18px; box-shadow: inset 0 1px 0 var(--line); }
.goal { display: flex; flex-direction: column; gap: 2px; align-self: flex-start; max-width: 68ch; padding: 8px 12px; border-radius: var(--radius-lg); background: var(--accent-soft); color: var(--ink); white-space: pre-wrap; overflow-wrap: anywhere; }
.trace { display: flex; flex-direction: column; list-style: none; padding: 0; margin: 0; }
.step { position: relative; display: grid; grid-template-columns: 22px minmax(0, 1fr); gap: 8px; padding-bottom: 8px; }
.step::before { content: ''; position: absolute; inset-inline-start: 10px; top: 20px; bottom: 0; width: 1px; background: var(--line); }
.step:last-child::before { display: none; }
.step-icon { display: grid; place-items: center; width: 22px; height: 20px; color: var(--ink-3); }
.step-icon .tabler-icon { --icon-size: 15px; }
.status-error .step-icon { color: var(--danger); }
.status-warning .step-icon, .status-pending .step-icon { color: var(--warn); }
.status-approved .step-icon, .kind-plan .step-icon { color: var(--accent); }
.line { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; min-width: 0; min-height: 20px; }
.step-title { flex: none; font-weight: 500; color: var(--ink-2); }
.message { gap: 6px; color: var(--ink-2); line-height: 1.55; }
.tool summary { display: flex; align-items: baseline; gap: 8px; min-width: 0; min-height: 20px; cursor: pointer; list-style: none; }
.tool summary::-webkit-details-marker { display: none; }
.tool summary .truncate { flex: 1; min-width: 0; }
.tool summary:hover .step-title { color: var(--ink); }
.dur { flex: none; }
.tool-body { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; padding: 10px 12px; border-radius: var(--radius); background: var(--surface-2); }
.tool-body pre { max-height: 180px; overflow: auto; margin: 0; font-size: var(--text-caption); line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--ink-2); }
.ledger-list { display: flex; flex-direction: column; gap: 3px; list-style: none; padding: 0; margin: 0; font-size: var(--text-small); }
.ledger-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; }
.ledger-list li > :last-child { color: var(--ink); text-align: end; }
.approval { display: flex; flex-direction: column; gap: 10px; min-width: 0; padding: 12px 14px; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line-strong); }
.status-pending .approval { box-shadow: 0 0 0 1px var(--warn), 0 0 0 4px var(--warn-soft); }
.approval-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.draft { display: flex; flex-direction: column; gap: 6px; max-width: 68ch; font-size: var(--text-reading); line-height: 1.65; color: var(--ink-2); }
.draft h4 { margin-top: 4px; font-size: var(--text-small); font-weight: 600; color: var(--ink); }
.draft ul { display: flex; flex-direction: column; gap: 2px; margin: 0; padding-inline-start: 1.2em; }
.decide { display: flex; flex-direction: column; gap: 8px; }
.decide-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.outcome { display: flex; }
.answer { display: flex; flex-direction: column; gap: 4px; }
.answer-text { max-width: 68ch; font-size: var(--text-reading); line-height: 1.7; color: var(--ink); }
.run-foot { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; min-height: 26px; }
.status { display: inline-flex; align-items: center; gap: 6px; font-size: var(--text-small); font-weight: 500; color: var(--ink-2); }
.status.failed { color: var(--danger); }
.spin { --icon-size: 14px; animation: spin 900ms linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
/* One field: the box carries the input tokens and focus ring; the textarea inside is bare and grows with
   its content. Corners stay concentric: box radius-lg (10px) = button radius (6px) + 4px padding. */
.composer { display: flex; flex-direction: column; gap: 6px; }
.composer-box { display: flex; flex-direction: column; gap: 2px; padding: 4px; border-radius: var(--radius-lg); background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); cursor: text; transition: box-shadow 120ms var(--ease); }
.composer-box:hover { box-shadow: inset 0 0 0 1px var(--line-strong); }
.composer-box:focus-within { box-shadow: inset 0 0 0 1px var(--accent), 0 0 0 3px var(--accent-soft); }
.composer-box.disabled { cursor: default; }
.composer-input { display: block; width: 100%; min-height: calc(3lh + 12px); max-height: calc(8lh + 12px); padding: 6px 8px; border: 0; outline: none; font: inherit; font-size: var(--text-body); line-height: 1.5; color: var(--ink); background: transparent; resize: none; field-sizing: content; overflow-y: auto; }
.composer-input::placeholder { color: var(--ink-3); opacity: 0.8; }
.composer-input:disabled { cursor: default; }
.composer-foot { display: flex; align-items: center; gap: 8px; padding-inline-start: 8px; }
.composer-foot .btn { margin-inline-start: auto; }
@media (max-width: 640px) { .composer-input { font-size: 16px; } }
.error { font-size: var(--text-small); color: var(--danger); }
aside.rail { position: sticky; top: 0; display: flex; flex-direction: column; gap: 16px; min-width: 0; padding-inline-start: 16px; box-shadow: inset 1px 0 0 var(--line); }
.rail section { display: flex; flex-direction: column; gap: 8px; }
.seek { display: inline-flex; align-items: center; justify-self: end; gap: 3px; padding: 0 4px; border: 0; border-radius: var(--radius-sm); font: inherit; color: var(--accent); background: transparent; cursor: pointer; }
.seek:hover { background: var(--accent-soft); }
.seek .tabler-icon { --icon-size: 11px; }
.plan { display: flex; flex-direction: column; gap: 6px; list-style: none; padding: 0; margin: 0; font-size: var(--text-small); }
.plan li { display: grid; grid-template-columns: 16px minmax(0, 1fr); gap: 6px; color: var(--ink-2); }
.plan .tabler-icon { --icon-size: 14px; margin-top: 2px; color: var(--ink-3); }
.plan-in_progress { color: var(--ink) !important; font-weight: 500; }
.plan-in_progress .tabler-icon, .plan-done .tabler-icon { color: var(--accent); }
.plan-skipped span:first-of-type { text-decoration: line-through; color: var(--ink-3); }
.evidence summary { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 6px; align-items: baseline; font-size: var(--text-small); cursor: pointer; }
.evidence .ledger-list { margin: 6px 0 4px; }
.budget { display: flex; flex-direction: column; gap: 4px; margin: 0; font-size: var(--text-small); }
.budget div { display: flex; justify-content: space-between; gap: 8px; }
.budget dt { color: var(--ink-3); }
.budget dd { margin: 0; color: var(--ink); }
@container agent (max-width: 760px) {
  .layout { grid-template-columns: minmax(0, 1fr); grid-template-areas: "thread" "composer" "rail"; }
  aside.rail { position: static; padding: 12px 0 0; box-shadow: inset 0 1px 0 var(--line); display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
}
@container agent (max-width: 520px) {
  .session-bar { width: 100%; }
  .session-select { flex: 1; width: auto; }
}
@container agent (max-width: 340px) { .composer-foot > .note { display: none; } }

/* Docked beside the wall's video: header, collapsible context strip, scrolling thread, pinned composer. */
.dock { display: flex; flex-direction: column; gap: 10px; height: 100%; min-height: 0; }
.dock > .ui-card-head { flex-direction: column; align-items: stretch; gap: 8px; }
.dock .layout { display: flex; flex-direction: column; align-items: stretch; flex: 1; min-height: 0; gap: 10px; }
.dock .rail { order: -1; flex: none; display: block; padding: 0; box-shadow: none; border-radius: var(--radius); background: var(--surface-2); }
.dock .rail[open] { max-height: 45%; overflow: auto; }
.dock .rail > section { padding: 0 10px 10px; }
.rail-summary { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 6px; padding: 7px 10px; font-size: var(--text-small); color: var(--ink-2); cursor: pointer; list-style: none; }
.rail-summary::-webkit-details-marker { display: none; }
.rail-summary .tabler-icon { --icon-size: 14px; color: var(--accent); }
.dock .thread { flex: 1; min-height: 0; overflow-y: auto; gap: 14px; padding-inline-end: 4px; overscroll-behavior: contain; }
.dock .run + .run { padding-top: 14px; }
.dock .goal, .dock .answer-text, .dock .draft { max-width: none; }
.dock .composer { flex: none; }
.dock .composer-input { min-height: calc(2lh + 12px); max-height: calc(6lh + 12px); }
</style>
