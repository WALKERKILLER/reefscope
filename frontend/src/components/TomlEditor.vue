<template>
  <div ref="host" class="toml" />
</template>

<script setup>
import { autocompletion, completeFromList } from '@codemirror/autocomplete'
import { StreamLanguage } from '@codemirror/language'
import { toml as tomlParser } from '@codemirror/legacy-modes/mode/toml'
import { Compartment, EditorState } from '@codemirror/state'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView, keymap } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { isDark } from '../lib/theme'

const props = defineProps({ content: { type: String, default: '' } })
const emit = defineEmits(['update:content', 'save'])
const host = ref(null)
const theme = new Compartment()
let view = null
let internal = false

const completions = completeFromList([
  { label: '[pipeline]', type: 'keyword' },
  { label: 'model_path', type: 'property', apply: 'model_path = "models/model_best.pt"' },
  { label: 'target_labels', type: 'property', apply: 'target_labels = ["fish"]' },
  { label: 'confidence_threshold', type: 'property', apply: 'confidence_threshold = 0.25' },
  { label: 'iou_threshold', type: 'property', apply: 'iou_threshold = 0.45' },
  { label: 'frame_stride', type: 'property', apply: 'frame_stride = 5' },
  { label: 'batch_size', type: 'property', apply: 'batch_size = 8' },
  { label: 'use_half', type: 'property', apply: 'use_half = true' },
  { label: 'true', type: 'constant' },
  { label: 'false', type: 'constant' }
])

// Surfaces follow the app tokens; only the syntax palette switches with the theme.
const chrome = EditorView.theme({
  '&': { height: '100%', fontSize: '12px', backgroundColor: 'var(--surface)', color: 'var(--ink)' },
  '.cm-scroller': { fontFamily: 'var(--font-mono)', lineHeight: '1.75' },
  '.cm-content': { padding: '12px 0' },
  '.cm-line': { padding: '0 16px' },
  '.cm-gutters': { backgroundColor: 'var(--surface-2)', color: 'var(--ink-3)', border: 'none', boxShadow: 'inset -1px 0 0 var(--line)' },
  '.cm-activeLine, .cm-activeLineGutter': { backgroundColor: 'var(--accent-soft)' },
  '.cm-tooltip': { backgroundColor: 'var(--surface)', color: 'var(--ink)', border: 'none', boxShadow: 'var(--shadow-pop)', borderRadius: '6px' },
  '.cm-tooltip-autocomplete ul li[aria-selected]': { backgroundColor: 'var(--accent-soft)', color: 'var(--ink)' }
})
const palette = () => (isDark.value ? oneDark : [])

onMounted(() => {
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: props.content,
      extensions: [
        // Earlier extensions win: app chrome overrides oneDark's surfaces, keeping its syntax colors.
        chrome,
        basicSetup,
        theme.of(palette()),
        StreamLanguage.define(tomlParser),
        autocompletion({ override: [completions] }),
        keymap.of([{ key: 'Mod-s', run: () => { emit('save'); return true } }]),
        EditorView.updateListener.of(update => { if (update.docChanged && !internal) emit('update:content', update.state.doc.toString()) })
      ]
    })
  })
})

watch(isDark, () => view?.dispatch({ effects: theme.reconfigure(palette()) }))
watch(() => props.content, next => {
  if (!view) return
  const current = view.state.doc.toString()
  if (current === next) return
  internal = true
  view.dispatch({ changes: { from: 0, to: current.length, insert: next } })
  internal = false
})
defineExpose({ focus: () => view?.focus() })
onBeforeUnmount(() => { view?.destroy(); view = null })
</script>

<style scoped>
.toml { height: 100%; }
.toml :deep(.cm-editor) { height: 100%; }
.toml :deep(.cm-editor.cm-focused) { outline: none; }
</style>
