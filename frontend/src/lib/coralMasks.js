import { getCoralMask } from '../api'

// Class-index masks from the coral Run: PNG gray value 0 background, 1 non-bleached, 2 bleached.
// Decoded at most MAX_WIDTH wide; drawing with smoothing off is nearest-neighbour, so class values
// survive the downscale and any value above 2 marks the mask as invalid.
const MAX_WIDTH = 1280, CAPACITY = 24

export function createMaskStore(runId, onChange) {
  const decoded = new Map(), pending = new Map(), failed = new Set()
  const surface = document.createElement('canvas')
  let surfaceKey = '', closed = false

  async function load(frame) {
    const controller = new AbortController()
    pending.set(frame, controller)
    try {
      const { data } = await getCoralMask(runId, frame, controller.signal)
      const bitmap = await createImageBitmap(data, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' })
      const scale = Math.min(1, MAX_WIDTH / bitmap.width)
      const width = Math.max(1, Math.round(bitmap.width * scale)), height = Math.max(1, Math.round(bitmap.height * scale))
      const canvas = document.createElement('canvas')
      canvas.width = width; canvas.height = height
      const context = canvas.getContext('2d', { willReadFrequently: true })
      context.imageSmoothingEnabled = false
      context.drawImage(bitmap, 0, 0, width, height)
      bitmap.close()
      const rgba = context.getImageData(0, 0, width, height).data, classes = new Uint8Array(width * height)
      for (let i = 0; i < classes.length; i++) {
        const value = rgba[i * 4]
        if (value > 2) throw new Error('invalid_mask')
        classes[i] = value
      }
      if (closed) return
      decoded.set(frame, { classes, width, height })
      while (decoded.size > CAPACITY) decoded.delete(decoded.keys().next().value)
    } catch (error) {
      if (closed || controller.signal.aborted) return
      failed.add(frame)
    } finally {
      pending.delete(frame)
    }
    if (!closed) onChange(frame)
  }

  function request(frame) {
    if (frame == null || closed || decoded.has(frame) || pending.has(frame) || failed.has(frame)) return
    load(frame)
  }

  return {
    // Returns the decoded mask, or null while it loads; recently used masks stay cached.
    get(frame) {
      const entry = decoded.get(frame)
      if (entry) { decoded.delete(frame); decoded.set(frame, entry); return entry }
      request(frame)
      return null
    },
    prefetch: request,
    failed: frame => failed.has(frame),
    // Colours one mask into the shared surface; recolours only when the frame or the visible classes change.
    paint(frame, entry, colors) {
      const key = `${frame}|${colors[1] || ''}|${colors[2] || ''}`
      if (key === surfaceKey) return surface
      surface.width = entry.width; surface.height = entry.height
      const context = surface.getContext('2d'), image = context.createImageData(entry.width, entry.height), out = image.data
      for (let i = 0; i < entry.classes.length; i++) {
        const color = colors[entry.classes[i]]
        if (!color) continue
        const j = i * 4
        out[j] = color[0]; out[j + 1] = color[1]; out[j + 2] = color[2]; out[j + 3] = 255
      }
      context.putImageData(image, 0, 0)
      surfaceKey = key
      return surface
    },
    close() {
      closed = true
      for (const controller of pending.values()) controller.abort()
      pending.clear(); decoded.clear()
    }
  }
}

// Latest sampled frame at or before `ms`; frames are sorted by timestamp.
export function sampleAt(frames, ms) {
  let left = 0, right = frames.length - 1, index = -1
  while (left <= right) {
    const mid = (left + right) >> 1
    if (frames[mid].timestamp_ms <= ms + 0.001) { index = mid; left = mid + 1 } else right = mid - 1
  }
  return index
}
