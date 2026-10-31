<template>
  <TooltipProvider :delay-duration="350">
    <div class="app" :data-view="activeView">
      <header class="topbar">
        <div class="brand">
          <svg class="mark" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9.25" fill="none" stroke="currentColor" stroke-width="1.5" /><path d="M5 13.5c1.75 0 1.75-1.5 3.5-1.5s1.75 1.5 3.5 1.5 1.75-1.5 3.5-1.5 1.75 1.5 3.5 1.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" /></svg>
          <span class="brand-name">ReefScope</span>
          <span class="brand-sub">水下生态视频分析</span>
        </div>
        <nav class="nav" aria-label="主导航">
          <button v-for="item in views" :key="item.value" class="nav-item" :aria-current="activeView === item.value ? 'page' : undefined" @click="activeView = item.value">
            <component :is="item.icon" />{{ item.label }}
          </button>
        </nav>
        <div class="top-actions">
          <UiTooltip v-if="activeView === 'monitor'" text="全屏展示" shortcut="F">
            <button class="btn btn-ghost btn-icon" aria-label="全屏展示" @click="toggleFullscreen"><IconMaximize /></button>
          </UiTooltip>
          <UiTooltip :text="isDarkTheme ? '切换到浅色' : '切换到深色'">
            <button class="btn btn-ghost btn-icon" :aria-label="isDarkTheme ? '切换到浅色' : '切换到深色'" @click="isDarkTheme = !isDarkTheme">
              <IconSun v-if="isDarkTheme" /><IconMoon v-else />
            </button>
          </UiTooltip>
        </div>
      </header>

      <main class="main">
        <div v-show="activeView !== 'records'" ref="layoutRef" class="layout" :class="{ wall: activeView === 'monitor' }" :style="layoutStyle">
          <div v-show="activeView === 'console'" class="area-library">
            <LibraryPanel
              :history="history"
              :current-id="currentTaskId"
              :config-file="configFileEntry"
              :selection-mode="selectionMode"
              :selected-ids="selectedFileIds"
              @file-select="handleFileSelect"
              @file-action="handleSingleFileAction"
              @file-batch-action="handleBatchFileAction"
              @toggle-select="toggleFileSelection"
              @selection-mode-change="setSelectionMode"
              @file-drop="handleFileDrop"
            />
          </div>
          <div v-show="activeView === 'console'" class="handle handle-left" role="separator" aria-orientation="vertical" aria-label="调整视频库宽度" @pointerdown="startResize('left', $event)" />

          <div v-if="activeView === 'monitor'" class="area-head">
            <MonitorView :analysis="analysisState" :file-name="fileName" @layer="(key, value) => analysisPanelRef?.setLayer(key, value)" />
          </div>

          <div class="area-center">
            <ConfigEditor
              v-if="workspaceMode === 'config'"
              class="grow"
              :file-name="configFileEntry.name"
              :content="configContent"
              :save-message="configSaveMessage"
              @update:content="configContent = $event"
              @save="handleSaveConfig"
              @close="handleCloseWorkspace"
            />
            <VideoWorkspace
              v-else
              class="grow"
              :file-name="fileName"
              :status="status"
              :progress="progress"
              :logs="logs"
              :video-url="videoUrl"
              :result-video-url="analysisState ? null : resultVideoUrl"
              :playback-mode="analysisState ? 'overlay' : playbackMode"
              :boxes="boxes"
              :analysis="analysisState"
              :current-time="currentTime"
              @roi-point="point => analysisPanelRef?.addRoiPoint(point)"
              @file-drop="handleFileDrop"
              @close="handleCloseWorkspace"
              @time-update="(t) => currentTime = t"
              @update:playback-mode="playbackMode = $event"
            />
            <div v-if="analysisState?.overview && workspaceMode === 'video'" class="timeline-card">
              <TrackTimeline :spans="analysisState.overview.spans" :frames="analysisState.overview.frames" :duration="analysisState.duration" :current-time="currentTime" :window="analysisState.window" @seek="handleTimelineClick" />
            </div>
          </div>

          <div v-show="activeView === 'console'" class="handle handle-right" role="separator" aria-orientation="vertical" aria-label="调整分析面板宽度" @pointerdown="startResize('right', $event)" />
          <div v-show="activeView === 'console'" class="area-inspector">
            <FishAnalysisPanel v-if="currentTaskId && workspaceMode === 'video'" ref="analysisPanelRef" :task-id="currentTaskId" :current-time="currentTime" :file-name="fileName" :wall="activeView === 'monitor'" @analysis="analysisState = $event" @seek="handleTimelineClick" @toast="toast" />
            <aside v-else class="inspector-empty" aria-label="分析">
              <h2>鱼类分析</h2>
              <ol class="steps">
                <li><span class="num">1</span><div><strong>打开视频</strong><p class="note">从视频库选择，或上传 MP4。</p></div></li>
                <li><span class="num">2</span><div><strong>创建分析</strong><p class="note">选择注册模型，由独立 Worker 逐帧追踪。</p></div></li>
                <li><span class="num">3</span><div><strong>查看证据</strong><p class="note">叠加框、尾迹与热图，按时间窗和 ROI 统计并导出。</p></div></li>
              </ol>
            </aside>
          </div>

          <div v-if="activeView === 'monitor'" class="area-side">
            <WallEvidence :analysis="analysisState" @open-workspace="activeView = 'console'" />
          </div>
        </div>

        <RecordsView v-if="activeView === 'records'" :history="history" @play-record="handlePlayRecord" />
      </main>

      <footer class="statusbar">
        <span class="health" :data-state="health"><span class="dot" />{{ healthText }}</span>
        <span v-if="fileName" class="context truncate"><span>{{ fileName }}</span><template v-if="analysisState?.runId"><span class="sep" />分析 <span class="mono">{{ shortId(analysisState.runId) }}</span></template></span>
        <span class="spacer" />
        <span class="faint">画面坐标分析 · 精度以独立评估为准</span>
      </footer>
    </div>
    <UiToaster />
    <UiDialogHost />
  </TooltipProvider>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, onMounted, defineAsyncComponent, shallowRef } from 'vue'
