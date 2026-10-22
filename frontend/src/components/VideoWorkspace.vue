<template>
  <div class="flex flex-col h-full bg-m3-surface/30 border border-m3-outline-variant/30 rounded-lg overflow-hidden relative">
    <!-- Editor Tab Bar -->
    <div class="flex items-center bg-transparent h-10 shrink-0 relative border-b border-m3-outline-variant/30 px-3 overflow-hidden">
      <div class="flex items-center px-4 h-full border-b-2 border-m3-primary text-m3-primary cursor-pointer relative z-10 box-border group">
        <span class="text-[11px] font-medium mr-2 text-m3-on-surface-variant bg-m3-surface-container py-0.5 px-1.5 rounded border border-m3-outline-variant/30 uppercase tracking-wider">源</span>
        <span class="font-medium text-[12px] text-m3-on-surface mr-3">{{ fileName || '未命名.mp4' }}</span>
        <button
          v-if="status !== 'idle'"
          @click="$emit('close')"
          aria-label="关闭视频"
          class="p-0.5 rounded opacity-0 group-hover:opacity-100 focus-visible:opacity-100 hover:bg-m3-primary/20 text-m3-primary transition-all"
        >
          <i class="w-3.5 h-3.5">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5 block">
              <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
            </svg>
          </i>
        </button>
      </div>
      <div class="absolute right-2 top-0 bottom-0 flex items-center gap-2 z-20">
        <div
          v-if="status === 'playing'"
          class="flex items-center rounded-md border border-m3-outline-variant/40 bg-m3-surface/80 p-0.5 backdrop-blur-sm"
        >
          <button
            type="button"
            class="px-2.5 py-1 text-[11px] font-medium rounded transition-colors"
            :class="props.playbackMode === 'overlay'
              ? 'bg-m3-primary text-m3-on-primary'
              : 'text-m3-on-surface-variant hover:bg-m3-surface-container hover:text-m3-on-surface'"
            @click="setPlaybackMode('overlay')"
          >
            CANVAS
          </button>
          <button
            type="button"
            class="px-2.5 py-1 text-[11px] rounded transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            :class="props.playbackMode === 'result'
              ? 'bg-m3-primary text-m3-on-primary'
              : 'text-m3-on-surface-variant hover:bg-m3-surface-container hover:text-m3-on-surface'"
            :disabled="!props.resultVideoUrl"
            @click="setPlaybackMode('result')"
          >
            YOLO 输出视频
          </button>
        </div>
        <button
          @click="$emit('settings-click')"
          class="p-1.5 hover:bg-m3-surface-container rounded-md text-m3-on-surface-variant hover:text-m3-on-surface transition-colors"
          title="管线设置"
        >
          <i class="w-4 h-4">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </i>
        </button>
      </div>
    </div>

    <!-- Editor Body -->
    <div class="flex-1 relative overflow-hidden flex flex-col bg-transparent">

      <!-- Idle State -->
      <div v-if="status === 'idle'" class="absolute inset-0 flex items-center justify-center p-8">
        <div
          class="w-full max-w-2xl h-64 rounded-xl border border-dashed flex flex-col items-center justify-center transition-all duration-300 relative overflow-hidden"
          :class="isDragging ? 'border-m3-primary bg-m3-primary/10 text-m3-on-primary-container' : 'border-m3-outline-variant/50 hover:border-m3-outline-variant bg-m3-surface/50 hover:bg-m3-surface'"
          @dragenter.prevent="onDragEnter"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop"
        >
          <!-- Organic blob background -->
          <div class="absolute w-64 h-64 bg-m3-primary/10 blur-2xl transition-all duration-500" :class="isDragging ? 'opacity-100 scale-110' : 'opacity-0 scale-50'"></div>

          <div class="relative z-10 flex flex-col items-center">
            <div class="w-12 h-12 mb-4 flex items-center justify-center rounded-full transition-all" :class="isDragging ? 'bg-m3-primary text-m3-on-primary' : 'bg-m3-surface-container text-m3-on-surface-variant'">
              <i class="w-5 h-5">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5 block">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </i>
            </div>
            <h2 class="text-[14px] font-medium mb-1 text-m3-on-surface">等待视频数据</h2>
            <p class="text-[11px] font-medium text-m3-on-surface-variant mb-6 tracking-widest">拖拽 MP4 以初始化</p>
            <div class="flex gap-3">
              <button
                @click="openFilePicker"
                class="px-5 py-2 text-[12px] rounded-md cursor-pointer text-m3-on-surface hover:bg-m3-surface-container transition-all bg-m3-surface-container font-medium border border-m3-outline-variant/30"
              >浏览文件</button>
            </div>
          </div>
        </div>
        <!-- Hidden file input -->
        <input
          ref="fileInputRef"
          type="file"
          accept="video/mp4"
          class="hidden"
          @change="onFilePicked"
        />
      </div>

      <!-- Processing State -->
      <div v-if="status === 'processing'" class="absolute inset-0 flex flex-col pt-20 items-center bg-m3-bg/50 backdrop-blur-sm z-20">
        <div class="relative w-24 h-24 mb-6 flex justify-center items-center">
          <div class="absolute inset-0 bg-m3-primary/30 blur-xl shadow-[0_0_80px_currentColor] animate-pulse rounded-full text-m3-primary/30" style="animation-duration: 3s"></div>
          <div class="absolute inset-4 bg-m3-primary/20 blur-lg rounded-full animate-pulse" style="animation-duration: 2s; animation-direction: reverse"></div>
          <span class="relative z-10 text-m3-primary font-bold text-3xl font-mono drop-shadow-[0_0_8px_currentColor]">{{ progress }}%</span>
        </div>

        <div class="w-full max-w-lg flex flex-col bg-m3-surface rounded-lg overflow-hidden border border-m3-outline-variant/30">
          <div class="bg-m3-surface-container px-6 py-4 text-[11px] font-medium tracking-widest text-m3-on-surface flex justify-between items-center border-b border-m3-outline-variant/30">
            <span class="flex items-center gap-2.5">
              <div class="w-2 h-2 bg-m3-warning rounded-full animate-pulse"></div>
              正在上传视频
            </span>
          </div>

          <div class="p-6 bg-transparent flex flex-col">
            <div class="h-2 w-full bg-m3-surface-container-highest rounded-full mb-4 overflow-hidden">
              <div class="h-full bg-m3-primary transition-all duration-300" :style="{ width: `${progress}%`, borderRadius: 'inherit' }"></div>
            </div>

            <div ref="logsContainerRef" class="h-32 overflow-y-auto font-mono text-[11px] text-m3-on-surface-variant whitespace-pre-wrap">
              <div
                v-for="(log, idx) in logs"
                :key="idx"
                class="mb-1 leading-snug"
                :class="{ 'text-m3-warning': log.includes('WARN'), 'text-m3-error': log.includes('ERR') }"
              >
                <span class="text-m3-outline select-none mr-2">[{{ getTimestamp() }}]</span>
                {{ log }}
              </div>
              <div v-if="progress < 100" class="animate-pulse mt-1 opacity-50">_</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Playing State -->
      <div v-if="status === 'playing'" class="absolute inset-0 flex flex-col bg-transparent">
        <div ref="containerRef" class="relative flex-1 rounded-lg overflow-hidden flex items-center justify-center select-none m-3 mt-4 mb-2 bg-[#000000]">
          <div ref="playerHostRef" class="absolute inset-0"></div>
          <canvas
            ref="canvasRef"
            :style="{pointerEvents: analysis?.layers.roiEditing ? 'auto' : 'none', cursor: analysis?.layers.roiEditing ? 'crosshair' : 'default'}"
            @click="pickRoiPoint"
            class="absolute inset-0 w-full h-full object-contain pointer-events-none z-20"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import Artplayer from 'artplayer'
