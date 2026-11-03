import { getCoralMask } from '../api'

// Class-index masks from the coral Run: PNG gray value 0 background, 1 non-bleached, 2 bleached.
// Decoded at most MAX_WIDTH wide; drawing with smoothing off is nearest-neighbour, so class values
// survive the downscale and any value above 2 marks the mask as invalid.
const MAX_WIDTH = 1280, CAPACITY = 24

export function createMaskStore(runId, onChange) {
  const decoded = new Map(), pending = new Map(), failed = new Set()
  const surface = document.createElement('canvas')
  let surfaceKey = '', closed = false, image = null, grid = null

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
    // Paints one mask at the on-screen size so outlines stay crisp: nearest-neighbour class lookup, then
    // a pixel is an outline when a 4-neighbour within `line` pixels shows a different visible class.
    // Outlines stay opaque; the fill alpha follows `opacity`. Repaints only when an input changes.
    paint(frame, entry, { colors, mode, opacity, width, height, line }) {
      const key = [frame, colors[1], colors[2], mode, opacity, width, height, line].join('|')
      if (key === surfaceKey) return surface
      if (surface.width !== width || surface.height !== height || !image) {
        surface.width = width; surface.height = height
        image = surface.getContext('2d').createImageData(width, height)
        grid = new Uint8Array(width * height)
      }
      const columns = new Uint32Array(width)
      for (let x = 0; x < width; x++) columns[x] = Math.min(entry.width - 1, Math.floor((x + 0.5) * entry.width / width))
      for (let y = 0; y < height; y++) {
        const row = Math.min(entry.height - 1, Math.floor((y + 0.5) * entry.height / height)) * entry.width, offset = y * width
        for (let x = 0; x < width; x++) { const c = entry.classes[row + columns[x]]; grid[offset + x] = colors[c] ? c : 0 }
      }
      const out = image.data, fill = mode === 'outline' ? 0 : Math.round(opacity * 255), edges = mode !== 'fill'
      for (let y = 0, i = 0; y < height; y++) {
        for (let x = 0; x < width; x++, i++) {
          const c = grid[i], j = i * 4
          if (!c) { out[j + 3] = 0; continue }
          let edge = false
          if (edges) {
            for (let d = 1; d <= line && !edge; d++) {
              edge = (x >= d && grid[i - d] !== c) || (x + d < width && grid[i + d] !== c) || (y >= d && grid[i - d * width] !== c) || (y + d < height && grid[i + d * width] !== c)
            }
          }
          const color = colors[c]
          out[j] = color[0]; out[j + 1] = color[1]; out[j + 2] = color[2]; out[j + 3] = edge ? 255 : fill
        }
      }
      surface.getContext('2d').putImageData(image, 0, 0)
      surfaceKey = key
      return surface
    },
    // Class index at normalized image coordinates, or null while the mask is not decoded.
    classAt(frame, u, v) {
      const entry = decoded.get(frame)
      if (!entry || u < 0 || v < 0 || u >= 1 || v >= 1) return null
      return entry.classes[Math.floor(v * entry.height) * entry.width + Math.floor(u * entry.width)]
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