import { TooltipProvider } from 'reka-ui'
import { IconSun, IconMoon, IconMaximize, IconLayoutColumns, IconDeviceDesktopAnalytics, IconListDetails } from '@tabler/icons-vue'
import { uploadVideo, getTask, listTasks, getConfig, updateConfig, mutateTask, batchMutateTasks, toMediaUrl, listAnalysisModels, listAnalysisRuns, createAnalysisRun, getHealth } from './api'
import LibraryPanel from './components/LibraryPanel.vue'
import VideoWorkspace from './components/VideoWorkspace.vue'
import FishAnalysisPanel from './components/FishAnalysisPanel.vue'
import MonitorView from './components/MonitorView.vue'
import WallEvidence from './components/WallEvidence.vue'
import TrackTimeline from './components/TrackTimeline.vue'
import RecordsView from './components/RecordsView.vue'
import UiTooltip from './components/ui/UiTooltip.vue'
import UiToaster from './components/ui/UiToaster.vue'
import UiDialogHost from './components/ui/UiDialogHost.vue'
import { isDark as isDarkTheme } from './lib/theme'
import { toast } from './lib/toast'
import { confirmDialog, promptDialog } from './lib/dialogs'
import { seekTo } from './lib/playback'
import { shortId } from './lib/format'
const ConfigEditor = defineAsyncComponent(() => import('./components/ConfigEditor.vue'))

const views = [
  { value: 'console', label: '工作台', icon: IconLayoutColumns },
  { value: 'monitor', label: '监测大屏', icon: IconDeviceDesktopAnalytics },
  { value: 'records', label: '记录', icon: IconListDetails }
]
const LEFT_MIN = 220, LEFT_MAX = 400, RIGHT_MIN = 300, RIGHT_MAX = 520, CENTER_MIN = 420