import { computed, ref, watch, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  analysis: { type:Object, default:null },
  status: { type: String, default: 'idle' },
  progress: { type: Number, default: 0 },
  logs: { type: Array, default: () => [] },
  videoUrl: { type: String, default: null },
  resultVideoUrl: { type: String, default: null },
  playbackMode: {
    type: String,
    default: 'overlay',
    validator: value => ['overlay', 'result'].includes(value)
  },
  boxes: { type: Array, default: () => [] },
  currentTime: { type: Number, default: 0 },
  fileName: { type: String, default: '' }
})

const emit = defineEmits(['roi-point', 'file-drop', 'close', 'time-update', 'settings-click', 'update:playback-mode'])

const isDragging = ref(false)
const isPlaying = ref(false)
const videoDuration = ref(0)
const displayTime = ref(0)
const playerHostRef = ref(null)
const canvasRef = ref(null)
const containerRef = ref(null)
const logsContainerRef = ref(null)
const fileInputRef = ref(null)

let art = null
let dragCounter = 0
let animationFrameId = null
let resizeObserver = null
let lastRenderedTime = -1
let lastEmittedTime = -1
let lastCanvasWidth = 0
let lastCanvasHeight = 0
let lastVideoWidth = 0
let lastVideoHeight = 0
let lastDrawMetrics = null
let preparedSegments = []
let activeSegments = []
let nextSegmentStartIndex = 0
let preparedFrameBuckets = []
let estimatedSampleSpacing = 1 / 30
let canvasContext = null
let pendingResumePlayback = false
let lastCanvasDpr = 0

const isOverlayMode = computed(() => props.playbackMode === 'overlay')
const activeVideoUrl = computed(() => (
  props.playbackMode === 'result' && props.resultVideoUrl
    ? props.resultVideoUrl
    : props.videoUrl
))

function getVideoElement() {
  return art?.video || null
}

function setPlaybackMode(mode) {
  if (mode === 'result' && !props.resultVideoUrl) return
  if (props.playbackMode === mode) return
  emit('update:playback-mode', mode)
}

