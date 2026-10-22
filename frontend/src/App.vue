<template>
  <div class="app-shell h-dvh w-screen flex flex-col overflow-hidden text-m3-on-surface bg-m3-bg font-sans text-[13px] transition-colors duration-200">
    <!-- Title Bar -->
    <header class="h-14 border-b border-m3-outline-variant/30 flex items-center justify-between px-6 shrink-0 select-none z-30 bg-m3-bg transition-colors duration-200">
      <div class="flex items-center gap-4 h-full">
        <div class="p-2 rounded-lg bg-m3-primary/10 text-m3-primary">
          <i class="w-5 h-5">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 block">
              <path d="M2 6c.6.5 1.2 1 2.5 1C7.7 7 7.7 5 11 5c2 0 2.5 1 5 1s3-1 5-1"/>
              <path d="M2 12c.6.5 1.2 1 2.5 1 3.2 0 3.2-2 6.5-2 2 0 2.5 1 5 1s3-1 5-1"/>
              <path d="M2 18c.6.5 1.2 1 2.5 1 3.2 0 3.2-2 6.5-2 2 0 2.5 1 5 1s3-1 5-1"/>
            </svg>
          </i>
        </div>
        <div class="flex space-x-6 h-full items-center font-medium">
          <button type="button" :aria-pressed="activeView === 'console'"
            @click="activeView = 'console'"
            class="cursor-pointer transition-colors px-2 py-1 rounded-md"
            :class="activeView === 'console' ? 'text-m3-primary font-semibold' : 'text-m3-on-surface-variant hover:text-m3-on-surface'"
          >控制台</button>
          <button type="button" :aria-pressed="activeView === 'monitor'"
            @click="activeView = 'monitor'"
            class="cursor-pointer transition-colors px-2 py-1 rounded-md"
            :class="activeView === 'monitor' ? 'text-m3-primary font-semibold' : 'text-m3-on-surface-variant hover:text-m3-on-surface'"
          >监控台</button>
          <button type="button" :aria-pressed="activeView === 'records'"
            @click="activeView = 'records'"
            class="cursor-pointer transition-colors px-2 py-1 rounded-md"
            :class="activeView === 'records' ? 'text-m3-primary font-semibold' : 'text-m3-on-surface-variant hover:text-m3-on-surface'"
          >记录</button>
        </div>
      </div>
      <div class="absolute left-1/2 -translate-x-1/2 flex items-center">
        <span class="text-[12px] text-m3-on-surface-variant font-medium">水下生态监测平台</span>
      </div>
      <div class="flex items-center gap-4">
        <!-- Theme Toggle -->
        <button
          @click="toggleTheme"
          :aria-label="isDarkTheme ? '切换为浅色' : '切换为深色'"
          class="w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer text-m3-on-surface-variant hover:text-m3-primary hover:bg-m3-primary/10 transition-colors"
        >
          <i v-if="isDarkTheme" class="w-4 h-4">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
              <circle cx="12" cy="12" r="4"/>
              <path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>
            </svg>
          </i>
          <i v-else class="w-4 h-4">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
              <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
            </svg>
          </i>
        </button>
        <div class="w-8 h-8 rounded-lg bg-m3-primary/20 flex items-center justify-center cursor-pointer text-m3-primary">
          <div class="w-2.5 h-2.5 rounded-full bg-m3-success"></div>
        </div>
      </div>
    </header>

    <!-- Main Body -->
    <main class="flex flex-1 overflow-hidden relative z-10">
      <!-- Console View -->
      <template v-if="activeView === 'console' || activeView === 'monitor'">
        <!-- Activity Bar -->
        <div class="w-16 border-r border-m3-outline-variant/30 bg-m3-bg flex flex-col items-center py-4 gap-4 shrink-0 z-20">
          <div
            @click="togglePanel('files')"
            class="p-3 rounded-lg cursor-pointer transition-colors"
            :class="activePanel === 'files' ? 'text-m3-primary bg-m3-primary/15' : 'text-m3-on-surface-variant hover:text-m3-on-surface hover:bg-m3-surface-container'"
          >
            <i class="w-5 h-5">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 block">
                <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
                <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
              </svg>
            </i>
          </div>
          <div
            @click="togglePanel('activity')"
            class="p-3 rounded-lg cursor-pointer transition-colors"
            :class="activePanel === 'activity' ? 'text-m3-primary bg-m3-primary/15' : 'text-m3-on-surface-variant hover:text-m3-on-surface hover:bg-m3-surface-container'"
          >
            <i class="w-5 h-5">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 block">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
            </i>
          </div>
          <div
            @click="togglePanel('box')"
            class="p-3 rounded-lg cursor-pointer transition-colors"
            :class="activePanel === 'box' ? 'text-m3-primary bg-m3-primary/15' : 'text-m3-on-surface-variant hover:text-m3-on-surface hover:bg-m3-surface-container'"
          >
            <i class="w-5 h-5">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 block">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
            </i>
          </div>
          <div
            @click="togglePanel('terminal')"
            class="p-3 rounded-lg cursor-pointer transition-colors"
            :class="activePanel === 'terminal' ? 'text-m3-primary bg-m3-primary/15' : 'text-m3-on-surface-variant hover:text-m3-on-surface hover:bg-m3-surface-container'"
          >
            <i class="w-5 h-5">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 block">
                <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
              </svg>
            </i>
          </div>
          <div
            @click="togglePanel('settings')"
            class="mt-auto p-3 rounded-lg cursor-pointer transition-colors"
            :class="activePanel === 'settings' ? 'text-m3-primary bg-m3-primary/15' : 'text-m3-on-surface-variant hover:text-m3-on-surface hover:bg-m3-surface-container'"
          >
            <i class="w-5 h-5">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 block">
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
            </i>
          </div>
        </div>

        <!-- Sidebar + Workspace + RightPanel flex layout -->
        <div ref="consoleLayoutRef" :class="{'ocean-wall':activeView === 'monitor' && currentTaskId}" class="console-layout flex-1 flex overflow-hidden">
          <!-- Sidebar -->
          <div
            v-if="activePanel !== null"
            class="file-sidebar flex-shrink-0"
            :style="{ width: `${leftPanelWidth}px`, minWidth: `${LEFT_PANEL_MIN}px` }"
          >
            <Sidebar
              :history="history"
              :active-panel="activePanel"
              :settings="pipelineSettings"
              :config-file="configFileEntry"
              :selection-mode="selectionMode"
              :selected-ids="selectedFileIds"
              @file-select="handleFileSelect"
              @update-settings="updatePipelineSettings"
              @file-action="handleSingleFileAction"
              @file-batch-action="handleBatchFileAction"
              @toggle-select="toggleFileSelection"
              @selection-mode-change="setSelectionMode"
            />
          </div>

          <!-- Separator -->
          <div
            v-if="activePanel !== null"
            class="relative w-1.5 flex items-center justify-center cursor-col-resize group z-30 transition-colors bg-transparent shrink-0"
            @mousedown="startResize('left', $event)"
          >
            <div class="absolute left-1/2 w-px h-full bg-m3-outline-variant/30 group-hover:bg-m3-primary transition-colors"></div>
            <div class="absolute left-1/2 -translate-x-[1px] w-[3px] h-6 bg-m3-outline-variant/70 rounded-full group-hover:bg-m3-primary transition-colors"></div>
          </div>

          <!-- VideoWorkspace -->
          <div class="video-column flex flex-col flex-1 min-w-0 bg-transparent p-4 overflow-hidden">
            <MonitorView v-if="activeView === 'monitor'" :analysis="analysisState" :file-name="fileName" />
            <ConfigEditor
              v-if="workspaceMode === 'config'"
              :file-name="configFileEntry.name"
              :content="configContent"
              :save-message="configSaveMessage"
              @update:content="configContent = $event"
              @save="handleSaveConfig"
              @close="handleCloseWorkspace"
            />
            <VideoWorkspace class="flex-1 min-h-0"
              v-if="workspaceMode !== 'config'"
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
              @settings-click="activePanel = 'settings'"
            />
          </div>

          <!-- Right Panel Separator -->
          <div
            class="relative w-1.5 flex items-center justify-center cursor-col-resize group z-30 transition-colors bg-transparent shrink-0"
            @mousedown="startResize('right', $event)"
          >
            <div class="absolute left-1/2 w-px h-full bg-m3-outline-variant/30 group-hover:bg-m3-primary transition-colors"></div>
            <div class="absolute left-1/2 -translate-x-[1px] w-[3px] h-6 bg-m3-outline-variant/70 rounded-full group-hover:bg-m3-primary transition-colors"></div>
          </div>

          <!-- RightPanel -->
          <div
            class="analysis-column flex-shrink-0"
            :style="{ width: `${rightPanelWidth}px`, minWidth: `${RIGHT_PANEL_MIN}px` }"
          >
            <FishAnalysisPanel v-if="currentTaskId && workspaceMode === 'video'" ref="analysisPanelRef" :task-id="currentTaskId" :current-time="currentTime" :file-name="fileName" @analysis="analysisState = $event" @seek="handleTimelineClick" />
            <RightPanel v-else
              :boxes="boxes"
              :current-time="currentTime"
              @timeline-click="handleTimelineClick"
            />
          </div>
        </div>
      </template>


      <!-- Records View -->
      <RecordsView
        v-if="activeView === 'records'"
        :history="history"
        @play-record="handlePlayRecord"
      />
    </main>

    <!-- Status Bar -->
    <footer class="h-8 border-t border-m3-outline-variant/30 bg-m3-bg px-4 flex items-center justify-between text-[11px] shrink-0 z-20 select-none transition-colors duration-200">
      <div class="flex h-full items-center gap-6 font-medium">
        <div class="flex items-center cursor-pointer text-m3-on-surface hover:text-m3-primary transition-colors">
          <span class="flex items-center gap-2">
            <div class="w-1.5 h-1.5 rounded-full animate-pulse" :class="status === 'processing' ? 'bg-m3-warning' : 'bg-m3-success'"></div>
            {{ status === 'processing' ? '处理中...' : '系统在线' }}
          </span>
        </div>
        <div class="flex items-center cursor-pointer text-m3-on-surface-variant hover:text-m3-on-surface transition-colors">
          本地研究工作台
        </div>
      </div>
      <div class="flex h-full items-center gap-6 text-m3-on-surface-variant font-medium">
        <div class="flex items-center">精度以独立评估为准</div>
        <div class="flex items-center">{{ status === 'playing' ? '视频回放' : '等待视频' }}</div>
      </div>
    </footer>

    <!-- Toast Container -->
    <div class="fixed bottom-20 right-8 flex flex-col gap-4 z-50 pointer-events-none">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast-enter w-[360px] m3-elevation-3 rounded-3xl flex items-start p-5 gap-4 pointer-events-auto"
        :class="toastBg(toast.type)"
      >
        <div class="mt-1">
          <div class="w-3.5 h-3.5 rounded-full" :class="toastIconColor(toast.type)"></div>
        </div>
        <div class="flex-1 flex flex-col">
          <span class="text-[15px] font-bold text-m3-on-surface mb-1 tracking-wide">{{ toast.title }}</span>
          <span v-if="toast.desc" class="text-[14px] text-m3-on-surface-variant leading-relaxed">{{ toast.desc }}</span>
        </div>
        <button
          @click="dismissToast(toast.id)"
          class="text-m3-on-surface-variant hover:text-m3-on-surface transition-colors p-2 rounded-full hover:bg-m3-outline-variant/20 m1-state-layer"
        >&#10005;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, onMounted, defineAsyncComponent } from 'vue'
