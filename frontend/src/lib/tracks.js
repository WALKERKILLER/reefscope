// Display-only derivations of loaded observations. Window statistics and exports stay server-side.

// Continuous observation spans per ID; a span breaks on segment change or a gap above allowedGap.
export function trackSpans(points, allowedGapSeconds) {
  const byId = new Map()
  for (const point of points) {
    if (!point.observed) continue
    let entry = byId.get(point.track_id)
    if (!entry) byId.set(point.track_id, entry = { id: point.track_id, label: point.label, first: point.timestamp_ms, last: point.timestamp_ms, count: 0, spans: [], paths: [] })
    const span = entry.spans[entry.spans.length - 1]
    const path = entry.paths[entry.paths.length - 1]
    const continuous = span && point.segment_id === span.segment && (point.timestamp_ms - span.end) / 1000 <= allowedGapSeconds && point.timestamp_ms > span.end
    if (continuous) {
      span.end = point.timestamp_ms
      path.push([point.center_xyn[0], point.center_xyn[1], point.timestamp_ms])
    } else {
      entry.spans.push({ start: point.timestamp_ms, end: point.timestamp_ms, segment: point.segment_id })
      entry.paths.push([[point.center_xyn[0], point.center_xyn[1], point.timestamp_ms]])
    }
    entry.last = Math.max(entry.last, point.timestamp_ms)
    entry.count += 1
  }
  return [...byId.values()].sort((a, b) => a.first - b.first || a.id - b.id)
}

// Observed boxes per source timestamp, deduplicated by ID within a frame.
export function observationsPerFrame(points) {
  const frames = new Map()
  for (const point of points) {
    if (!point.observed) continue
    let ids = frames.get(point.timestamp_ms)
    if (!ids) frames.set(point.timestamp_ms, ids = new Set())
    ids.add(point.track_id)
  }
  return [...frames.entries()].sort((a, b) => a[0] - b[0]).map(([t, ids]) => [t / 1000, ids.size])
}

// Mean visible IDs per one-second bin, for KPI trends.
export function visiblePerSecond(frames, duration) {
  const bins = Math.max(1, Math.ceil(duration || frames.at(-1)?.[0] || 1))
  const sum = new Float64Array(bins), n = new Uint32Array(bins)
  for (const [t, count] of frames) { const i = Math.min(bins - 1, Math.floor(t)); sum[i] += count; n[i] += 1 }
  return Array.from(sum, (s, i) => [i + 0.5, n[i] ? s / n[i] : 0])
}

// Running count of IDs first observed by each second.
export function newIdsCumulative(spans, duration) {
  const bins = Math.max(1, Math.ceil(duration || 1))
  const firsts = spans.map(s => s.first / 1000).sort((a, b) => a - b)
  const out = []
  for (let i = 0, k = 0; i <= bins; i++) { while (k < firsts.length && firsts[k] <= i) k++; out.push([i, k]) }
  return out
}

// Observed IDs in the frame shown at `time`; frames without observations count as zero.
export function visibleAt(frames, time, fps) {
  let lo = 0, hi = frames.length - 1, hit = -1
  while (lo <= hi) { const mid = (lo + hi) >> 1; if (frames[mid][0] <= time + 1e-6) { hit = mid; lo = mid + 1 } else hi = mid - 1 }
  return hit >= 0 && time - frames[hit][0] < 1 / (fps || 30) ? frames[hit][1] : 0
}

// IDs ranked by observed span (first to last observation), longest first.
export function longestStays(spans, limit = 24) {
  return spans.map(s => ({ ...s, seconds: (s.last - s.first) / 1000 })).sort((a, b) => b.seconds - a.seconds || a.id - b.id).slice(0, limit)
}
