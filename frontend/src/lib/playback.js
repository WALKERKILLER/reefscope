import { shallowRef } from 'vue'

// The workspace keeps one active player; other views seek or sample frames through this registry.
export const activeVideo = shallowRef(null)
export const videoAspect = shallowRef(16 / 9)

export function seekTo(seconds) {
  const video = activeVideo.value
  if (video && Number.isFinite(seconds)) video.currentTime = Math.max(0, seconds)
}

export function captureFrame(maxWidth = 960) {
  const video = activeVideo.value
  if (!video?.videoWidth) return null
  const scale = Math.min(1, maxWidth / video.videoWidth)
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(video.videoWidth * scale)
  canvas.height = Math.round(video.videoHeight * scale)
  try {
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.82)
  } catch {
    return null
  }
}
