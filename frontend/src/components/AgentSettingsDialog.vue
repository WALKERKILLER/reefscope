<template>
  <DialogRoot :open="open" @update:open="emit('update:open', $event)">
    <DialogPortal>
      <DialogOverlay class="ui-overlay" />
      <DialogContent class="ui-dialog agent-dialog" @open-auto-focus="reset">
        <DialogTitle class="ui-dialog-title">模型服务</DialogTitle>
        <DialogDescription class="ui-dialog-desc">连接兼容 OpenAI Chat Completions 或 Anthropic Messages 的服务，供 Agent 分析和报告文字解读使用；Agent 需要服务支持工具调用。报告中的数值始终由平台计算。</DialogDescription>
        <form class="form" novalidate @submit.prevent="save">
          <div class="field">
            <span id="agent-format">接口格式</span>
            <UiSegmented v-model="draft.api_format" :options="FORMATS" aria-label="接口格式" block />
          </div>
          <label class="field">
            <span>Base URL</span>
            <input v-model.trim="draft.base_url" class="input mono" type="url" inputmode="url" autocomplete="off" spellcheck="false" :placeholder="draft.api_format === 'openai_chat' ? 'https://api.example.com/v1' : 'https://api.example.com'" />
          </label>
          <p v-if="endpoint" class="note">请求地址 <span class="mono">{{ endpoint }}</span></p>
          <label class="field">
            <span>模型</span>
            <input v-model.trim="draft.model" class="input mono" autocomplete="off" spellcheck="false" placeholder="服务商提供的模型 ID" />
          </label>
          <label class="field">
            <span>API Key</span>
            <input v-model="draft.api_key" class="input mono" type="password" autocomplete="new-password" spellcheck="false" :placeholder="config?.key_configured ? `已保存${config.key_hint ? `，末尾 ${config.key_hint}` : ''}。留空则保持不变` : '粘贴 API Key'" />
          </label>
          <p class="note">
            <template v-if="urlChanged && config?.key_configured && !draft.api_key">修改地址后，已保存的 Key 会被清除，需要重新填写。</template>
            <template v-else>Key 只保存在服务器本地的私有文件中，不会回显。</template>
            <button v-if="config?.key_configured" type="button" class="ui-link" @click="clearKey">清除已保存的 Key</button>
          </p>
          <div class="pair">
            <label class="field"><span>超时（秒）</span><input v-model.number="draft.timeout_seconds" class="input tnum" type="number" min="5" max="100" step="1" /></label>
            <label v-if="draft.api_format === 'anthropic_messages'" class="field"><span>最大输出 tokens</span><input v-model.number="draft.max_output_tokens" class="input tnum" type="number" min="256" max="32000" step="256" /></label>
          </div>
          <div class="toggle">
            <UiSwitch id="agent-enabled" v-model="draft.enabled" />
            <label for="agent-enabled">启用模型服务</label>
          </div>
          <div class="ui-banner ui-banner-info"><IconInfoCircle /><span>生成报告时，所选视频的统计值、站点名称、观测日期和录入的环境数据会发送到这个服务。视频画面、文件名和坐标不会发送。</span></div>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <p v-if="result" class="result" :data-ok="result.ok" role="status">
            <component :is="result.ok ? IconCircleCheck : IconAlertTriangle" />
            <span v-if="result.ok">连接正常 · <span class="tnum">{{ (result.latency_ms / 1000).toFixed(1) }} s</span><template v-if="result.model"> · <span class="mono">{{ result.model }}</span></template></span>
            <span v-else>{{ result.error_text || result.error_code }}<template v-if="result.http_status">（HTTP {{ result.http_status }}）</template></span>
          </p>
          <div class="ui-dialog-actions">
            <UiTooltip :text="dirty ? '先保存，再测试' : '用已保存的设置发送一次测试请求'">
              <span><button type="button" class="btn" :disabled="dirty || !config?.key_configured || testing" @click="test"><IconPlugConnected />{{ testing ? '正在测试…' : '测试连接' }}</button></span>
            </UiTooltip>
            <span class="spacer" />
            <DialogClose type="button" class="btn btn-ghost">关闭</DialogClose>
            <button class="btn btn-primary" :disabled="!dirty || saving">{{ saving ? '正在保存…' : '保存' }}</button>
          </div>
        </form>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from 'reka-ui'