// --- State ---
const analysisState = shallowRef(null)
const analysisPanelRef = ref(null)
const history = ref([])
const status = ref('idle') // 'idle' | 'processing' | 'playing'
const progress = ref(0)
const logs = ref([])
const videoUrl = ref(null)
const resultVideoUrl = ref(null)
const playbackMode = ref('result')
const boxes = shallowRef([])
const currentTime = ref(0)
const fileName = ref('')
const activeView = ref('console')
const currentTaskId = ref(null)
const leftWidth = ref(264)
const rightWidth = ref(352)
const layoutRef = ref(null)
const workspaceMode = ref('video')
const configContent = ref('')
const configSaveMessage = ref('')
const configFileEntry = ref({ id: 'config:pipeline_settings.toml', type: 'config', name: 'pipeline_settings.toml', path: 'config/pipeline_settings.toml' })
const selectionMode = ref(false)
const selectedFileIds = ref([])
const health = ref('checking')

const layoutStyle = computed(() => ({ '--left': `${leftWidth.value}px`, '--right': `${rightWidth.value}px` }))
const healthText = computed(() => ({ online: '后端已连接', offline: '无法连接后端 · 每 15 秒重试', checking: '正在连接后端…' })[health.value])

let workspaceGeneration = 0
let uploadAbort = null
let taskAbort = null
let healthTimer = null
let configSaveTimer = null
let stopResizeListener = null
function invalidateWorkspaceRequests() {
  workspaceGeneration += 1
  uploadAbort?.abort()
  taskAbort?.abort()
}

// --- Layout ---
function startResize(side, event) {
  const container = layoutRef.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  event.currentTarget.setPointerCapture?.(event.pointerId)
  const move = (e) => {
    if (side === 'left') {
      leftWidth.value = Math.round(Math.min(LEFT_MAX, Math.max(LEFT_MIN, Math.min(e.clientX - rect.left, rect.width - rightWidth.value - CENTER_MIN))))
    } else {
      rightWidth.value = Math.round(Math.min(RIGHT_MAX, Math.max(RIGHT_MIN, Math.min(rect.right - e.clientX, rect.width - leftWidth.value - CENTER_MIN))))
    }
  }
  const up = () => { stopResize() }
  stopResize()
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
  stopResizeListener = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up) }
}
function stopResize() {
  stopResizeListener?.()
  stopResizeListener = null
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen()
  else document.documentElement.requestFullscreen?.()
}
function onKeydown(event) {
  if (activeView.value !== 'monitor' || event.key.toLowerCase() !== 'f' || event.metaKey || event.ctrlKey || event.altKey) return
  if (event.target.closest?.('input, textarea, select, [contenteditable], .art-video-player')) return
  toggleFullscreen()
}

// --- Health ---
async function checkHealth() {
  try { await getHealth(); health.value = 'online' } catch { health.value = 'offline' }
  healthTimer = setTimeout(checkHealth, 15000)
}

// --- Toast ---
function showToast(title, desc, type = 'info') {
  toast({ title, desc, type })
}

function resetConfigSaveMessage() {
  clearTimeout(configSaveTimer)
  configSaveTimer = setTimeout(() => { configSaveMessage.value = '' }, 2000)
}

function mapTaskDetections(task) {
  const taskSampleInterval = Number(task.sample_interval_seconds || 0)
  const taskFrameStride = Number(task.frame_stride || 0)
  const taskFps = Number(task.fps || 0)
  return (task.detections || []).map((d, idx) => ({
    id: d.id || `det_${idx}`,
    frame: d.frame,
    timestamp: d.timestamp,
    label: d.label,
    confidence: d.confidence,
    type: (d.label && (d.label.toLowerCase().includes('crown') || d.label.toLowerCase().includes('thorn') || d.label.toLowerCase().includes('net') || d.label.toLowerCase().includes('debris'))) ? 'alert' : 'safe',
    x: d.x,
    y: d.y,
    width: d.width,
    height: d.height,
    start_time: d.start_time,
    end_time: d.end_time,
    sample_interval_seconds: Number(d.sample_interval_seconds || taskSampleInterval || 0),
    frame_stride: Number(d.frame_stride || taskFrameStride || 0),
    fps: Number(d.fps || taskFps || 0)
  }))
}

function buildHistoryItem(task) {
  const detections = mapTaskDetections(task)
  return {
    id: String(task.task_id),
    taskId: task.task_id,
    name: task.original_filename,
    duration: detections.length > 0 ? Math.max(...detections.map(d => d.end_time)) : 0,
    status: task.status === 'completed' ? 'processed' : task.status,
    url: toMediaUrl(task.uploaded_video_path),
    sourceUrl: toMediaUrl(task.uploaded_video_path),
    resultUrl: toMediaUrl(task.result_video_path),
    detections
  }
}

