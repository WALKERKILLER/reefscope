// A small Markdown subset for agent answers, parsed into a tree that Vue renders without v-html.
// Audited segments (metrics, citations, flagged numbers) are atoms: they travel through the parser as
// sentinels, so a metric can sit inside bold text, a list item or a table cell and stays intact.
const OPEN = '\uE000', CLOSE = '\uE001'
const FENCE = /^\s*(```|~~~)/
const HEADING = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/
const RULE = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/
const QUOTE = /^\s{0,3}>\s?(.*)$/
const ITEM = /^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$/
const TABLE_SEP = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/
const INLINE = new RegExp([
  '`([^`\\n]+)`',
  `${OPEN}(\\d+)${CLOSE}`,
  '\\[([^\\]\\n]+)\\]\\((https?:\\/\\/[^\\s)]+)\\)',
  '\\*\\*(?=\\S)([\\s\\S]+?)\\*\\*',
  '__(?=\\S)([\\s\\S]+?)__',
  '~~(?=\\S)([\\s\\S]+?)~~',
  '\\*(?=[^\\s*])([\\s\\S]+?)\\*',
  '(?<![A-Za-z0-9])_(?=\\S)([^_\\n]+?)_(?![A-Za-z0-9])'
].join('|'), 'g')

const plainText = part => Object.keys(part).length === 1 && typeof part.text === 'string'

export function toSource(parts) {
  const atoms = []
  const text = parts.map(part => {
    if (plainText(part)) return part.text.replace(/[\uE000\uE001]/g, '')
    atoms.push(part)
    return `${OPEN}${atoms.length - 1}${CLOSE}`
  }).join('')
  return { text, atoms }
}

const indent = line => line.replace(/\t/g, '    ').match(/^ */)[0].length
const isTableStart = (lines, i) => lines[i].includes('|') && TABLE_SEP.test(lines[i + 1] || '') && (lines[i + 1] || '').includes('-')
const startsBlock = (lines, i) => FENCE.test(lines[i]) || HEADING.test(lines[i]) || RULE.test(lines[i]) || QUOTE.test(lines[i]) || ITEM.test(lines[i]) || isTableStart(lines, i)
const cells = line => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => parseInline(cell.trim()))

export function parseBlocks(lines) {
  const blocks = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (FENCE.test(line)) {
      const fence = line.trim().slice(0, 3), body = []
      for (i++; i < lines.length && !lines[i].trim().startsWith(fence); i++) body.push(lines[i])
      blocks.push({ type: 'code', children: parseInline(body.join('\n'), true) })
      i++
    } else if (HEADING.test(line)) {
      const [, marks, text] = HEADING.exec(line)
      blocks.push({ type: 'heading', level: marks.length, children: parseInline(text) })
      i++
    } else if (RULE.test(line)) {
      blocks.push({ type: 'rule' })
      i++
    } else if (QUOTE.test(line)) {
      const inner = []
      for (; i < lines.length && QUOTE.test(lines[i]); i++) inner.push(QUOTE.exec(lines[i])[1])
      blocks.push({ type: 'quote', children: parseBlocks(inner) })
    } else if (isTableStart(lines, i)) {
      const head = cells(line)
      const align = cells(lines[i + 1]).map((_, n) => {
        const spec = lines[i + 1].trim().replace(/^\|/, '').replace(/\|$/, '').split('|')[n]?.trim() || ''
        return spec.endsWith(':') ? (spec.startsWith(':') ? 'center' : 'end') : 'start'
      })
      const rows = []
      for (i += 2; i < lines.length && lines[i].trim() && lines[i].includes('|'); i++) rows.push(cells(lines[i]))
      blocks.push({ type: 'table', head, align, rows })
    } else if (ITEM.test(line)) {
      const { node, next } = parseList(lines, i)
      blocks.push(node)
      i = next
    } else {
      const body = []
      for (; i < lines.length && lines[i].trim() && (body.length === 0 || !startsBlock(lines, i)); i++) body.push(lines[i].trim())
      blocks.push({ type: 'paragraph', children: parseInline(body.join('\n')) })
    }
  }
  return blocks
}

function parseList(lines, start) {
  const first = ITEM.exec(lines[start]), base = indent(first[1]), ordered = /\d/.test(first[2])
  const list = { type: 'list', ordered, start: ordered ? parseInt(first[2], 10) : null, items: [] }
  const item = () => list.items.at(-1)
  let i = start
  while (i < lines.length) {
    const match = ITEM.exec(lines[i])
    if (match && indent(match[1]) === base) {
      if (/\d/.test(match[2]) !== ordered) break
      list.items.push({ lines: [match[3]], children: [] })
      i++
    } else if (match && indent(match[1]) > base) {
      const sub = parseList(lines, i)
      item().children.push(sub.node)
      i = sub.next
    } else if (!match && lines[i].trim() && (indent(lines[i]) > base || !startsBlock(lines, i)) && lines[i - 1]?.trim()) {
      item().lines.push(lines[i].trim())
      i++
    } else if (!lines[i].trim()) {
      let j = i
      while (j < lines.length && !lines[j].trim()) j++
      const next = ITEM.exec(lines[j] || '')
      if (!next || indent(next[1]) < base) break
      i = j
    } else {
      break
    }
  }
  for (const entry of list.items) entry.content = parseInline(entry.lines.join('\n'))
  return { node: list, next: i }
}

// Inline nodes: text, br, atom, code, link, strong, em, del. Code keeps atoms but no other markup.
export function parseInline(text, codeOnly = false) {
  const nodes = []
  const pushText = value => value.split('\n').forEach((piece, n) => {
    if (n) nodes.push({ type: 'br' })
    if (piece) nodes.push({ type: 'text', text: piece })
  })
  if (codeOnly) {
    text.split(new RegExp(`${OPEN}(\\d+)${CLOSE}`)).forEach((piece, n) => n % 2 ? nodes.push({ type: 'atom', index: Number(piece) }) : piece && nodes.push({ type: 'text', text: piece }))
    return nodes
  }
  let cursor = 0
  for (const m of text.matchAll(INLINE)) {
    if (m.index > cursor) pushText(text.slice(cursor, m.index))
    if (m[1] != null) nodes.push({ type: 'code', children: parseInline(m[1], true) })
    else if (m[2] != null) nodes.push({ type: 'atom', index: Number(m[2]) })
    else if (m[3] != null) nodes.push({ type: 'link', href: m[4], children: parseInline(m[3]) })
    else if (m[5] != null || m[6] != null) nodes.push({ type: 'strong', children: parseInline(m[5] ?? m[6]) })
    else if (m[7] != null) nodes.push({ type: 'del', children: parseInline(m[7]) })
    else nodes.push({ type: 'em', children: parseInline(m[8] ?? m[9]) })
    cursor = m.index + m[0].length
  }
  if (cursor < text.length) pushText(text.slice(cursor))
  return nodes
}

export function parseMarkdown(parts) {
  const { text, atoms } = toSource(parts)
  return { blocks: parseBlocks(text.replace(/\r\n?/g, '\n').split('\n')), atoms }
}