import { IconAlertTriangle, IconCircleCheck, IconInfoCircle, IconPlugConnected } from '@tabler/icons-vue'
import UiSegmented from './ui/UiSegmented.vue'
import UiSwitch from './ui/UiSwitch.vue'
import UiTooltip from './ui/UiTooltip.vue'
import { saveReportAgent, testReportAgent } from '../api'
import { agentConfig as config, loadAgentConfig, previewEndpoint, AGENT_CONFIG_ERRORS } from '../lib/reportAgent'
import { toast } from '../lib/toast'

defineProps({ open: Boolean })
const emit = defineEmits(['update:open'])
const FORMATS = [{ value: 'openai_chat', label: 'OpenAI 兼容' }, { value: 'anthropic_messages', label: 'Anthropic Messages' }]
const FIELDS = ['api_format', 'base_url', 'model', 'timeout_seconds', 'max_output_tokens', 'enabled']
const draft = reactive({ api_format: 'openai_chat', base_url: '', model: '', timeout_seconds: 60, max_output_tokens: 4096, enabled: false, api_key: '' })
const saving = ref(false), testing = ref(false), error = ref(''), result = ref(null)

const endpoint = computed(() => previewEndpoint(draft.api_format, draft.base_url))
const urlChanged = computed(() => (draft.base_url || '').replace(/\/+$/, '') !== (config.value?.base_url || ''))
const dirty = computed(() => !!draft.api_key || FIELDS.some(key => config.value && draft[key] !== config.value[key]))

async function reset() {
  error.value = ''
  result.value = null
  const current = config.value || await loadAgentConfig()
  if (current) for (const key of FIELDS) draft[key] = current[key]
  draft.api_key = ''
}

async function submit(payload, message) {
  saving.value = true
  error.value = ''
  try {
    config.value = (await saveReportAgent(payload)).data
    draft.api_key = ''
    for (const key of FIELDS) draft[key] = config.value[key]
    toast({ title: message, type: 'success' })
  } catch (err) {
    const code = err.response?.data?.error?.code
    error.value = AGENT_CONFIG_ERRORS[code] || (code ? `无法保存：${code}` : '无法连接后端。检查连接后重试。')
  } finally {
    saving.value = false
  }
}

function save() {
  const payload = Object.fromEntries(FIELDS.map(key => [key, draft[key]]))
  if (draft.api_key.trim()) payload.api_key = draft.api_key.trim()
  result.value = null
  return submit(payload, '已保存模型服务设置')
}

function clearKey() {
  result.value = null
  return submit({ clear_api_key: true, enabled: false }, '已清除 API Key')
}

async function test() {
  testing.value = true
  result.value = null
  try {
    result.value = (await testReportAgent()).data
  } catch {
    result.value = { ok: false, error_text: '无法连接后端。检查连接后重试。' }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.agent-dialog { width: min(520px, calc(100vw - 32px)); max-height: calc(100dvh - 32px); overflow-y: auto; }
.form { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.form > .note { margin-top: -6px; overflow-wrap: anywhere; }
.form > .note .ui-link { margin-inline-start: 6px; }
.pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.toggle { display: flex; align-items: center; gap: 8px; font-size: var(--text-small); }
.toggle label { cursor: pointer; }
.error { font-size: var(--text-small); color: var(--danger); }
.result { display: flex; align-items: center; gap: 6px; font-size: var(--text-small); color: var(--danger); }
.result[data-ok=true] { color: var(--ok); }
.result .tabler-icon { --icon-size: 14px; flex: none; }
.ui-dialog-actions { align-items: center; }
.spacer { flex: 1; }
</style>