function upsertHistory(task) {
  const nextItem = buildHistoryItem(task)
  history.value = [nextItem, ...history.value.filter(item => String(item.id) !== String(nextItem.id))]
}

function removeHistoryByIds(ids) {
  const idSet = new Set(ids.map(String))
  history.value = history.value.filter(item => !idSet.has(String(item.id)))
}

function applyTaskPlayback(task, logPrefix = '[DONE]') {
  const detections = mapTaskDetections(task)
  const resolvedResultVideoUrl = toMediaUrl(task.result_video_path) || null
  workspaceMode.value = 'video'
  fileName.value = task.original_filename
  videoUrl.value = toMediaUrl(task.uploaded_video_path)
  resultVideoUrl.value = resolvedResultVideoUrl
  playbackMode.value = resolvedResultVideoUrl ? 'result' : 'overlay'
  boxes.value = detections
  currentTaskId.value = task.task_id
  currentTime.value = 0
  progress.value = Number(task.progress || 100)
  status.value = 'playing'
  logs.value = [`${logPrefix} 已加载视频 ${task.task_id}：${task.original_filename}`]
  upsertHistory(task)
}

// --- Upload ---
async function handleFileDrop(file) {
  if (!file.name.toLowerCase().endsWith('.mp4')) {
    showToast('只支持 MP4 视频', `“${file.name}”不是 MP4 文件。转换格式后重新上传。`, 'alert')
    return
  }
  activeView.value = 'console'
  workspaceMode.value = 'video'
  fileName.value = file.name
  const fileSizeMB = (file.size / 1024 / 1024).toFixed(1)
  invalidateWorkspaceRequests()
  const version = workspaceGeneration
  uploadAbort = new AbortController()
  currentTaskId.value = null
  analysisState.value = null
  status.value = 'processing'
  progress.value = 0
  logs.value = [`正在上传 ${file.name}（${fileSizeMB} MB）`, '等待本地后端保存视频…']
  try {
    const uploadRes = await uploadVideo(file, uploadAbort.signal)
    if (version !== workspaceGeneration) return
    const task = uploadRes.data
    currentTaskId.value = task.task_id
    upsertHistory(task)
    logs.value = [...logs.value, `上传完成，视频编号 ${task.task_id}`]
    videoUrl.value = toMediaUrl(task.uploaded_video_path)
    resultVideoUrl.value = null
    playbackMode.value = 'overlay'
    boxes.value = []
    status.value = 'playing'
    showToast('视频已就绪', '在右侧选择注册模型，开始分析。', 'success')
  } catch (error) {
    if (version !== workspaceGeneration || error.code === 'ERR_CANCELED') return
    const errMsg = error.response?.data?.detail || error.message || '上传失败'
    logs.value = [...logs.value, `[ERR] ${errMsg}`]
    showToast('上传失败', `${errMsg}。检查后端连接后重试。`, 'alert')
    status.value = 'idle'
  }
}

// --- Workspace ---
function handleCloseWorkspace() {
  status.value = 'idle'
  fileName.value = ''
  videoUrl.value = null
  resultVideoUrl.value = null
  playbackMode.value = 'overlay'
  analysisState.value = null
  boxes.value = []
  logs.value = []
  progress.value = 0
  currentTime.value = 0
  currentTaskId.value = null
  workspaceMode.value = 'video'
  invalidateWorkspaceRequests()
}

function handleTimelineClick(time) {
  seekTo(time)
  currentTime.value = time
}

function handleFileSelect(item) {
  if (item.type === 'config') {
    activeView.value = 'console'
    handleCloseWorkspace()
    workspaceMode.value = 'config'
    fileName.value = item.name
    return
  }
  if (item.sourceUrl || item.url) handlePlayRecord(item)
}

function setSelectionMode(value) {
  selectionMode.value = Boolean(value)
  if (!selectionMode.value) selectedFileIds.value = []
}