function ensureArtPlayer() {
  if (art || !playerHostRef.value) return

  art = new Artplayer({
    container: playerHostRef.value,
    url: activeVideoUrl.value || '',
    theme: '#85d2f6',
    autoplay: true,
    autoSize: false,
    autoMini: false,
    loop: true,
    fullscreen: true,
    fullscreenWeb: true,
    setting: false,
    playbackRate: true,
    pip: true,
    mutex: true,
    backdrop: true,
    playsInline: true,
    airplay: true,
    screenshot: false,
    autoPlayback: false,
    moreVideoAttr: {
      preload: 'auto',
      crossOrigin: 'anonymous',
    },
    customType: {},
  })

  art.on('ready', handleArtReady)
  art.on('play', handleVideoPlay)
  art.on('pause', handleVideoPause)
  art.on('video:timeupdate', handleArtTimeUpdate)
  art.on('video:loadedmetadata', handleArtMetadataReady)
  art.on('video:canplay', handleArtCanPlay)
  art.on('video:seeking', onVideoSeeking)
  art.on('resize', handleArtResize)
  art.on('fullscreen', handleArtResize)
  art.on('fullscreenWeb', handleArtResize)
  ensureCanvasMount()
}

function destroyArtPlayer() {
  if (!art) return
  art.destroy(false)
  art = null
}

function resetVideoElement(shouldResumePlayback = false) {
  const video = getVideoElement()
  if (!video || !art) return

  stopRenderLoop()
  isPlaying.value = false
  video.pause()
  video.currentTime = 0
  videoDuration.value = 0
  displayTime.value = 0
  pendingResumePlayback = shouldResumePlayback
  art.url = activeVideoUrl.value || ''
}

// Drag and Drop
function onDragEnter(e) {
  dragCounter++
  isDragging.value = true
}

function onDragOver(e) {
  // preventDefault handled by @dragover.prevent
}

function onDragLeave() {
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragging.value = false
  }
}

function onDrop(e) {
  dragCounter = 0
  isDragging.value = false
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    emit('file-drop', e.dataTransfer.files[0])
  }
}

// File Picker
function openFilePicker() {
  if (fileInputRef.value) {
    fileInputRef.value.click()
  }
}

function onFilePicked(e) {
  const file = e.target.files?.[0]
  if (file) {
    emit('file-drop', file)
    // Reset file input so the same file can be picked again
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
  }
}

// Playback
function togglePlay() {
  const video = getVideoElement()
  if (!video) return
  if (isPlaying.value) {
    video.pause()
  } else {
    video.play()
  }
}

function handleArtTimeUpdate() {
  const video = getVideoElement()
  if (!video) return
  const time = video.currentTime || 0
  videoDuration.value = video.duration || 0
  isPlaying.value = !video.paused && !video.ended
  syncDisplayedTime(time, false)
  if (isOverlayMode.value) {
    renderCanvas(false, time)
  }
}

function handleArtReady() {
  const video = getVideoElement()
  if (!video) return

  ensureCanvasMount()
  videoDuration.value = video.duration || 0
  isPlaying.value = !video.paused && !video.ended
}

function handleArtMetadataReady() {
  const video = getVideoElement()
  if (!video) return

  videoDuration.value = video.duration || 0
  isPlaying.value = !video.paused && !video.ended
  requestAnimationFrame(() => {
    renderCanvas(true, video.currentTime)
    if (props.status === 'playing') {
      startRenderLoop()
    }
  })
}

function handleArtCanPlay() {
  const video = getVideoElement()
  if (!video) return

  videoDuration.value = video.duration || 0
  isPlaying.value = !video.paused && !video.ended
  requestAnimationFrame(() => {
    renderCanvas(true, video.currentTime)
    if (props.status === 'playing') {
      startRenderLoop()
    }
  })

  if (pendingResumePlayback) {
    pendingResumePlayback = false
    video.play().catch(() => {})
  }
}

function handleVideoPlay() {
  isPlaying.value = true
  startRenderLoop()
}

function handleVideoPause() {
  isPlaying.value = false
  renderCanvas(true, getVideoElement()?.currentTime ?? 0)
}

function onVideoSeeking() {
  const video = getVideoElement()
  if (video) {
    nextSegmentStartIndex = 0
    activeSegments = []
    getActiveBoxes(video.currentTime)
  }
  renderCanvas(true, video?.currentTime ?? 0)
}

function handleArtResize() {
  requestAnimationFrame(() => {
    ensureCanvasMount()
    isPlaying.value = !getVideoElement()?.paused && !getVideoElement()?.ended
    renderCanvas(true, getVideoElement()?.currentTime ?? 0)
  })
}

watch(() => props.currentTime, (t) => {
  displayTime.value = t
  const video=getVideoElement()
  if(video && Math.abs(video.currentTime-t)>0.15)video.currentTime=t
})

function prepareBoxes(boxes) {
  const detections = [...boxes]
    .map((box, index) => ({
      ...box,
      _index: index,
      _time: Number.isFinite(Number(box.timestamp)) ? Number(box.timestamp) : (Number(box.start_time) || 0),
      _start: Number(box.start_time) || 0,
      _end: Number(box.end_time) || 0,
      _sampleInterval: Number(box.sample_interval_seconds || 0),
      _sampleDuration: Math.max(
        Number(box.sample_interval_seconds || 0) ||
        ((Number(box.end_time) || 0) - (Number(box.start_time) || 0)),
        0
      ),
      _labelText: ` ${box.label} ${(Number(box.confidence || 0) * 100).toFixed(0)}% `,
      _centerX: (Number(box.x) || 0) + (Number(box.width) || 0) / 2,
      _centerY: (Number(box.y) || 0) + (Number(box.height) || 0) / 2,
    }))
    .sort((a, b) => a._time - b._time)

  preparedFrameBuckets = buildFrameBuckets(detections)
  estimatedSampleSpacing = resolveSampleSpacing(preparedFrameBuckets, detections)
  const tracks = buildTracks(detections, estimatedSampleSpacing)
  preparedSegments = buildSegments(tracks, estimatedSampleSpacing)
  activeSegments = []
  nextSegmentStartIndex = 0
  lastRenderedTime = -1
}

