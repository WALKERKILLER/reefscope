import { h, render } from 'vue'
import { IconCamera, IconPlayerTrackNext, IconPlayerTrackPrev, IconRepeat } from '@tabler/icons-vue'

// Extra Artplayer controls for frame-accurate review. Flip and aspect-ratio stay off:
// the detection overlay assumes the native, unmirrored "contain" mapping.
export const RATES = [0.25, 0.5, 1, 1.5, 2, 4]
const rateText = rate => `${rate}×`

function icon(component) {
  const el = document.createElement('span')
  el.className = 'rs-art-icon'
  render(h(component, { size: 20, stroke: 1.75 }), el)
  return el
}

export function stepFrame(art, direction, fps) {
  const video = art.video
  if (!video || !Number.isFinite(video.duration)) return
  art.pause()
  const rate = fps > 0 ? fps : 30
  // Land just past the frame boundary so rounding never shows the previous frame.
  const frame = Math.round(video.currentTime * rate) + direction
  video.currentTime = Math.min(video.duration, Math.max(0, frame / rate + 0.001))
}

function syncRate(el, rate) {
  if (!el) return
  const value = el.querySelector('.art-selector-value')
  if (value) value.textContent = rateText(rate)
  el.querySelectorAll('.art-selector-item').forEach(item => item.classList.toggle('art-current', Number(item.dataset.value) === rate))
}

function syncLoop(el, on) {
  if (!el) return
  el.classList.toggle('is-on', on)
  el.setAttribute('aria-pressed', String(on))
  el.setAttribute('aria-label', on ? '循环播放：开' : '循环播放：关')
}

export function installPlayerControls(art, { fps, snapshot }) {
  let rateEl = null, loopEl = null
  const setRate = rate => { art.playbackRate = rate }
  const shiftRate = direction => {
    const index = RATES.findIndex(rate => rate >= art.playbackRate - 1e-6)
    const next = RATES[Math.min(RATES.length - 1, Math.max(0, (index < 0 ? RATES.length - 1 : index) + direction))]
    setRate(next)
    art.notice.show = `播放速度 ${rateText(next)}`
  }

  art.controls.add({ name: 'frame-prev', position: 'left', index: 11, html: icon(IconPlayerTrackPrev), tooltip: '上一帧（,）', click: () => stepFrame(art, -1, fps()) })
  art.controls.add({ name: 'frame-next', position: 'left', index: 12, html: icon(IconPlayerTrackNext), tooltip: '下一帧（.）', click: () => stepFrame(art, 1, fps()) })
  art.controls.add({
    name: 'rate', position: 'right', index: 15, html: rateText(1),
    selector: RATES.map(rate => ({ html: rateText(rate), value: rate, default: rate === 1 })),
    mounted: el => { rateEl = el },
    onSelect: item => { setRate(item.value); return item.html }
  })
  art.controls.add({
    name: 'loop', position: 'right', index: 16, html: icon(IconRepeat), tooltip: '循环播放',
    // Artplayer restarts on `ended` from option.loop; the media element's own loop flag stays off.
    mounted: el => { loopEl = el; syncLoop(el, art.option.loop) },
    click: () => { art.option.loop = !art.option.loop; syncLoop(loopEl, art.option.loop); art.notice.show = art.option.loop ? '循环播放：开' : '循环播放：关' }
  })
  art.controls.add({ name: 'snapshot', position: 'right', index: 18, html: icon(IconCamera), tooltip: '截图（含叠加层）', click: () => snapshot() })

  art.on('video:ratechange', () => syncRate(rateEl, art.playbackRate))
  art.hotkey.add('Comma', () => stepFrame(art, -1, fps()))
  art.hotkey.add('Period', () => stepFrame(art, 1, fps()))
  art.hotkey.add('BracketLeft', () => shiftRate(-1))
  art.hotkey.add('BracketRight', () => shiftRate(1))
}