function toggleFileSelection(item) {
  const id = String(item.id)
  selectedFileIds.value = selectedFileIds.value.includes(id) ? selectedFileIds.value.filter(currentId => currentId !== id) : [...selectedFileIds.value, id]
}

function getHistoryItemById(id) {
  return history.value.find(item => String(item.id) === String(id))
}

async function queueNewAnalysis(taskId) {
  const [taskResponse, historyResponse, modelsResponse] = await Promise.all([getTask(taskId), listAnalysisRuns(taskId), listAnalysisModels()])
  const previous = historyResponse.data.items[0]
  const model = modelsResponse.data.items.find(item => item.id === previous?.config_snapshot.models.fish) || modelsResponse.data.items[0]
  if (!model) throw new Error('还没有注册模型。先在后端注册授权权重')
  await createAnalysisRun(taskId, { kind: 'fish', models: { fish: model.id }, settings: previous?.config_snapshot.settings || {} })
  return taskResponse.data
}

async function handleSingleFileAction({ action, item }) {
  const taskId = item.taskId || Number(item.id)
  if (!Number.isFinite(taskId)) {
    showToast('无法操作这个视频', '视频编号无效。刷新页面后重试。', 'alert')
    return
  }
  try {
    if (action === 'delete') {
      const confirmed = await confirmDialog({ title: `删除“${item.name}”？`, description: '本地视频文件和数据库记录会一起删除，无法恢复。被分析引用的视频不能删除。', confirmLabel: '删除视频', danger: true })
      if (!confirmed) return
      await mutateTask(taskId, { action: 'delete' })
      removeHistoryByIds([item.id])
      if (currentTaskId.value === taskId) handleCloseWorkspace()
      showToast('已删除', item.name)
      return
    }
    if (action === 'rename') {
      const nextName = await promptDialog({ title: '重命名视频', label: '文件名', value: item.name, confirmLabel: '重命名' })
      if (!nextName || nextName === item.name) return
      const res = await mutateTask(taskId, { action: 'rename', name: nextName })
      upsertHistory(res.data)
      if (currentTaskId.value === taskId) fileName.value = res.data.original_filename
      showToast('已重命名', res.data.original_filename, 'success')
      return
    }
    if (action === 'copy') {
      const res = await mutateTask(taskId, { action: 'copy' })
      upsertHistory(res.data)
      showToast('已复制', res.data.original_filename, 'success')
      return
    }
    if (action === 'rerun') {
      const version = workspaceGeneration
      const task = await queueNewAnalysis(taskId)
      if (version !== workspaceGeneration) return
      const wasCurrent = currentTaskId.value === taskId
      applyTaskPlayback(task, '[RERUN]')
      if (wasCurrent) analysisPanelRef.value?.refresh()
      showToast('分析已排队', '沿用上次的模型与参数。旧结果保留，可在分析记录中切换。')
    }
  } catch (error) {
    const errMsg = error.response?.data?.detail || error.message || '操作失败'
    showToast('操作失败', errMsg, 'alert')
  }
}

async function handleBatchFileAction({ action }) {
  const selectedItems = selectedFileIds.value.map(id => getHistoryItemById(id)).filter(Boolean)
  if (!selectedItems.length) return
  const taskIds = selectedItems.map(item => item.taskId || Number(item.id)).filter(id => Number.isFinite(id))
  try {
    if (action === 'delete') {
      const confirmed = await confirmDialog({ title: `删除 ${selectedItems.length} 个视频？`, description: '本地视频文件和数据库记录会一起删除，无法恢复。被分析引用的视频不能删除。', confirmLabel: `删除 ${selectedItems.length} 个视频`, danger: true })
      if (!confirmed) return
      await batchMutateTasks({ action: 'delete', task_ids: taskIds })
      removeHistoryByIds(selectedItems.map(item => item.id))
      if (currentTaskId.value && taskIds.includes(currentTaskId.value)) handleCloseWorkspace()
      setSelectionMode(false)
      showToast('已删除', `${selectedItems.length} 个视频`)
      return
    }
    if (action === 'copy') {
      const res = await batchMutateTasks({ action: 'copy', task_ids: taskIds })
      for (const task of res.data.tasks || []) upsertHistory(task)
      setSelectionMode(false)
      showToast('已复制', `${selectedItems.length} 个视频`, 'success')
      return
    }
    if (action === 'rerun') {
      let count = 0
      for (const taskId of taskIds) {
        try { await queueNewAnalysis(taskId); count += 1 }
        catch { showToast('部分分析没有排队', `已排队 ${count} 个，其余视频请单独重试。`, 'alert'); return }
      }
      setSelectionMode(false)
      analysisPanelRef.value?.refresh()
      showToast('分析已排队', `${count} 个视频各自新建一次分析，旧结果保留。`)
    }
  } catch (error) {
    const errMsg = error.response?.data?.detail || error.message || '批量操作失败'
    showToast('批量操作失败', errMsg, 'alert')
  }
}