function buildFrameBuckets(detections) {
  const frameBucketMap = new Map()

  detections.forEach((detection) => {
    const key = detection._time.toFixed(4)
    if (!frameBucketMap.has(key)) {
      frameBucketMap.set(key, [])
    }
    frameBucketMap.get(key).push(detection)
  })

  return [...frameBucketMap.entries()]
    .map(([key, bucketDetections]) => ({
      time: Number(key),
      detections: bucketDetections
    }))
    .sort((a, b) => a.time - b.time)
}

function resolveSampleSpacing(frameBuckets, detections) {
  const explicitSampleIntervals = detections
    .map((detection) => detection._sampleInterval)
    .filter((interval) => interval > 0.0001)
    .sort((a, b) => a - b)

  if (explicitSampleIntervals.length > 0) {
    return explicitSampleIntervals[Math.floor(explicitSampleIntervals.length / 2)]
  }

  if (frameBuckets.length > 1) {
    const gaps = []
    for (let index = 1; index < frameBuckets.length; index += 1) {
      const gap = frameBuckets[index].time - frameBuckets[index - 1].time
      if (gap > 0.0001) {
        gaps.push(gap)
      }
    }
    if (gaps.length > 0) {
      gaps.sort((a, b) => a - b)
      return gaps[Math.floor(gaps.length / 2)]
    }
  }

  const sampleDurations = detections
    .map((detection) => detection._sampleDuration)
    .filter((duration) => duration > 0.0001)
    .sort((a, b) => a - b)

  if (sampleDurations.length > 0) {
    return sampleDurations[Math.floor(sampleDurations.length / 2)]
  }

  return 1 / 30
}

function buildTracks(detections, sampleSpacing) {
  const frameBuckets = new Map()
  let nextTrackId = 0

  detections.forEach((detection) => {
    const key = detection._time.toFixed(4)
    if (!frameBuckets.has(key)) {
      frameBuckets.set(key, [])
    }
    frameBuckets.get(key).push(detection)
  })

  const bucketTimes = [...frameBuckets.keys()]
    .map(Number)
    .sort((a, b) => a - b)

  const tracks = []

  bucketTimes.forEach((time) => {
    const bucketKey = time.toFixed(4)
    const frameDetections = frameBuckets.get(bucketKey) || []
    const candidates = []

    frameDetections.forEach((detection, detectionIndex) => {
      tracks.forEach((track, trackIndex) => {
        const previous = track.keyframes[track.keyframes.length - 1]
        if (!previous || previous.label !== detection.label) return

        const gap = detection._time - previous._time
        const allowedGap = Math.max(previous._sampleDuration || sampleSpacing, sampleSpacing) * 4 + 0.08
        if (gap <= 0 || gap > allowedGap) return

        const iouValue = computeIoU(previous, detection)
        const centerDistance = computeCenterDistance(previous, detection)

        if (iouValue < 0.01 && centerDistance > 0.28) return

        const score =
          iouValue * 2 +
          (1 - Math.min(centerDistance / 0.28, 1)) +
          (1 - Math.min(gap / allowedGap, 1)) * 0.15
        candidates.push({
          trackIndex,
          detectionIndex,
          score
        })
      })
    })

    candidates.sort((a, b) => b.score - a.score)

    const matchedTracks = new Set()
    const matchedDetections = new Set()

    candidates.forEach((candidate) => {
      if (matchedTracks.has(candidate.trackIndex) || matchedDetections.has(candidate.detectionIndex)) {
        return
      }

      tracks[candidate.trackIndex].keyframes.push(frameDetections[candidate.detectionIndex])
      matchedTracks.add(candidate.trackIndex)
      matchedDetections.add(candidate.detectionIndex)
    })

    frameDetections.forEach((detection, detectionIndex) => {
      if (matchedDetections.has(detectionIndex)) return
      tracks.push({
        id: nextTrackId++,
        keyframes: [detection]
      })
    })
  })

  return tracks
}

