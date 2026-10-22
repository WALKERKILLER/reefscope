<template>
  <div class="flex flex-col h-full bg-m3-surface/30 border border-m3-outline-variant/30 rounded-lg overflow-hidden relative">
    <div class="flex items-center bg-transparent h-10 shrink-0 relative border-b border-m3-outline-variant/30 px-3 overflow-hidden">
      <div class="flex items-center px-4 h-full border-b-2 border-m3-primary text-m3-primary cursor-pointer relative z-10 box-border group">
        <span class="text-[11px] font-medium mr-2 text-m3-on-surface-variant bg-m3-surface-container py-0.5 px-1.5 rounded border border-m3-outline-variant/30 uppercase tracking-wider">配置</span>
        <span class="font-medium text-[12px] text-m3-on-surface mr-3">{{ fileName }}</span>
        <button
          @click="$emit('close')"
          class="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-m3-primary/20 text-m3-primary transition-all"
        >
          <i class="w-3.5 h-3.5">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5 block">
              <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
            </svg>
          </i>
        </button>
      </div>

      <div class="absolute right-3 top-0 bottom-0 flex items-center gap-2 z-20">
        <span v-if="saveMessage" class="text-[11px] text-m3-on-surface-variant">{{ saveMessage }}</span>
        <button
          @click="$emit('save')"
          class="px-3 py-1.5 text-[12px] rounded-md cursor-pointer bg-m3-primary text-m3-on-primary hover:bg-m3-primary/90 transition-colors font-medium"
        >保存</button>
      </div>
    </div>

    <div class="relative flex-1 min-h-0 bg-[#0f172a]">
      <div ref="editorRef" class="absolute inset-0"></div>
      <div class="pointer-events-none absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-[#0f172a] to-transparent"></div>
    </div>
  </div>
</template>

<script setup>
import { autocompletion, completeFromList } from '@codemirror/autocomplete'
import { StreamLanguage } from '@codemirror/language'
import { toml as tomlParser } from '@codemirror/legacy-modes/mode/toml'
import { EditorState } from '@codemirror/state'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView, keymap, lineNumbers } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  fileName: {
    type: String,
    default: 'pipeline_settings.toml'
  },
  content: {
    type: String,
    default: ''
  },
  saveMessage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:content', 'save', 'close'])
const editorRef = ref(null)

let editorView = null
let isInternalUpdate = false

const tomlCompletions = completeFromList([
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

function createEditor() {
  if (!editorRef.value) return

  const updateListener = EditorView.updateListener.of((update) => {
    if (!update.docChanged || isInternalUpdate) return
    emit('update:content', update.state.doc.toString())
  })

  editorView = new EditorView({
    state: EditorState.create({
      doc: props.content,
      extensions: [
        basicSetup,
        lineNumbers(),
        oneDark,
        StreamLanguage.define(tomlParser),
        autocompletion({ override: [tomlCompletions] }),
        keymap.of([
          {
            key: 'Mod-s',
            run: () => {
              emit('save')
              return true
            }
          }
        ]),
        updateListener,
        EditorView.theme({
          '&': {
            height: '100%',
            fontSize: '12px'
          },
          '.cm-scroller': {
            fontFamily: 'var(--font-mono)',
            lineHeight: '1.75'
          },
          '.cm-content': {
            padding: '16px 0'
          },
          '.cm-line': {
            padding: '0 16px'
          },
          '.cm-gutters': {
            borderRight: '1px solid rgba(255,255,255,0.08)'
          },
          '.cm-tooltip-autocomplete': {
            backgroundColor: '#111827',
            color: '#e5e7eb',
            border: '1px solid rgba(148, 163, 184, 0.35)'
          },
          '.cm-tooltip-autocomplete ul li[aria-selected]': {
            backgroundColor: 'rgba(56, 189, 248, 0.2)',
            color: '#f8fafc'
          }
        })
      ]
    }),
    parent: editorRef.value
  })
}

watch(() => props.content, (nextValue) => {
  if (!editorView) return
  const currentValue = editorView.state.doc.toString()
  if (currentValue === nextValue) return
  isInternalUpdate = true
  editorView.dispatch({
    changes: {
      from: 0,
      to: currentValue.length,
      insert: nextValue
    }
  })
  isInternalUpdate = false
})

onMounted(() => {
  createEditor()
})

onBeforeUnmount(() => {
  editorView?.destroy()
  editorView = null
})
</script>

<style scoped>
:deep(.cm-editor) {
  height: 100%;
}
</style>