async function handlePlayRecord(record) {
  activeView.value = activeView.value === 'records' ? 'console' : activeView.value
  workspaceMode.value = 'video'
  invalidateWorkspaceRequests()
  const version = workspaceGeneration
  taskAbort = new AbortController()
  applyTaskPlayback({
    task_id: record.taskId || Number(record.id),
    original_filename: record.name,
    uploaded_video_path: record.sourceUrl || record.url || '',
    result_video_path: record.resultUrl || '',
    detections: record.detections || [],
    progress: 100,
    status: 'completed'
  }, '[HISTORY]')
  const taskId = record.taskId || Number(record.id)
  if (!Number.isFinite(taskId)) return
  try {
    const res = await getTask(taskId, taskAbort.signal)
    if (version !== workspaceGeneration) return
    applyTaskPlayback(res.data, '[HISTORY]')
  } catch (error) {
    if (version !== workspaceGeneration || error.code === 'ERR_CANCELED') return
    logs.value = [...logs.value, `[WARN] 视频详情读取失败，使用缓存回放：${error.message}`]
  }
}

async function handleSaveConfig() {
  try {
    const res = await updateConfig({ content: configContent.value })
    configContent.value = res.data.content
    configSaveMessage.value = '已保存'
    resetConfigSaveMessage()
  } catch (error) {
    const errMsg = error.response?.data?.detail || error.message || '配置保存失败'
    configSaveMessage.value = '保存失败'
    showToast('配置没有保存', `${errMsg}。检查 TOML 语法后重试。`, 'alert')
    resetConfigSaveMessage()
  }
}

async function refreshHistory() {
  const res = await listTasks()
  history.value = (res.data || []).map(buildHistoryItem)
}

async function loadPipelineConfig() {
  const res = await getConfig()
  configContent.value = res.data.content || ''
  configFileEntry.value = { ...configFileEntry.value, path: res.data.path || configFileEntry.value.path }
}

watch(activeView, () => setSelectionMode(false))

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  checkHealth()
  try {
    await Promise.all([refreshHistory(), loadPipelineConfig()])
  } catch (error) {
    showToast('无法读取视频库', '确认本地后端已启动后刷新页面。', 'alert')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  invalidateWorkspaceRequests()
  stopResize()
  clearTimeout(healthTimer)
  clearTimeout(configSaveTimer)
})
</script>