function buildSegments(tracks, sampleSpacing) {
  const segments = []

  tracks.forEach((track) => {
    const keyframes = track.keyframes
    if (!keyframes.length) return

    for (let index = 0; index < keyframes.length - 1; index += 1) {
      const current = keyframes[index]
      const next = keyframes[index + 1]
      const bridgeGap = next._time - current._time
      const maxBridge = Math.max(current._sampleDuration || sampleSpacing, sampleSpacing) * 4 + 0.08

      if (bridgeGap > 0 && bridgeGap <= maxBridge) {
        segments.push({
          id: `interp_${track.id}_${index}`,
          _mode: 'interp',
          _start: current._time,
          _end: next._time,
          _from: current,
          _to: next
        })
        continue
      }

      const fallbackHoldEnd = Math.min(
        current._end,
        current._time + Math.min(Math.max(current._sampleDuration || sampleSpacing, sampleSpacing) * 0.9, 0.24)
      )
      segments.push({
        id: `hold_${track.id}_${index}`,
        _mode: 'hold',
        _start: current._time,
        _end: fallbackHoldEnd,
        _from: current,
        _to: current
      })
    }

    const last = keyframes[keyframes.length - 1]
    const previous = keyframes[keyframes.length - 2]
    const tailGap = previous
      ? Math.max(last._time - previous._time, sampleSpacing)
      : Math.max(last._sampleDuration || sampleSpacing, sampleSpacing)
    const tailEnd = Math.min(last._end, last._time + Math.min(tailGap * 0.9, 0.24))
    segments.push({
      id: `tail_${track.id}`,
      _mode: 'hold',
      _start: last._time,
      _end: tailEnd,
      _from: last,
      _to: last
    })
  })

  return segments.sort((a, b) => a._start - b._start)
}

function computeIoU(a, b) {
  const ax1 = Number(a.x) || 0
  const ay1 = Number(a.y) || 0
  const ax2 = ax1 + (Number(a.width) || 0)
  const ay2 = ay1 + (Number(a.height) || 0)
  const bx1 = Number(b.x) || 0
  const by1 = Number(b.y) || 0
  const bx2 = bx1 + (Number(b.width) || 0)
  const by2 = by1 + (Number(b.height) || 0)

  const intersectionWidth = Math.max(0, Math.min(ax2, bx2) - Math.max(ax1, bx1))
  const intersectionHeight = Math.max(0, Math.min(ay2, by2) - Math.max(ay1, by1))
  const intersection = intersectionWidth * intersectionHeight
  const union = (Number(a.width) || 0) * (Number(a.height) || 0) + (Number(b.width) || 0) * (Number(b.height) || 0) - intersection

  if (union <= 0) return 0
  return intersection / union
}

function computeCenterDistance(a, b) {
  const dx = (a._centerX || 0) - (b._centerX || 0)
  const dy = (a._centerY || 0) - (b._centerY || 0)
  return Math.sqrt(dx * dx + dy * dy)
}

function isSegmentActive(segment, time) {
  if (time < segment._start) return false
  if (segment._mode === 'interp') {
    return time < segment._end - 0.0001
  }
  return time <= segment._end + 0.0001
}

function materializeSegmentBox(segment, time) {
  const from = segment._from
  const to = segment._to

  if (segment._mode !== 'interp' || segment._end <= segment._start) {
    return from
  }

  const ratio = Math.min(Math.max((time - segment._start) / (segment._end - segment._start), 0), 1)
  const confidence = Number(from.confidence || 0) + (Number(to.confidence || 0) - Number(from.confidence || 0)) * ratio

  return {
    ...from,
    x: Number(from.x || 0) + (Number(to.x || 0) - Number(from.x || 0)) * ratio,
    y: Number(from.y || 0) + (Number(to.y || 0) - Number(from.y || 0)) * ratio,
    width: Number(from.width || 0) + (Number(to.width || 0) - Number(from.width || 0)) * ratio,
    height: Number(from.height || 0) + (Number(to.height || 0) - Number(from.height || 0)) * ratio,
    confidence,
    _labelText: ` ${from.label} ${(confidence * 100).toFixed(0)}% `,
  }
}

function getPlaybackSurfaceElement() {
  return art?.template?.$player || containerRef.value || null
}

function ensureCanvasMount() {
  const canvas = canvasRef.value
  const host = art?.template?.$layer || getPlaybackSurfaceElement()
  if (!canvas || !host || canvas.parentElement === host) return
  host.appendChild(canvas)
}

function computeDrawMetrics(video, surface) {
  const surfaceRect = surface.getBoundingClientRect()
  const canvasWidth = Math.round(surfaceRect.width)
  const canvasHeight = Math.round(surfaceRect.height)
  const videoWidth = video.videoWidth
  const videoHeight = video.videoHeight
  const videoBoxWidth = Math.round(video.clientWidth || canvasWidth)
  const videoBoxHeight = Math.round(video.clientHeight || canvasHeight)
  const videoRect = video.getBoundingClientRect()
  const baseOffsetX = Math.round(videoRect.left - surfaceRect.left)
  const baseOffsetY = Math.round(videoRect.top - surfaceRect.top)

  if (
    !canvasWidth ||
    !canvasHeight ||
    !videoWidth ||
    !videoHeight ||
    !videoBoxWidth ||
    !videoBoxHeight
  ) {
    return null
  }

  const videoRatio = videoWidth / videoHeight
  const boxRatio = videoBoxWidth / videoBoxHeight

  let drawWidth = 0
  let drawHeight = 0
  let offsetX = baseOffsetX
  let offsetY = baseOffsetY

  if (boxRatio > videoRatio) {
    drawHeight = videoBoxHeight
    drawWidth = Math.round(drawHeight * videoRatio)
    offsetX += Math.round((videoBoxWidth - drawWidth) / 2)
  } else {
    drawWidth = videoBoxWidth
    drawHeight = Math.round(drawWidth / videoRatio)
    offsetY += Math.round((videoBoxHeight - drawHeight) / 2)
  }

  if (
    lastDrawMetrics &&
    lastCanvasWidth === canvasWidth &&
    lastCanvasHeight === canvasHeight &&
    lastVideoWidth === drawWidth &&
    lastVideoHeight === drawHeight
  ) {
    return lastDrawMetrics
  }

  lastCanvasWidth = canvasWidth
  lastCanvasHeight = canvasHeight
  lastVideoWidth = drawWidth
  lastVideoHeight = drawHeight
  lastDrawMetrics = { canvasWidth, canvasHeight, drawWidth, drawHeight, offsetX, offsetY }

  return lastDrawMetrics
}

