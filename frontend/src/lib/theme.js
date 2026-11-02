import { ref, watch } from 'vue'

const stored = typeof localStorage === 'undefined' ? null : localStorage.getItem('reefscope-theme')
export const isDark = ref(stored ? stored === 'dark' : true)

watch(isDark, value => {
  document.documentElement.classList.toggle('dark', value)
  try { localStorage.setItem('reefscope-theme', value ? 'dark' : 'light') } catch { /* private mode */ }
}, { immediate: true })

// Charts read resolved token values so ECharts never receives unsupported color syntax.
export function chartTokens() {
  const probe = document.createElement('span')
  document.body.appendChild(probe)
  const read = name => {
    probe.style.color = `var(${name})`
    const value = getComputedStyle(probe).color
    return toRgb(value)
  }
  const tokens = { ink: read('--ink'), ink2: read('--ink-2'), ink3: read('--ink-3'), line: read('--line'), lineStrong: read('--line-strong'), surface: read('--surface'), surface2: read('--surface-2'), accent: read('--accent'), warn: read('--warn'), canvas: read('--canvas'), series: [read('--series-1'), read('--series-2')] }
  probe.remove()
  return tokens
}

// Computed oklch() colors serialize as oklch; rasterize through a 1px canvas to get rgb.
const ctx = typeof document === 'undefined' ? null : document.createElement('canvas').getContext('2d', { willReadFrequently: true })
function toRgb(color) {
  if (!ctx || color.startsWith('rgb')) return color
  ctx.clearRect(0, 0, 1, 1)
  ctx.fillStyle = color
  ctx.fillRect(0, 0, 1, 1)
  const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data
  return a === 255 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${(a / 255).toFixed(3)})`
}
