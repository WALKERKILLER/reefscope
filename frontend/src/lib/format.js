export function formatClock(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00.0'
  const m = Math.floor(seconds / 60)
  const s = seconds - m * 60
  return `${m}:${s.toFixed(1).padStart(4, '0')}`
}

export function formatSeconds(seconds, digits = 2) {
  return Number.isFinite(seconds) ? `${seconds.toFixed(digits)} s` : '—'
}

export function metricValue(metric, digits = 3) {
  const value = metric?.value
  if (value == null) return null
  if (Number.isInteger(value)) return value.toLocaleString('zh-CN')
  return Number(value).toFixed(digits)
}

export const MISSING_REASONS = {
  missing_independent_ground_truth: '缺少独立测试真值',
  missing_manual_identity_ground_truth: '缺少人工 ID 真值',
  no_coral_model_or_benthic_roi: '尚无珊瑚分割模型与底栖 ROI',
  no_observations: '窗口内没有观测'
}

export function shortId(id) {
  return id ? String(id).slice(0, 8) : '—'
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