function getActiveBoxes(time) {
  if (!preparedSegments.length) return []

  if (lastRenderedTime >= 0 && time + 0.0001 < lastRenderedTime) {
    nextSegmentStartIndex = 0
    activeSegments = []
  }

  while (nextSegmentStartIndex < preparedSegments.length && preparedSegments[nextSegmentStartIndex]._start <= time + 0.0001) {
    activeSegments.push(preparedSegments[nextSegmentStartIndex])
    nextSegmentStartIndex += 1
  }

  activeSegments = activeSegments.filter(segment => isSegmentActive(segment, time))
  const activeBoxes = activeSegments.map(segment => materializeSegmentBox(segment, time))
  if (activeBoxes.length > 0) {
    return activeBoxes
  }

  return getNearestFrameFallbackBoxes(time)
}

function getNearestFrameFallbackBoxes(time) {
  if (!preparedFrameBuckets.length) return []

  let nearestBucket = null
  let nearestDistance = Number.POSITIVE_INFINITY

  for (const bucket of preparedFrameBuckets) {
    const distance = Math.abs(bucket.time - time)
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestBucket = bucket
    }
  }

  const tolerance = Math.min(Math.max(estimatedSampleSpacing * 1.1, 0.12), 0.4)
  if (!nearestBucket || nearestDistance > tolerance) {
    return []
  }

  return nearestBucket.detections
}

function syncDisplayedTime(time, forceEmit = false) {
  displayTime.value = time

  const roundedTime = Number(time.toFixed(3))
  if (!forceEmit && Math.abs(roundedTime - lastEmittedTime) < 0.03) {
    return
  }

  lastEmittedTime = roundedTime
  emit('time-update', roundedTime)
}

// Canvas rendering
function renderCanvas(force = false, explicitTime = null) {
  const video = getVideoElement()
  const canvas = canvasRef.value
  const surface = getPlaybackSurfaceElement()
  if (!video || !canvas || !surface) return

  ensureCanvasMount()

  if (!isOverlayMode.value) {
    if (!canvasContext) {
      canvasContext = canvas.getContext('2d')
    }
    canvasContext?.clearRect(0, 0, lastCanvasWidth || canvas.width, lastCanvasHeight || canvas.height)
    return
  }

  const time = explicitTime ?? video.currentTime
  syncDisplayedTime(time, force)

  if (!force && Math.abs(time - lastRenderedTime) < 1 / 240) {
    return
  }

  const metrics = computeDrawMetrics(video, surface)
  if (!canvasContext) {
    canvasContext = canvas.getContext('2d')
  }
  const ctx = canvasContext
  if (!ctx) return

  if (!metrics) {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    return
  }

  const { canvasWidth, canvasHeight, drawWidth, drawHeight, offsetX, offsetY } = metrics
  const dpr = window.devicePixelRatio || 1

  if (canvas.width !== Math.round(canvasWidth * dpr) || canvas.height !== Math.round(canvasHeight * dpr) || lastCanvasDpr !== dpr) {
    canvas.width = Math.round(canvasWidth * dpr)
    canvas.height = Math.round(canvasHeight * dpr)
    canvas.style.width = `${canvasWidth}px`
    canvas.style.height = `${canvasHeight}px`
    canvasContext = canvas.getContext('2d')
    lastCanvasDpr = dpr
  }
  canvasContext?.setTransform(dpr, 0, 0, dpr, 0, 0)

  const currentBoxes = props.analysis ? analysisBoxes(time) : getActiveBoxes(time)
  lastRenderedTime = time

  ctx.clearRect(0, 0, canvasWidth, canvasHeight)
  if (props.analysis) renderAnalysisLayers(ctx,metrics,time)
  const labelFontSize = Math.max(10, Math.min(14, Math.round(drawWidth / 90)))
  const lineWidth = Math.max(2, Math.min(3, Math.round(drawWidth / 560)))
  const labelHeight = Math.max(18, Math.round(labelFontSize * 1.35))
  ctx.font = `700 ${labelFontSize}px "Segoe UI", sans-serif`
  ctx.textBaseline = 'alphabetic'
  currentBoxes.forEach(box => {
    const x = offsetX + (box.x * drawWidth)
    const y = offsetY + (box.y * drawHeight)
    const w = box.width * drawWidth
    const h = box.height * drawHeight

    const isAlert = box.type === 'alert'
    const color = isAlert ? '#ffb4ab' : '#85d2f6'
    const bgColor = isAlert ? 'rgba(255, 180, 171, 0.2)' : 'rgba(133, 210, 246, 0.2)'
    const textColor = isAlert ? '#93000a' : '#003548'

    ctx.setLineDash(box._held ? [4, 3] : [])
    ctx.beginPath()
    ctx.rect(x, y, w, h)
    ctx.strokeStyle = color
    ctx.lineWidth = lineWidth
    ctx.stroke()

    if (isAlert) {
      ctx.fillStyle = bgColor
      ctx.fill()
    }

    ctx.setLineDash([])
    ctx.fillStyle = color
    const textWidth = ctx.measureText(box._labelText).width

    const labelX = Math.max(offsetX, Math.min(x - 1, offsetX + drawWidth - textWidth - 10))
    const labelY = Math.max(offsetY, y - labelHeight)
    ctx.beginPath()
    ctx.rect(labelX, labelY, textWidth + 10, labelHeight)
    ctx.fill()

    ctx.fillStyle = textColor
    ctx.fillText(box._labelText, labelX + 4, labelY + labelHeight - 5)
  })
}

