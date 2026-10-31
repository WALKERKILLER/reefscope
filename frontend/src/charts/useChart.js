import { onBeforeUnmount, onMounted, watch } from 'vue'
import { isDark, chartTokens } from '../lib/theme'

// One ECharts instance per host: lazy module load, created only once the host has a size
// (hidden tabs stay cheap), coalesced resize, theme-aware rebuild, guaranteed dispose.
export function useChart(hostRef, build) {
  let chart = null, observer = null, frame = 0, disposed = false, loading = null

  const sized = () => hostRef.value && hostRef.value.clientWidth > 0 && hostRef.value.clientHeight > 0

  async function ensure() {
    if (chart || disposed || !sized()) return chart
    loading ||= import('./echarts.js')
    const { init } = await loading
    if (disposed || !sized() || chart) return chart
    chart = init(hostRef.value, null, { renderer: 'canvas' })
    return chart
  }

  async function render() {
    const instance = await ensure()
    if (!instance || !sized()) return
    const option = build(chartTokens(), { width: hostRef.value.clientWidth, height: hostRef.value.clientHeight })
    if (option) instance.setOption(option, { notMerge: true, lazyUpdate: true })
    else instance.clear()
  }

  onMounted(() => {
    observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => { if (!sized()) return; chart?.resize(); render() })
    })
    if (hostRef.value) observer.observe(hostRef.value)
  })
  watch(isDark, () => requestAnimationFrame(render))
  onBeforeUnmount(() => {
    disposed = true
    cancelAnimationFrame(frame)
    observer?.disconnect()
    chart?.dispose()
    chart = null
  })
  return { render, chart: () => chart }
}