import { uploadVideo, getTask, listTasks, getConfig, updateConfig, mutateTask, batchMutateTasks, toMediaUrl, listAnalysisModels, listAnalysisRuns, createAnalysisRun } from './api'
import Sidebar from './components/Sidebar.vue'
import VideoWorkspace from './components/VideoWorkspace.vue'
const ConfigEditor = defineAsyncComponent(() => import('./components/ConfigEditor.vue'))
import RightPanel from './components/RightPanel.vue'
import FishAnalysisPanel from './components/FishAnalysisPanel.vue'
import MonitorView from './components/MonitorView.vue'
import RecordsView from './components/RecordsView.vue'

const LEFT_PANEL_MIN = 200
const RIGHT_PANEL_MIN = 200
const WORKSPACE_MIN = 320
const RESIZE_GAP = 12

// --- State ---
const analysisState = ref(null)
const analysisPanelRef = ref(null)
const history = ref([])
const status = ref('idle') // 'idle' | 'processing' | 'playing'
const progress = ref(0)
const logs = ref([])
const videoUrl = ref(null)
const resultVideoUrl = ref(null)
const playbackMode = ref('result')
const boxes = ref([])
const currentTime = ref(0)
const fileName = ref('')
const activePanel = ref('files')
const activeView = ref('console')
const isDarkTheme = ref(true)
const toasts = ref([])
const currentTaskId = ref(null)
const leftPanelWidth = ref(280)
const rightPanelWidth = ref(340)
const consoleLayoutRef = ref(null)
const workspaceMode = ref('video')
const configContent = ref('')
const configSaveMessage = ref('')
const configFileEntry = ref({
  id: 'config:pipeline_settings.toml',
  type: 'config',
  name: 'pipeline_settings.toml',
  path: 'config/pipeline_settings.toml'
})
const pipelineSettings = ref({
  modelPath: import.meta.env.VITE_DEFAULT_MODEL_PATH || '',
  targetLabels: import.meta.env.VITE_DEFAULT_TARGET_LABELS || 'fish',
  confidenceThreshold: Number(import.meta.env.VITE_DEFAULT_CONFIDENCE_THRESHOLD || 0.25),
  iouThreshold: Number(import.meta.env.VITE_DEFAULT_IOU_THRESHOLD || 0.45),
  frameStride: Number(import.meta.env.VITE_DEFAULT_FRAME_STRIDE || 5),
  batchSize: Number(import.meta.env.VITE_DEFAULT_BATCH_SIZE || 8),
  useHalf: String(import.meta.env.VITE_DEFAULT_USE_HALF || 'true').toLowerCase() !== 'false'
})
const selectionMode = ref(false)
const selectedFileIds = ref([])