let heatSurface = null
let serverFrames = []
let serverTails = new Map()
watch(() => props.analysis, value => {
  heatSurface = null
  serverFrames = []
  serverTails = new Map()
  if(value) {
    const frames = new Map()
    for(const point of value.tracks || []) {
      if(!point.observed) continue
      if(!frames.has(point.timestamp_ms)) frames.set(point.timestamp_ms,[])
      frames.get(point.timestamp_ms).push(point)
      if(!serverTails.has(point.track_id)) serverTails.set(point.track_id,[])
      serverTails.get(point.track_id).push(point)
    }
    serverFrames=[...frames.entries()].sort((a,b)=>a[0]-b[0])
    const grid=value.heatmap
    if(grid){
      heatSurface=document.createElement('canvas');heatSurface.width=grid.width;heatSurface.height=grid.height
      const context=heatSurface.getContext('2d'),pixels=context.createImageData(grid.width,grid.height)
      grid.values_display.forEach((row,y)=>row.forEach((v,x)=>{const i=(y*grid.width+x)*4;pixels.data[i]=56;pixels.data[i+1]=189;pixels.data[i+2]=248;pixels.data[i+3]=Math.round(Math.max(0,Math.min(1,v))*235)}))
      context.putImageData(pixels,0,0)
    }
  }
  nextTick(()=>renderCanvas(true,getVideoElement()?.currentTime ?? 0))
},{immediate:true})
function analysisBoxes(time){
  if(!props.analysis.layers.boxes) return []
  let left=0,right=serverFrames.length-1,index=-1
  while(left<=right){const mid=(left+right)>>1;if(serverFrames[mid][0]<=time*1000+0.001){index=mid;left=mid+1}else right=mid-1}
  if(index<0 || time*1000-serverFrames[index][0]>Math.min(250,Math.max(50,1200/props.analysis.fps)))return []
  const held = time*1000-serverFrames[index][0] > 1000/props.analysis.fps
  return serverFrames[index][1].map(p=>({x:p.bbox_xywhn[0],y:p.bbox_xywhn[1],width:p.bbox_xywhn[2],height:p.bbox_xywhn[3],_held:held,_labelText:` ${p.label} #${p.track_id} · ${held?'保持':'观测'}@${(p.timestamp_ms/1000).toFixed(2)}s `}))
}
function renderAnalysisLayers(ctx,m,time){
  const a=props.analysis,project=p=>[m.offsetX+p[0]*m.drawWidth,m.offsetY+p[1]*m.drawHeight]
  ctx.save()
  ctx.beginPath();ctx.rect(m.offsetX,m.offsetY,m.drawWidth,m.drawHeight);ctx.clip()
  if(a.layers.heatmap && heatSurface){ctx.globalAlpha=a.layers.opacity;ctx.imageSmoothingEnabled=false;ctx.drawImage(heatSurface,m.offsetX,m.offsetY,m.drawWidth,m.drawHeight);ctx.globalAlpha=1}
  if(a.layers.tails || a.layers.fullTracks){
    ctx.strokeStyle='#38bdf8';ctx.lineWidth=2
    for(const points of serverTails.values()){
      let previous=null
      ctx.beginPath()
      for(const p of points){
        if(!a.layers.fullTracks && p.timestamp_ms>time*1000)break
        if(!a.layers.fullTracks && p.timestamp_ms<(time-a.layers.tailSeconds)*1000)continue
        const [x,y]=project(p.center_xyn)
        if(!previous || (p.timestamp_ms-previous.timestamp_ms)/1000>a.allowedGap || p.segment_id!==previous.segment_id)ctx.moveTo(x,y);else ctx.lineTo(x,y)
        previous=p
      }
      ctx.stroke()
    }
  }
  if(a.roi?.length){ctx.beginPath();a.roi.forEach((p,i)=>{const[x,y]=project(p);if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y)});ctx.closePath();ctx.strokeStyle='#fbbf24';ctx.setLineDash([5,4]);ctx.lineWidth=2;ctx.stroke()}
  ctx.restore()
}
function pickRoiPoint(event){
  if(!props.analysis?.layers.roiEditing)return
  const video=getVideoElement(),surface=getPlaybackSurfaceElement()
  if(!video||!surface)return
  const m=computeDrawMetrics(video,surface),rect=surface.getBoundingClientRect()
  if(!m)return
  const x=(event.clientX-rect.left-m.offsetX)/m.drawWidth,y=(event.clientY-rect.top-m.offsetY)/m.drawHeight
  if(x>=0&&x<=1&&y>=0&&y<=1)emit('roi-point',[Number(x.toFixed(4)),Number(y.toFixed(4))])
}

