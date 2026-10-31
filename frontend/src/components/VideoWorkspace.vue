<template>
  <div class="workspace">
    <header class="bar">
      <div class="title">
        <IconMovie class="title-icon" />
        <span class="name" :title="fileName">{{ fileName || '未选择视频' }}</span>
        <span v-if="isDemo" class="tag tag-warn">合成演示</span>
      </div>
      <div class="actions">
        <UiSegmented v-if="status === 'playing' && !analysis && resultVideoUrl" :model-value="playbackMode" @update:model-value="setPlaybackMode" :options="modeOptions" aria-label="播放内容" />
        <UiTooltip v-if="status !== 'idle'" text="关闭视频">
          <button class="btn btn-ghost btn-sm btn-icon" @click="$emit('close')" aria-label="关闭视频"><IconX /></button>
        </UiTooltip>
      </div>
    </header>

    <div class="body">
      <div v-if="status === 'idle'" class="idle">
        <div
          class="drop"
          :class="{ dragging: isDragging }"
          @dragenter.prevent="onDragEnter"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop"
        >
          <IconUpload class="drop-icon" />
          <h2>拖入 MP4 视频开始</h2>
          <p class="note">视频保存在本地后端。上传后在右侧选择注册模型创建分析，或从左侧视频库打开已有视频。</p>
          <button class="btn" @click="openFilePicker"><IconUpload />选择文件</button>
        </div>
        <input ref="fileInputRef" type="file" accept="video/mp4" class="sr-only" tabindex="-1" @change="onFilePicked" />
      </div>

      <div v-if="status === 'processing'" class="uploading" role="status">
        <div class="upload-card">
          <div class="upload-head"><span>正在上传</span><span class="tnum">{{ progress }}%</span></div>
          <div class="progress"><span :style="{ width: `${progress}%` }" /></div>
          <ol ref="logsContainerRef" class="log">
            <li v-for="(log, idx) in logs" :key="idx" :class="{ warn: log.includes('WARN'), err: log.includes('ERR') }">{{ log }}</li>
          </ol>
        </div>
      </div>

      <div v-if="status === 'playing'" class="stage">
        <div ref="containerRef" class="player">
          <div ref="playerHostRef" class="player-host"></div>
          <canvas
            ref="canvasRef"
            :style="{ pointerEvents: analysis?.layers.roiEditing ? 'auto' : 'none', cursor: analysis?.layers.roiEditing ? 'crosshair' : 'default' }"
            @click="pickRoiPoint"
            class="overlay-canvas"
          />
        </div>
        <div v-if="analysis?.layers.roiEditing" class="hud hud-top"><IconPointer />在画面上点选 ROI 顶点，至少 3 个，完成后到“统计”应用</div>
        <div v-if="analysis?.layers.heatmap && analysis?.heatmap" class="hud hud-legend">
          <span class="ramp" />
          <span class="tnum">0 – {{ heatPeakText }}</span>
          <span class="sep" />
          <span>画面相对占据度，非海底地理坐标</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onUnmounted, nextTick } from 'vue'
import { IconMovie, IconX, IconUpload, IconPointer } from '@tabler/icons-vue'
import UiSegmented from './ui/UiSegmented.vue'
import UiTooltip from './ui/UiTooltip.vue'
import { trackColor, inferno } from '../lib/palette'
import { activeVideo, videoAspect } from '../lib/playback'
import { installPlayerControls } from '../lib/playerControls'
import { toast } from '../lib/toast'

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