let workspaceGeneration = 0
let uploadAbort = null
let taskAbort = null
function invalidateWorkspaceRequests() {
  workspaceGeneration += 1
  uploadAbort?.abort()
  taskAbort?.abort()
}
let stopResizeListener = null
let configSaveTimer = null

// --- Theme ---
watch(isDarkTheme, (val) => {
  if (val) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}, { immediate: true })

function toggleTheme() {
  isDarkTheme.value = !isDarkTheme.value
}

// --- Panel ---
function togglePanel(panel) {
  activePanel.value = activePanel.value === panel ? null : panel
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function stopResize() {
  if (stopResizeListener) {
    stopResizeListener()
    stopResizeListener = null
  }
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

function startResize(side, event) {
  if (!consoleLayoutRef.value) return

  const container = consoleLayoutRef.value
  const rect = container.getBoundingClientRect()

  const handleMouseMove = (moveEvent) => {
    const totalWidth = rect.width
    if (!totalWidth) return

    if (side === 'left') {
      const maxLeft = totalWidth - rightPanelWidth.value - WORKSPACE_MIN - RESIZE_GAP
      leftPanelWidth.value = clamp(
        moveEvent.clientX - rect.left,
        LEFT_PANEL_MIN,
        Math.max(LEFT_PANEL_MIN, maxLeft)
      )
      return
    }

    const maxRight = totalWidth - leftPanelWidth.value - WORKSPACE_MIN - RESIZE_GAP
    rightPanelWidth.value = clamp(
      rect.right - moveEvent.clientX,
      RIGHT_PANEL_MIN,
      Math.max(RIGHT_PANEL_MIN, maxRight)
    )
  }

  const handleMouseUp = () => {
    stopResize()
    window.removeEventListener('mousemove', handleMouseMove)
    window.removeEventListener('mouseup', handleMouseUp)
  }

  stopResize()
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'col-resize'
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('mouseup', handleMouseUp)
  stopResizeListener = () => {
    window.removeEventListener('mousemove', handleMouseMove)
    window.removeEventListener('mouseup', handleMouseUp)
  }
}

// --- Toast ---
function showToast(title, desc, type = 'info') {
  const id = Date.now().toString()
  toasts.value = [...toasts.value, { id, title, desc, type }]
  setTimeout(() => {
    dismissToast(id)
  }, 4000)
}

function dismissToast(id) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

function toastBg(type) {
  return 'bg-m3-surface-container-highest'
}

function toastIconColor(type) {
  if (type === 'warn') return 'bg-m3-warning'
  if (type === 'alert') return 'bg-m3-error'
  if (type === 'success') return 'bg-m3-success'
  return 'bg-m3-primary'
}

function updatePipelineSettings(patch) {
  pipelineSettings.value = {
    ...pipelineSettings.value,
    ...patch
  }
  syncConfigTextFromSettings()
  persistPipelineSettings()
}

function syncConfigTextFromSettings() {
  const targetLabels = String(pipelineSettings.value.targetLabels || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)

  configContent.value = [
    '[pipeline]',
    `model_path = "${String(pipelineSettings.value.modelPath || '').replaceAll('\\', '\\\\').replaceAll('"', '\\"')}"`,
    `target_labels = [${(targetLabels.length > 0 ? targetLabels : ['fish']).map(item => `"${item.replaceAll('\\', '\\\\').replaceAll('"', '\\"')}"`).join(', ')}]`,
    `confidence_threshold = ${Number(pipelineSettings.value.confidenceThreshold || 0.25).toFixed(2)}`,
    `iou_threshold = ${Number(pipelineSettings.value.iouThreshold || 0.45).toFixed(2)}`,
    `frame_stride = ${Number(pipelineSettings.value.frameStride || 5)}`,
    `batch_size = ${Number(pipelineSettings.value.batchSize || 8)}`,
    `use_half = ${Boolean(pipelineSettings.value.useHalf) ? 'true' : 'false'}`
  ].join('\n')
}

async function persistPipelineSettings() {
  try {
    const res = await updateConfig({ settings: pipelineSettings.value })
    pipelineSettings.value = { ...pipelineSettings.value, ...res.data.settings }
    configContent.value = res.data.content
    configFileEntry.value = {
      ...configFileEntry.value,
      path: res.data.path || configFileEntry.value.path
    }
    configSaveMessage.value = '已保存'
    resetConfigSaveMessage()
  } catch (error) {
    configSaveMessage.value = '保存失败'
    resetConfigSaveMessage()
  }
}

function resetConfigSaveMessage() {
  if (configSaveTimer) {
    clearTimeout(configSaveTimer)
  }
  configSaveTimer = setTimeout(() => {
    configSaveMessage.value = ''
  }, 2000)
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
  history.value = [
    nextItem,
    ...history.value.filter(item => String(item.id) !== String(nextItem.id))
  ]
}

function replaceHistory(tasks) {
  history.value = tasks.map(buildHistoryItem)
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
  logs.value = [
    ...logs.value,
    `${logPrefix} 已加载任务 ${task.task_id}: ${task.original_filename}`,
    `${logPrefix} 播放原视频，前端叠加 ${detections.length} 条检测框`,
    resolvedResultVideoUrl
      ? `${logPrefix} 可切换到 YOLO 输出视频，直接查看后端内嵌框`
      : `${logPrefix} 当前任务未提供 YOLO 输出视频，保持前端叠框回放`
  ]
  upsertHistory(task)
}

// --- API: File Drop (Real) ---
async function handleFileDrop(file) {
  workspaceMode.value = 'video'
  if (!file.name.toLowerCase().endsWith('.mp4')) {
    showToast('文件格式不支持', '当前只支持上传 MP4 视频', 'alert')
    return
  }

  fileName.value = file.name
  const fileSizeMB = (file.size / 1024 / 1024).toFixed(2)
  invalidateWorkspaceRequests()
  const version = workspaceGeneration
  uploadAbort = new AbortController()
  currentTaskId.value = null
  analysisState.value = null
  status.value = 'processing'
  progress.value = 0
  logs.value = [`正在上传 ${file.name}（${fileSizeMB} MB）`]

  try {
    // Step 1: Upload
    logs.value = [...logs.value, '等待本地后端保存视频…']
    const uploadRes = await uploadVideo(file, uploadAbort.signal)
    if (version !== workspaceGeneration) return
    const task = uploadRes.data
    currentTaskId.value = task.task_id
    upsertHistory(task)
    progress.value = 0
    logs.value = [...logs.value, `[NET] 上传完成，任务 ID: ${task.task_id}`]

    videoUrl.value = toMediaUrl(task.uploaded_video_path)
    resultVideoUrl.value = null
    playbackMode.value = 'overlay'
    boxes.value = []
    status.value = 'playing'
    showToast('视频已就绪', '在右侧选择注册模型并创建分析 Run', 'info')
  } catch (error) {
    if (version !== workspaceGeneration || error.code === 'ERR_CANCELED') return
    const errMsg = error.response?.data?.detail || error.message || '上传失败'
    logs.value = [...logs.value, `[ERR] ${errMsg}`]
    showToast('处理失败', errMsg, 'alert')
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
  const videoObj = document.querySelector('video')
  if (videoObj) {
    videoObj.currentTime = time
  }
}

function handleFileSelect(item) {
  if (item.type === 'config') {
    activeView.value = 'console'
    workspaceMode.value = 'config'
    status.value = 'idle'
    fileName.value = item.name
    videoUrl.value = null
    resultVideoUrl.value = null
    playbackMode.value = 'overlay'
    boxes.value = []
    logs.value = []
    progress.value = 0
    currentTime.value = 0
    currentTaskId.value = null
    invalidateWorkspaceRequests()
    return
  }

  if (item.sourceUrl || item.url) {
    handlePlayRecord(item)
  }
}

function setSelectionMode(value) {
  selectionMode.value = Boolean(value)
  if (!selectionMode.value) {
    selectedFileIds.value = []
  }
}

function toggleFileSelection(item) {
  const id = String(item.id)
  if (selectedFileIds.value.includes(id)) {
    selectedFileIds.value = selectedFileIds.value.filter(currentId => currentId !== id)
  } else {
    selectedFileIds.value = [...selectedFileIds.value, id]
  }
}

function getHistoryItemById(id) {
  return history.value.find(item => String(item.id) === String(id))
}

function syncTaskInHistory(task) {
  upsertHistory(task)
}

async function queueNewAnalysis(taskId) {
  const [taskResponse, historyResponse, modelsResponse] = await Promise.all([getTask(taskId), listAnalysisRuns(taskId), listAnalysisModels()])
  const previous = historyResponse.data.items[0]
  const model = modelsResponse.data.items.find(item => item.id === previous?.config_snapshot.models.fish) || modelsResponse.data.items[0]
  if (!model) throw new Error('尚无注册模型，请先注册授权权重')
  await createAnalysisRun(taskId, { kind: 'fish', models: { fish: model.id }, settings: previous?.config_snapshot.settings || {} })
  return taskResponse.data
}

async function handleSingleFileAction({ action, item }) {
  const taskId = item.taskId || Number(item.id)
  if (!Number.isFinite(taskId)) {
    showToast('操作失败', '无效的任务编号', 'alert')
    return
  }

  try {
    if (action === 'delete') {
      const confirmed = window.confirm(`确认删除 ${item.name} 吗？这会同时删除本地文件和数据库记录。`)
      if (!confirmed) return
      await mutateTask(taskId, { action: 'delete' })
      removeHistoryByIds([item.id])
      if (currentTaskId.value === taskId) {
        handleCloseWorkspace()
      }
      showToast('已删除', item.name, 'info')
      return
    }

    if (action === 'rename') {
      const nextName = window.prompt('输入新的文件名', item.name)
      if (!nextName || nextName.trim() === item.name) return
      const res = await mutateTask(taskId, { action: 'rename', name: nextName.trim() })
      syncTaskInHistory(res.data)
      if (currentTaskId.value === taskId) {
        fileName.value = res.data.original_filename
      }
      showToast('已重命名', res.data.original_filename, 'success')
      return
    }

    if (action === 'copy') {
      const res = await mutateTask(taskId, { action: 'copy' })
      syncTaskInHistory(res.data)
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
      showToast('新分析已入队', '旧 Run 和产物保留，可在分析历史切换', 'info')
    }
  } catch (error) {
    const errMsg = error.response?.data?.detail || error.message || '操作失败'
    logs.value = [...logs.value, `[ERR] ${errMsg}`]
    showToast('操作失败', errMsg, 'alert')
  }
}

async function handleBatchFileAction({ action }) {
  if (action === 'clear-selection') {
    selectedFileIds.value = []
    return
  }

  const selectedItems = selectedFileIds.value
    .map(id => getHistoryItemById(id))
    .filter(Boolean)

  if (selectedItems.length === 0) {
    showToast('未选择文件', '请先选择要操作的文件', 'info')
    return
  }

  const taskIds = selectedItems
    .map(item => item.taskId || Number(item.id))
    .filter(id => Number.isFinite(id))

  try {
    if (action === 'delete') {
      const confirmed = window.confirm(`确认批量删除 ${selectedItems.length} 个文件吗？这会同时删除本地文件和数据库记录。`)
      if (!confirmed) return
      await batchMutateTasks({ action: 'delete', task_ids: taskIds })
      removeHistoryByIds(selectedItems.map(item => item.id))
      if (currentTaskId.value && taskIds.includes(currentTaskId.value)) {
        handleCloseWorkspace()
      }
      setSelectionMode(false)
      showToast('批量删除完成', `共删除 ${selectedItems.length} 个文件`, 'info')
      return
    }

    if (action === 'rename') {
      if (selectedItems.length !== 1) {
        showToast('批量重命名受限', '重命名一次只能选择 1 个文件', 'alert')
        return
      }
      await handleSingleFileAction({ action: 'rename', item: selectedItems[0] })
      return
    }

    if (action === 'copy') {
      const res = await batchMutateTasks({ action: 'copy', task_ids: taskIds })
      for (const task of res.data.tasks || []) {
        syncTaskInHistory(task)
      }
      setSelectionMode(false)
      showToast('批量拷贝完成', `共生成 ${selectedItems.length} 个副本`, 'success')
      return
    }

    if (action === 'rerun') {
      let count = 0
      for (const taskId of taskIds) {
        try { await queueNewAnalysis(taskId); count += 1 }
        catch { showToast('部分分析未入队', `已入队 ${count} 个 Run，其余文件请重试`, 'alert'); return }
      }
      setSelectionMode(false)
      analysisPanelRef.value?.refresh()
      showToast('批量分析已入队', `共创建 ${count} 个独立 Run，旧结果保留`, 'info')
    }
  } catch (error) {
    const errMsg = error.response?.data?.detail || error.message || '批量操作失败'
    logs.value = [...logs.value, `[ERR] ${errMsg}`]
    showToast('批量操作失败', errMsg, 'alert')
  }
}

async function handlePlayRecord(record) {
  activeView.value = 'console'
  workspaceMode.value = 'video'
  invalidateWorkspaceRequests()
  const version = workspaceGeneration
  taskAbort = new AbortController()

  const fallbackTask = {
    task_id: record.taskId || Number(record.id),
    original_filename: record.name,
    uploaded_video_path: record.sourceUrl || record.url || '',
    result_video_path: record.resultUrl || '',
    detections: record.detections || [],
    progress: 100,
    status: 'completed'
  }

  applyTaskPlayback(fallbackTask, '[HISTORY]')

  const taskId = record.taskId || Number(record.id)
  if (!Number.isFinite(taskId)) return

  try {
    const res = await getTask(taskId, taskAbort.signal)
    if (version !== workspaceGeneration) return
    applyTaskPlayback(res.data, '[HISTORY]')
  } catch (error) {
    if (version !== workspaceGeneration || error.code === 'ERR_CANCELED') return
    logs.value = [...logs.value, `[WARN] 历史任务详情加载失败，已使用缓存数据回放: ${error.message}`]
  }
}

async function handleSaveConfig() {
  try {
    const res = await updateConfig({ content: configContent.value })
    pipelineSettings.value = { ...pipelineSettings.value, ...res.data.settings }
    configContent.value = res.data.content
    configSaveMessage.value = '已保存'
    resetConfigSaveMessage()
  } catch (error) {
    const errMsg = error.response?.data?.detail || error.message || '配置保存失败'
    configSaveMessage.value = '保存失败'
    logs.value = [...logs.value, `[ERR] ${errMsg}`]
    showToast('配置保存失败', errMsg, 'alert')
    resetConfigSaveMessage()
  }
}

async function refreshHistory() {
  const res = await listTasks()
  replaceHistory(res.data || [])
}

async function loadPipelineConfig() {
  const res = await getConfig()
  pipelineSettings.value = { ...pipelineSettings.value, ...(res.data.settings || {}) }
  configContent.value = res.data.content || ''
  configFileEntry.value = {
    ...configFileEntry.value,
    path: res.data.path || configFileEntry.value.path
  }
}

onMounted(async () => {
  try {
    await Promise.all([refreshHistory(), loadPipelineConfig()])
  } catch (error) {
    const errMsg = error.response?.data?.detail || error.message || '初始化失败'
    logs.value = [...logs.value, `[WARN] ${errMsg}`]
  }
})

onBeforeUnmount(() => {
  invalidateWorkspaceRequests()
  stopResize()
  if (configSaveTimer) {
    clearTimeout(configSaveTimer)
  }
})
</script>

<style scoped>
.ocean-wall .file-sidebar{display:none}
.ocean-wall>.cursor-col-resize{display:none}
@media(max-width:1100px){.file-sidebar{width:210px!important;min-width:0!important}.analysis-column{width:310px!important;min-width:0!important}}
@media(max-width:800px){.console-layout{flex-direction:column;overflow:auto!important}.file-sidebar{width:100%!important;max-height:160px;flex-shrink:0}.video-column{min-height:420px;flex:none}.analysis-column{width:100%!important;min-height:500px;flex:1}.console-layout>.cursor-col-resize{display:none}header{padding-left:10px;padding-right:10px}header>.absolute{display:none}footer{font-size:10px;gap:8px}footer>div{gap:10px}}
</style>
