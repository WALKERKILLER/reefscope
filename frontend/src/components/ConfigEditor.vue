<template>
  <div class="editor">
    <header class="bar">
      <div class="title">
        <IconFileText class="title-icon" />
        <span class="name">{{ fileName }}</span>
        <span class="tag">旧检测管线</span>
      </div>
      <div class="actions">
        <span v-if="saveMessage" class="note" role="status">{{ saveMessage }}</span>
        <span class="note hint">保存 <span class="kbd">Ctrl S</span></span>
        <button class="btn btn-primary btn-sm" @click="$emit('save')">保存配置</button>
        <UiTooltip text="关闭配置"><button class="btn btn-ghost btn-sm btn-icon" aria-label="关闭配置" @click="$emit('close')"><IconX /></button></UiTooltip>
      </div>
    </header>
    <p class="note intro">这些参数只影响旧的 HTTP 检测接口。鱼类分析的模型与阈值在每次分析时单独设置。</p>
    <div class="code"><div ref="editorRef" class="code-host"></div></div>
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
import { IconFileText, IconX } from '@tabler/icons-vue'
import UiTooltip from './ui/UiTooltip.vue'

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
.editor { display: flex; flex-direction: column; height: 100%; min-height: 0; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); overflow: hidden; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; height: 40px; padding: 0 8px 0 12px; box-shadow: inset 0 -1px 0 var(--line); }
.title { display: flex; align-items: center; gap: 8px; min-width: 0; }
.title-icon { color: var(--ink-3); }
.name { font-weight: 500; font-family: var(--font-mono); font-size: var(--text-small); }
.actions { display: flex; align-items: center; gap: 8px; }
.intro { padding: 8px 12px; box-shadow: inset 0 -1px 0 var(--line); }
.code { position: relative; flex: 1; min-height: 0; background: #282c34; }
.code-host { position: absolute; inset: 0; }
:deep(.cm-editor) { height: 100%; }
@media (max-width: 700px) { .hint { display: none; } }
</style>