const emit = defineEmits(['roi-point', 'file-drop', 'close', 'time-update', 'update:playback-mode'])
const modeOptions = [{ value: 'overlay', label: '叠加层' }, { value: 'result', label: '推理视频' }]
const isDemo = computed(() => /synthetic|合成|DEMO/i.test(props.fileName || ''))
const heatPeakText = computed(() => {
  const grid = props.analysis?.heatmap
  return grid ? `${Math.max(0, ...grid.values_raw.flat()).toFixed(2)} track-s` : ''
})

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
let Artplayer = null
let unmounted = false
// Artplayer is only needed once a video plays; keep it out of the initial bundle.
const loadArtplayer = () => Artplayer ? Promise.resolve() : import('artplayer').then(m => { Artplayer = m.default })
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
  if (art || !Artplayer || !playerHostRef.value) return

  art = new Artplayer({
    container: playerHostRef.value,
    url: activeVideoUrl.value || '',
    theme: '#61c7c2',
    autoplay: true,
    autoSize: false,
    autoMini: false,
    loop: true,
    fullscreen: true,
    fullscreenWeb: true,
    setting: false,
    playbackRate: true,
    hotkey: true,
    miniProgressBar: true,
    fastForward: true,
    lock: true,
    autoOrientation: true,
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

  installPlayerControls(art, { fps: () => props.analysis?.fps || 0, snapshot: saveSnapshot })
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

// Saves the current frame with the visible overlay, at the video's resolution (capped at 1920 px wide).
function saveSnapshot() {
  const video = getVideoElement(), overlay = canvasRef.value
  if (!video?.videoWidth) return
  const scale = Math.min(1, 1920 / video.videoWidth)
  const out = document.createElement('canvas')
  out.width = Math.round(video.videoWidth * scale)
  out.height = Math.round(video.videoHeight * scale)
  const ctx = out.getContext('2d')
  ctx.drawImage(video, 0, 0, out.width, out.height)
  const m = lastDrawMetrics, dpr = lastCanvasDpr
  if (isOverlayMode.value && m && overlay && dpr) ctx.drawImage(overlay, m.offsetX * dpr, m.offsetY * dpr, m.drawWidth * dpr, m.drawHeight * dpr, 0, 0, out.width, out.height)
  const name = `${(props.fileName || 'frame').replace(/\.[^.]+$/, '')}-${video.currentTime.toFixed(2)}s.png`
  try {
    out.toBlob(blob => {
      if (!blob) return
      const url = URL.createObjectURL(blob), a = document.createElement('a')
      a.href = url
      a.download = name
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      toast({ title: '已保存截图', desc: name, type: 'success' })
    }, 'image/png')
  } catch {
    toast({ title: '无法截图', desc: '视频来源不允许读取画面。', type: 'error' })
  }
}

function destroyArtPlayer() {
  if (!art) return
  if (activeVideo.value === art.video) activeVideo.value = null
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
  activeVideo.value = video

  ensureCanvasMount()
  videoDuration.value = video.duration || 0
  isPlaying.value = !video.paused && !video.ended
}

function handleArtMetadataReady() {
  const video = getVideoElement()
  if (!video) return
  activeVideo.value = video
  if (video.videoWidth && video.videoHeight) videoAspect.value = video.videoWidth / video.videoHeight

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
  drawBoxes(ctx, currentBoxes, metrics)
}

const LABEL_FONT = '"Inter Variable", Inter, "HarmonyOS Sans SC", sans-serif'

function roundedRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

// Boxes carry the identity color; labels sit on a filled pill so they stay legible on bright water.
function drawBoxes(ctx, boxes, { drawWidth, drawHeight, offsetX, offsetY }) {
  const fontSize = Math.max(10, Math.min(13, Math.round(drawWidth / 100)))
  const lineWidth = drawWidth > 1400 ? 2 : 1.5
  const labelHeight = Math.round(fontSize * 1.55)
  ctx.font = `600 ${fontSize}px ${LABEL_FONT}`
  ctx.textBaseline = 'middle'
  for (const box of boxes) {
    const x = offsetX + box.x * drawWidth, y = offsetY + box.y * drawHeight
    const w = box.width * drawWidth, h = box.height * drawHeight
    const color = box._color || (box.type === 'alert' ? '#ee8790' : '#61c7c2')
    ctx.setLineDash(box._held ? [5, 4] : [])
    ctx.lineWidth = lineWidth
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.45)'
    ctx.strokeRect(x - 0.5, y - 0.5, w + 1, h + 1)
    ctx.strokeStyle = color
    ctx.strokeRect(x, y, w, h)
    ctx.setLineDash([])
    const text = box._labelText.trim()
    const textWidth = ctx.measureText(text).width
    const pillW = textWidth + 10
    const labelX = Math.max(offsetX, Math.min(x, offsetX + drawWidth - pillW))
    const above = y - labelHeight - 2 >= offsetY
    const labelY = above ? y - labelHeight - 2 : Math.min(offsetY + drawHeight - labelHeight, y + h + 2)
    roundedRect(ctx, labelX, labelY, pillW, labelHeight, 3)
    ctx.fillStyle = box._held ? 'rgba(10, 20, 28, 0.82)' : color
    ctx.fill()
    if (box._held) { ctx.strokeStyle = color; ctx.lineWidth = 1; ctx.stroke() }
    ctx.fillStyle = box._held ? color : '#0a141c'
    ctx.fillText(text, labelX + 5, labelY + labelHeight / 2 + 0.5)
  }
}

// Analysis layers: frames and tails rebuild only when the loaded observations change; the heat raster only when the grid changes.
let heatSurface = null
let serverFrames = []
let serverTails = new Map()
watch(() => props.analysis?.tracks, points => {
  serverFrames = []
  serverTails = new Map()
  const frames = new Map()
  for (const point of points || []) {
    if (!point.observed) continue
    if (!frames.has(point.timestamp_ms)) frames.set(point.timestamp_ms, [])
    frames.get(point.timestamp_ms).push(point)
    if (!serverTails.has(point.track_id)) serverTails.set(point.track_id, [])
    serverTails.get(point.track_id).push(point)
  }
  serverFrames = [...frames.entries()].sort((a, b) => a[0] - b[0])
  scheduleRedraw()
}, { immediate: true })
watch(() => props.analysis?.heatmap, grid => {
  heatSurface = null
  if (grid) {
    heatSurface = document.createElement('canvas')
    heatSurface.width = grid.width
    heatSurface.height = grid.height
    const context = heatSurface.getContext('2d'), pixels = context.createImageData(grid.width, grid.height)
    grid.values_display.forEach((row, y) => row.forEach((v, x) => {
      if (!(v > 0)) return
      const value = Math.min(1, v), [r, g, b] = inferno(value), i = (y * grid.width + x) * 4
      pixels.data[i] = r; pixels.data[i + 1] = g; pixels.data[i + 2] = b
      pixels.data[i + 3] = Math.round((0.35 + 0.65 * Math.sqrt(value)) * 255)
    }))
    context.putImageData(pixels, 0, 0)
  }
  scheduleRedraw()
}, { immediate: true })
watch(() => props.analysis && [props.analysis.layers, props.analysis.roi, props.analysis.roiDraft], scheduleRedraw)
function scheduleRedraw() { nextTick(() => renderCanvas(true, getVideoElement()?.currentTime ?? 0)) }

function analysisBoxes(time){
  if(!props.analysis.layers.boxes) return []
  let left=0,right=serverFrames.length-1,index=-1
  while(left<=right){const mid=(left+right)>>1;if(serverFrames[mid][0]<=time*1000+0.001){index=mid;left=mid+1}else right=mid-1}
  if(index<0 || time*1000-serverFrames[index][0]>Math.min(250,Math.max(50,1200/props.analysis.fps)))return []
  const held = time*1000-serverFrames[index][0] > 1000/props.analysis.fps
  return serverFrames[index][1].map(p=>({x:p.bbox_xywhn[0],y:p.bbox_xywhn[1],width:p.bbox_xywhn[2],height:p.bbox_xywhn[3],_held:held,_color:trackColor(p.track_id),_labelText:`#${p.track_id} ${p.label} · ${held?'保持 ':''}${(p.timestamp_ms/1000).toFixed(2)} s`}))
}

const TAIL_BANDS = 5
function renderAnalysisLayers(ctx, m, time) {
  const a = props.analysis, project = p => [m.offsetX + p[0] * m.drawWidth, m.offsetY + p[1] * m.drawHeight]
  ctx.save()
  ctx.beginPath(); ctx.rect(m.offsetX, m.offsetY, m.drawWidth, m.drawHeight); ctx.clip()
  if (a.layers.heatmap && heatSurface) {
    ctx.globalAlpha = a.layers.opacity
    ctx.imageSmoothingEnabled = false
    ctx.drawImage(heatSurface, m.offsetX, m.offsetY, m.drawWidth, m.drawHeight)
    ctx.globalAlpha = 1
  }
  if (a.layers.tails || a.layers.fullTracks) {
    const now = time * 1000, tail = a.layers.tailSeconds * 1000
    ctx.lineCap = 'round'; ctx.lineJoin = 'round'
    for (const [id, points] of serverTails) {
      const color = trackColor(id)
      // Bucket segments by age so each opacity band is one path.
      const bands = Array.from({ length: TAIL_BANDS }, () => [])
      let previous = null, head = null
      for (const p of points) {
        if (!a.layers.fullTracks && p.timestamp_ms > now) break
        if (!a.layers.fullTracks && p.timestamp_ms < now - tail) { previous = null; continue }
        if (previous && (p.timestamp_ms - previous.timestamp_ms) / 1000 <= a.allowedGap && p.segment_id === previous.segment_id) {
          const age = a.layers.fullTracks ? 0 : (now - p.timestamp_ms) / tail
          bands[Math.min(TAIL_BANDS - 1, Math.floor(age * TAIL_BANDS))].push(project(previous.center_xyn), project(p.center_xyn))
        }
        previous = p
        head = p
      }
      ctx.strokeStyle = color
      bands.forEach((segments, band) => {
        if (!segments.length) return
        ctx.globalAlpha = a.layers.fullTracks ? 0.75 : 1 - band / TAIL_BANDS * 0.85
        ctx.lineWidth = a.layers.fullTracks ? 1.25 : 2 - band * 0.2
        ctx.beginPath()
        for (let i = 0; i < segments.length; i += 2) { ctx.moveTo(...segments[i]); ctx.lineTo(...segments[i + 1]) }
        ctx.stroke()
      })
      ctx.globalAlpha = 1
      if (head && !a.layers.fullTracks && now - head.timestamp_ms < 300) {
        const [hx, hy] = project(head.center_xyn)
        ctx.fillStyle = color
        ctx.beginPath(); ctx.arc(hx, hy, 2.5, 0, Math.PI * 2); ctx.fill()
      }
    }
  }
  if (a.roi?.length || a.layers.roiEditing) drawRoi(ctx, project)
  ctx.restore()
}

function drawRoi(ctx, project) {
  const editing = props.analysis.layers.roiEditing
  const points = (editing ? props.analysis.roiDraft : props.analysis.roi) || []
  if (!points.length) return
  ctx.beginPath()
  points.forEach((p, i) => { const [x, y] = project(p); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y) })
  ctx.closePath()
  ctx.fillStyle = 'rgba(234, 191, 112, 0.08)'
  ctx.fill()
  ctx.strokeStyle = '#eabf70'; ctx.setLineDash([6, 4]); ctx.lineWidth = 1.5; ctx.stroke(); ctx.setLineDash([])
  if (editing) {
    ctx.fillStyle = '#eabf70'
    for (const p of points) { const [x, y] = project(p); ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill() }
  }
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
  loadArtplayer().then(() => nextTick()).then(() => {
    if (unmounted || props.status !== 'playing') return
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
  unmounted = true
  teardownPlaybackSurface()
  destroyArtPlayer()
})

</script>

<style scoped>
.workspace { display: flex; flex-direction: column; height: 100%; min-height: 0; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); overflow: hidden; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; height: 40px; padding: 0 8px 0 12px; flex: none; box-shadow: inset 0 -1px 0 var(--line); }
.title { display: flex; align-items: center; gap: 8px; min-width: 0; }
.title-icon { color: var(--ink-3); }
.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.actions { display: flex; align-items: center; gap: 6px; }
.body { position: relative; flex: 1; min-height: 0; }
.idle { position: absolute; inset: 0; display: grid; place-items: center; padding: 24px; }
.drop { display: flex; flex-direction: column; align-items: center; gap: 10px; width: min(560px, 100%); padding: 44px 32px; border-radius: var(--radius-lg); text-align: center; background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); transition: background-color 150ms var(--ease), box-shadow 150ms var(--ease); }
.drop.dragging { background: var(--accent-soft); box-shadow: inset 0 0 0 1.5px var(--accent); }
.drop-icon { --icon-size: 28px; --icon-stroke: 1.25; color: var(--ink-3); margin-bottom: 4px; }
.drop.dragging .drop-icon { color: var(--accent); }
.drop h2 { font-size: var(--text-title); font-weight: 600; }
.drop .note { max-width: 40ch; text-wrap: pretty; margin-bottom: 8px; }
.uploading { position: absolute; inset: 0; display: grid; place-items: center; padding: 24px; }
.upload-card { width: min(480px, 100%); padding: 16px; border-radius: var(--radius-lg); background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); }
.upload-head { display: flex; justify-content: space-between; font-weight: 500; margin-bottom: 10px; }
.progress { height: 3px; border-radius: 2px; background: var(--surface-3); overflow: hidden; }
.progress > span { display: block; height: 100%; background: var(--accent); transition: width 200ms var(--ease); }
.log { max-height: 128px; overflow-y: auto; margin-top: 12px; font-family: var(--font-mono); font-size: var(--text-caption); line-height: 1.6; color: var(--ink-3); }
.log .warn { color: var(--warn); }
.log .err { color: var(--danger); }
.stage { position: absolute; inset: 0; background: var(--stage); }
.player { position: absolute; inset: 0; overflow: hidden; }
.player-host { position: absolute; inset: 0; }
.overlay-canvas { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 20; }
.hud { position: absolute; z-index: 30; display: inline-flex; align-items: center; gap: 8px; padding: 5px 9px; border-radius: var(--radius); font-size: var(--text-caption); color: oklch(0.95 0.01 205); background: oklch(0.15 0.02 240 / 0.78); backdrop-filter: blur(6px); pointer-events: none; }
.hud-top { top: 10px; left: 50%; translate: -50% 0; color: #eabf70; }
.hud-legend { left: 10px; bottom: 58px; }
.hud .ramp { width: 72px; height: 6px; border-radius: 1px; background: linear-gradient(90deg, #000004, #420a68, #932667, #dd513a, #fca50a, #fcffa4); }
.hud .sep { width: 1px; height: 10px; background: oklch(1 0 0 / 0.25); }

:deep(.art-video-player) { width: 100%; height: 100%; background: var(--stage); }
:deep(.art-video-player .art-video) { object-fit: contain; object-position: center center; background: var(--stage); }
:deep(.art-video-player .art-layers) { display: flex; }
:deep(.art-video-player.art-fullscreen), :deep(.art-video-player.art-fullscreen-web) { width: 100% !important; height: 100% !important; }
:deep(.art-video-player .art-bottom) { background-image: linear-gradient(to top, oklch(0 0 0 / 0.55), transparent); }
:deep(.art-video-player .art-control) { font-variant-numeric: tabular-nums; }
:deep(.art-video-player .rs-art-icon) { display: inline-flex; --icon-size: 20px; --icon-stroke: 1.75; }
:deep(.art-video-player .art-control-rate .art-selector-value) { min-width: 34px; font-size: 13px; font-weight: 600; text-align: center; }
:deep(.art-video-player .art-control-loop:not(.is-on)) { opacity: 0.55; }
:deep(.art-video-player .art-control-loop.is-on) { color: var(--art-theme); }
</style>
