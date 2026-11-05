<script>
import { computed, h } from 'vue'
import ReportSegments from './ReportSegments.vue'
import { parseMarkdown } from '../lib/markdown'

// Renders an agent answer's audited segments as Markdown. The tree is built with render functions,
// never v-html, so model text cannot inject markup; links open only http(s) URLs in a new tab.
export default {
  name: 'AgentMarkdown',
  props: { parts: { type: Array, default: () => [] }, metrics: { type: Object, default: () => ({}) }, seekTask: { type: Number, default: null } },
  emits: ['seek'],
  setup(props, { emit }) {
    const tree = computed(() => parseMarkdown(props.parts))
    // Models usually start at ### — levels count from the answer's shallowest heading so its top
    // sections never render smaller than body text.
    const top = computed(() => {
      const levels = [], walk = blocks => blocks.forEach(b => b.type === 'heading' ? levels.push(b.level) : b.type === 'quote' && walk(b.children))
      walk(tree.value.blocks)
      return levels.length ? Math.min(...levels) : 1
    })
    const atom = index => h(ReportSegments, { parts: [tree.value.atoms[index]], metrics: props.metrics, seekTask: props.seekTask, onSeek: seconds => emit('seek', seconds) })
    const inline = nodes => nodes.map(node => {
      switch (node.type) {
        case 'text': return node.text
        case 'br': return h('br')
        case 'atom': return atom(node.index)
        case 'code': return h('code', inline(node.children))
        case 'link': return h('a', { class: 'ui-link', href: node.href, target: '_blank', rel: 'noopener noreferrer' }, inline(node.children))
        case 'strong': return h('strong', inline(node.children))
        case 'em': return h('em', inline(node.children))
        default: return h('del', inline(node.children))
      }
    })
    const list = node => h(node.ordered ? 'ol' : 'ul', node.ordered && node.start !== 1 ? { start: node.start } : null,
      node.items.map(item => h('li', [...inline(item.content), ...item.children.map(list)])))
    // Answer headings sit below the page's own h2/h3, so depths map to h4–h6.
    const block = node => {
      switch (node.type) {
        case 'heading': return h(`h${Math.min(node.level - top.value + 4, 6)}`, { class: 'md-h' }, inline(node.children))
        case 'paragraph': return h('p', inline(node.children))
        case 'list': return list(node)
        case 'quote': return h('blockquote', node.children.map(block))
        case 'code': return h('pre', h('code', inline(node.children)))
        case 'rule': return h('hr')
        default: return h('div', { class: 'md-table' }, h('table', { class: 'ui-table' }, [
          h('thead', h('tr', node.head.map((cell, n) => h('th', { style: { textAlign: node.align[n] } }, inline(cell))))),
          h('tbody', node.rows.map(row => h('tr', node.head.map((_, n) => h('td', { style: { textAlign: node.align[n] } }, inline(row[n] || []))))))
        ]))
      }
    }
    return () => h('div', { class: 'md' }, tree.value.blocks.map(block))
  }
}
</script>

<style scoped>
.md { display: flex; flex-direction: column; gap: 8px; min-width: 0; overflow-wrap: anywhere; }
.md p { margin: 0; }
.md-h { margin: 6px 0 -2px; font-size: var(--text-title); font-weight: 600; line-height: 1.4; color: var(--ink); text-wrap: balance; }
h5.md-h { color: var(--ink-2); }
h6.md-h { font-size: var(--text-body); color: var(--ink-2); }
.md :first-child.md-h { margin-top: 0; }
.md ul, .md ol { display: flex; flex-direction: column; gap: 3px; margin: 0; padding-inline-start: 1.4em; }
.md li > ul, .md li > ol { margin-top: 3px; }
.md li::marker { color: var(--ink-3); font-variant-numeric: tabular-nums; }
.md strong { font-weight: 600; color: var(--ink); }
.md del { color: var(--ink-3); }
.md code { padding: 1px 4px; border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 0.9em; background: var(--surface-3); }
.md pre { margin: 0; padding: 8px 10px; border-radius: var(--radius); overflow-x: auto; font-size: var(--text-small); line-height: 1.55; background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); }
.md pre code { padding: 0; font-size: 1em; white-space: pre; background: none; }
.md blockquote { margin: 0; padding-inline-start: 10px; border-inline-start: 2px solid var(--line-strong); color: var(--ink-2); }
.md hr { width: 100%; margin: 2px 0; border: 0; border-top: 1px solid var(--line); }
.md a { white-space: normal; }
.md-table { max-width: 100%; overflow-x: auto; border-radius: var(--radius); box-shadow: 0 0 0 1px var(--line); }
.md-table table { width: 100%; font-size: var(--text-small); }
.md-table th { white-space: nowrap; }
.md-table td { overflow-wrap: normal; }
</style>
