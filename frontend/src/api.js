import axios from 'axios'

// 开发环境默认使用 5173 代理到 Django，Docker 环境通过 nginx 同源代理
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const http = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000
})

export function uploadVideo(file) {
  const formData = new FormData()
  formData.append('video', file)
  return http.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function startProcess(taskId, payload = {}) {
  return http.post(`/process/${taskId}`, payload)
}

export function getTask(taskId) {
  return http.get(`/task/${taskId}`)
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
