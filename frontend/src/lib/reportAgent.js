import { ref } from 'vue'
import { getReportAgent } from '../api'

// One copy of the report-agent settings, shared by the top-bar dialog and the reports page.
export const agentConfig = ref(null)
export const agentDialogOpen = ref(false)

export async function loadAgentConfig() {
  try {
    agentConfig.value = (await getReportAgent()).data
  } catch {
    agentConfig.value = null
  }
  return agentConfig.value
}

// Mirrors `agent.endpoint` on the backend, which stays authoritative; used only to preview unsaved input.
export function previewEndpoint(format, baseUrl) {
  const base = (baseUrl || '').trim().replace(/\/+$/, '')
  if (!base) return ''
  if (format === 'openai_chat') return base.endsWith('/chat/completions') ? base : `${base}/chat/completions`
  if (base.endsWith('/messages')) return base
  return `${base}${base.endsWith('/v1') ? '/messages' : '/v1/messages'}`
}

export const AGENT_CONFIG_ERRORS = {
  invalid_base_url: '填写以 http:// 或 https:// 开头的地址，不含账号、查询参数或 #。',
  invalid_model: '模型 ID 只能包含字母、数字和 . _ : / @ + -。',
  invalid_api_key: 'API Key 应为 8–400 个可见字符，不含空格。',
  invalid_timeout: '超时填写 5–100 秒。',
  invalid_max_output_tokens: '最大输出 tokens 填写 256–32000。',
  agent_config_incomplete: '启用前需要填写接口地址、模型和 API Key。'
}
