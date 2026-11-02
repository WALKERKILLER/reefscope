// Track identity colors: 12 OKLCH hues 30° apart (L 0.8 for video overlays, L 0.6 for light charts).
// Multiplying the ID by 5 (coprime with 12) keeps consecutive IDs 150° apart.
const ON_VIDEO = ['#fda19a', '#fea668', '#e7b643', '#bbc855', '#81d584', '#34dbb9', '#11d6e7', '#6cc9fd', '#9ebdff', '#c3b0fd', '#eb9def', '#fd9bc2']
const ON_PAPER = ['#c65954', '#be6517', '#a1790c', '#7e8904', '#419547', '#11957c', '#0f919c', '#0b8bc0', '#567cd3', '#876cca', '#a960ae', '#bf5884']

export function trackColor(id, surface = 'video') {
  const index = ((Number(id) || 0) * 5) % 12
  return (surface === 'paper' ? ON_PAPER : ON_VIDEO)[(index + 12) % 12]
}

// Inferno colormap (matplotlib, CC0), sampled at 11 even stops; linear interpolation between stops.
export const INFERNO = ['#000004', '#160b39', '#420a68', '#6a176e', '#932667', '#bc3754', '#dd513a', '#f37819', '#fca50a', '#f6d746', '#fcffa4']
const STOPS = INFERNO.map(hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)))

export function inferno(t) {
  const x = Math.min(1, Math.max(0, t)) * (STOPS.length - 1)
  const i = Math.min(STOPS.length - 2, Math.floor(x)), f = x - i
  return STOPS[i].map((v, k) => Math.round(v + (STOPS[i + 1][k] - v) * f))
}

export const infernoGradient = `linear-gradient(90deg, ${INFERNO.join(', ')})`