function startRenderLoop() {
  const video = getVideoElement()
  if (!video) return

  stopRenderLoop()

  const hasVideoFrameCallback = typeof video.requestVideoFrameCallback === 'function'
  const isVideoActivelyPlaying = () => !video.paused && !video.ended && video.readyState >= 2

  function loop(now, metadata) {
    const frameTime = metadata?.mediaTime ?? video.currentTime
    renderCanvas(false, frameTime)

    isPlaying.value = isVideoActivelyPlaying()
    if (!isVideoActivelyPlaying()) {
      animationFrameId = null
      return
    }

    if (hasVideoFrameCallback) {
      animationFrameId = video.requestVideoFrameCallback(loop)
      return
    }

    animationFrameId = requestAnimationFrame(loop)
  }

  if (hasVideoFrameCallback) {
    animationFrameId = video.requestVideoFrameCallback(loop)
    return
  }

  animationFrameId = requestAnimationFrame(loop)
}

function stopRenderLoop() {
  const video = getVideoElement()
  if (video && typeof video.cancelVideoFrameCallback === 'function' && animationFrameId) {
    video.cancelVideoFrameCallback(animationFrameId)
    animationFrameId = null
    return
  }

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
}

function ensureResizeObserver() {
  const surface = getPlaybackSurfaceElement()
  if (!surface || resizeObserver) return

  resizeObserver = new ResizeObserver(() => {
    requestAnimationFrame(() => {
      ensureCanvasMount()
      renderCanvas(true, getVideoElement()?.currentTime ?? 0)
    })
  })
  resizeObserver.observe(surface)
}

function teardownPlaybackSurface() {
  stopRenderLoop()
  isPlaying.value = false
  lastRenderedTime = -1
  lastEmittedTime = -1
  lastDrawMetrics = null
  lastCanvasWidth = 0
  lastCanvasHeight = 0
  lastVideoWidth = 0
  lastVideoHeight = 0
  activeSegments = []
  nextSegmentStartIndex = 0
  canvasContext = null
  lastCanvasDpr = 0
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
}

function syncPlaybackSurface() {
  nextTick(() => {
    ensureArtPlayer()
    const video = getVideoElement()
    if (!video) return

    ensureResizeObserver()
    renderCanvas(true, video.currentTime)

    if (video.readyState >= 1 && video.videoWidth > 0 && video.videoHeight > 0) {
      startRenderLoop()
      return
    }

    stopRenderLoop()
    video.load()
  })
}

// Setup/cleanup based on status
watch(() => props.status, (newStatus) => {
  if (newStatus === 'playing') {
    syncPlaybackSurface()
  } else {
    teardownPlaybackSurface()
  }
}, { immediate: true })

watch(() => props.videoUrl, () => {
  if (props.status !== 'playing') return
  lastRenderedTime = -1
  lastEmittedTime = -1
  resetVideoElement(props.playbackMode === 'overlay')
})

watch(() => props.resultVideoUrl, () => {
  if (props.status !== 'playing' || props.playbackMode !== 'result') return
  lastRenderedTime = -1
  lastEmittedTime = -1
  resetVideoElement(true)
})

watch(() => props.playbackMode, () => {
  lastRenderedTime = -1
  lastEmittedTime = -1
  if (props.status !== 'playing') return
  resetVideoElement(true)
})

watch(() => props.boxes, () => {
  prepareBoxes(props.boxes)
  if (props.status !== 'playing') return
  nextTick(() => {
    renderCanvas(true, getVideoElement()?.currentTime ?? 0)
  })
}, { deep: false, immediate: true })

// Auto-scroll logs
watch(() => props.logs, () => {
  nextTick(() => {
    if (logsContainerRef.value) {
      logsContainerRef.value.scrollTop = logsContainerRef.value.scrollHeight
    }
  })
}, { deep: true })

onUnmounted(() => {
  teardownPlaybackSurface()
  destroyArtPlayer()
})

// Timestamp helper
function getTimestamp() {
  return new Date().toISOString().split('T')[1]?.slice(0, 8) || '00:00:00'
}

function formatTime(sec) {
  if (!sec || isNaN(sec)) return '00:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
</script>

<style scoped>
:deep(.art-video-player) {
  width: 100%;
  height: 100%;
  background: #000;
}

:deep(.art-video-player .art-video) {
  object-fit: contain;
  object-position: center center;
  background: #000;
}

:deep(.art-video-player .art-layers) {
  display: flex;
}

:deep(.art-video-player .art-mask),
:deep(.art-video-player .art-bottom),
:deep(.art-video-player .art-top),
:deep(.art-video-player .art-contextmenus),
:deep(.art-video-player .art-settings) {
  border-radius: 0;
}

:deep(.art-video-player.art-fullscreen),
:deep(.art-video-player.art-fullscreen-web) {
  width: 100% !important;
  height: 100% !important;
}
</style>
