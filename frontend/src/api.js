import axios from 'axios'

// 开发环境默认使用 5173 代理到 Django，Docker 环境通过 nginx 同源代理
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const http = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000
})

export function uploadVideo(file, signal) {
  const formData = new FormData()
  formData.append('video', file)
  return http.post('/upload', formData, {
    signal,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function startProcess(taskId, payload = {}) {
  return http.post(`/process/${taskId}`, payload)
}

export function getTask(taskId, signal) {
  return http.get(`/task/${taskId}`, { signal })
}

export function listTasks() {
  return http.get('/tasks')
}

export function getConfig() {
  return http.get('/config')
}

export function updateConfig(payload = {}) {
  return http.put('/config', payload)
}

export function deleteTask(taskId) {
  return http.delete(`/task/${taskId}`)
}

export function mutateTask(taskId, payload = {}) {
  return http.patch(`/task/${taskId}`, payload)
}

export function batchMutateTasks(payload = {}) {
  return http.post('/tasks/actions', payload)
}

export function toMediaUrl(path) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${API_BASE_URL}${path}`
}

export const listAnalysisModels = (signal) => http.get('/v1/models', { signal })
export const listAnalysisRuns = (taskId, signal) => http.get(`/v1/tasks/${taskId}/analysis-runs`, { signal })
export const createAnalysisRun = (taskId, payload) => http.post(`/v1/tasks/${taskId}/analysis-runs`, payload)
export const getAnalysisRun = (id, signal) => http.get(`/v1/analysis-runs/${id}`, { signal })
export const retryAnalysisRun = (id) => http.post(`/v1/analysis-runs/${id}/retry`)
export const getAnalysisTracks = (id, params, signal) => http.get(`/v1/analysis-runs/${id}/tracks`, { params, signal })
export const getAnalysisHeatmap = (id, params, signal) => http.get(`/v1/analysis-runs/${id}/heatmap`, { params, signal })
export const getAnalysisSummary = (id, params, signal) => http.get(`/v1/analysis-runs/${id}/summary`, { params, signal })
export const downloadAnalysis = (id, resource, params) => http.get(`/v1/analysis-runs/${id}/${resource}`, { params, responseType: 'blob' })

export const getModelResearch = (id, signal) => http.get(`/v1/model-versions/${encodeURIComponent(id)}/history`, { signal })
export const getTrainingReport = (id, signal) => http.get(`/v1/reports/${id}`, { signal })
export const downloadTrainingReport = (id) => http.get(`/v1/reports/${id}/export`, { params: { export: 'markdown' }, responseType: 'blob' })
export const reportPrintUrl = (id) => `${API_BASE_URL}/api/v1/reports/${encodeURIComponent(id)}/export?export=html`
