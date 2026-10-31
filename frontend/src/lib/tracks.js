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