<style scoped>
.app { display: grid; grid-template-rows: 48px 1fr 28px; height: 100dvh; }
.topbar { display: flex; align-items: center; gap: 24px; padding: 0 12px 0 16px; background: var(--canvas); box-shadow: inset 0 -1px 0 var(--line); }
.brand { display: flex; align-items: center; gap: 8px; min-width: 0; }
.mark { width: 20px; height: 20px; color: var(--accent); flex: none; }
.brand-name { font-weight: 600; letter-spacing: -0.01em; }
.brand-sub { color: var(--ink-3); font-size: var(--text-small); white-space: nowrap; }
.nav { display: flex; gap: 2px; height: 100%; }
.nav-item { position: relative; display: inline-flex; align-items: center; gap: 6px; height: 100%; padding: 0 12px; border: 0; background: none; font: inherit; font-weight: 500; color: var(--ink-3); cursor: pointer; transition: color 120ms var(--ease); }
.nav-item:hover { color: var(--ink); }
.nav-item[aria-current=page] { color: var(--ink); }
.nav-item[aria-current=page]::after { content: ""; position: absolute; left: 12px; right: 12px; bottom: 0; height: 2px; border-radius: 1px; background: var(--accent); }
.nav-item[aria-current=page] .tabler-icon { color: var(--accent); }
.top-actions { display: flex; gap: 4px; margin-inline-start: auto; }
.main { position: relative; min-height: 0; overflow: hidden; }
.layout {
  display: grid; height: 100%; padding: 10px; column-gap: 0; row-gap: 10px;
  grid-template-columns: var(--left) 10px minmax(0, 1fr) 10px var(--right);
  grid-template-rows: minmax(0, 1fr);
  grid-template-areas: "library hl center hr inspector";
}
.layout.wall { grid-template-columns: minmax(0, 1fr) 12px minmax(340px, 30%); grid-template-rows: auto minmax(0, 1fr); grid-template-areas: "head head head" "center . side"; padding: 14px 16px; }
.area-library { grid-area: library; min-height: 0; border-radius: var(--radius-lg); overflow: hidden; box-shadow: 0 0 0 1px var(--line); }
.area-inspector { grid-area: inspector; min-height: 0; border-radius: var(--radius-lg); overflow: hidden; box-shadow: 0 0 0 1px var(--line); background: var(--surface); }
.area-head { grid-area: head; min-width: 0; }
.area-center { grid-area: center; display: flex; flex-direction: column; gap: 10px; min-width: 0; min-height: 0; }
.area-side { grid-area: side; min-height: 0; display: flex; flex-direction: column; }
.grow { flex: 1; min-height: 0; }
.handle { position: relative; cursor: col-resize; touch-action: none; }
.handle-left { grid-area: hl; }
.handle-right { grid-area: hr; }
.handle::after { content: ""; position: absolute; top: 50%; left: 50%; width: 3px; height: 28px; translate: -50% -50%; border-radius: 2px; background: var(--line-strong); opacity: 0; transition: opacity 120ms var(--ease); }
.handle:hover::after, .handle:active::after { opacity: 1; }
.timeline-card { flex: none; padding: 10px 12px 8px; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); }
.inspector-empty { display: flex; flex-direction: column; gap: 16px; padding: 16px; }
.inspector-empty h2 { font-size: var(--text-title); font-weight: 600; }
.steps { display: flex; flex-direction: column; gap: 14px; }
.steps li { display: flex; gap: 10px; }
.steps strong { font-weight: 500; }
.num { display: grid; place-items: center; flex: none; width: 20px; height: 20px; border-radius: 50%; font-size: var(--text-caption); font-weight: 600; color: var(--ink-2); background: var(--surface-3); }
.statusbar .mono { font-size: 1em; }
.statusbar { display: flex; align-items: center; gap: 14px; padding: 0 14px; font-size: var(--text-caption); color: var(--ink-3); background: var(--canvas); box-shadow: inset 0 1px 0 var(--line); white-space: nowrap; }
.health { display: inline-flex; align-items: center; gap: 6px; }
.health[data-state=online] .dot { color: var(--ok); }
.health[data-state=offline] { color: var(--danger); }
.health[data-state=checking] .dot { color: var(--ink-3); }
.context { display: inline-flex; align-items: center; gap: 6px; min-width: 0; color: var(--ink-2); }
.truncate { overflow: hidden; text-overflow: ellipsis; }
.sep { width: 3px; height: 3px; border-radius: 50%; background: var(--ink-3); opacity: 0.6; }
.spacer { flex: 1; }
.faint { color: var(--ink-3); }

@media (max-width: 1180px) {
  .brand-sub { display: none; }
  .layout { grid-template-columns: 232px 8px minmax(0, 1fr) 8px 312px; }
}
@media (max-width: 900px) {
  .topbar { gap: 8px; padding: 0 8px; }
  .nav-item { padding: 0 8px; }
  .layout, .layout.wall { display: flex; flex-direction: column; overflow-y: auto; padding: 8px; gap: 8px; }
  .handle { display: none; }
  .area-library { flex: none; height: 220px; }
  .area-center { flex: none; height: 62vh; min-height: 360px; }
  .area-inspector { flex: none; min-height: 560px; }
  .area-side { flex: none; }
  .statusbar .faint { display: none; }
}
</style>
