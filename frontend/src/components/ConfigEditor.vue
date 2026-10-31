<template>
  <div class="editor" @keydown="onKeydown">
    <header class="bar">
      <div class="title">
        <IconAdjustmentsHorizontal class="title-icon" />
        <span class="name" :title="fileName">{{ fileName }}</span>
        <span class="tag">旧检测管线</span>
      </div>
      <div class="actions">
        <span v-if="saveMessage" class="note" role="status">{{ saveMessage }}</span>
        <span v-else-if="dirty" class="unsaved note"><span class="dot" />未保存</span>
        <UiSegmented :model-value="mode" :options="modeOptions" aria-label="编辑方式" @update:model-value="switchMode" />
        <button v-if="dirty" class="btn btn-ghost btn-sm" @click="revert">撤销修改</button>
        <UiTooltip text="保存配置" shortcut="Ctrl S">
          <button class="btn btn-primary btn-sm" :disabled="!canSave" @click="save">{{ saving ? '正在保存…' : '保存' }}</button>
        </UiTooltip>
        <UiTooltip text="关闭配置"><button class="btn btn-ghost btn-sm btn-icon" aria-label="关闭配置" @click="$emit('close')"><IconX /></button></UiTooltip>
      </div>
    </header>

    <div v-show="mode === 'form'" class="form-scroll">
      <form v-if="draft" class="form" novalidate @submit.prevent="save">
        <p class="note intro"><IconInfoCircle />旧检测接口的预设参数。工作台已改用鱼类分析，这里的修改不影响新的分析；鱼类分析的模型与阈值在每次创建分析时设置。</p>

        <section class="group" aria-labelledby="g-model">
          <h3 id="g-model">模型</h3>
          <div class="row">
            <div class="label"><label for="cfg-model">权重路径</label><p id="cfg-model-help" class="note">相对路径从 backend 目录解析，也可填写绝对路径。</p></div>
            <div class="control">
              <input id="cfg-model" v-model.trim="draft.modelPath" class="input mono" spellcheck="false" placeholder="models/model_best.pt" :aria-invalid="!!errors.modelPath" aria-describedby="cfg-model-help cfg-model-error" />
              <p v-if="errors.modelPath" id="cfg-model-error" class="error">{{ errors.modelPath }}</p>
            </div>
          </div>
          <div class="row">
            <div class="label"><label for="cfg-labels">目标类别</label><p id="cfg-labels-help" class="note">只保留这些类别的框。名称须与模型类别一致，不区分大小写。</p></div>
            <div class="control">
              <div class="chips input" :class="{ invalid: errors.labels }" @click="labelInput?.focus()">
                <span v-for="(label, i) in draft.labels" :key="label" class="chip">{{ label }}<button type="button" :aria-label="`移除 ${label}`" @click.stop="draft.labels.splice(i, 1)"><IconX /></button></span>
                <input id="cfg-labels" ref="labelInput" v-model="labelText" class="chip-input" spellcheck="false" :placeholder="draft.labels.length ? '' : '输入类别后按回车'" :aria-invalid="!!errors.labels" aria-describedby="cfg-labels-help cfg-labels-error" @keydown="onLabelKey" @blur="commitLabel" />
              </div>
              <p v-if="errors.labels" id="cfg-labels-error" class="error">{{ errors.labels }}</p>
            </div>
          </div>
        </section>

        <section class="group" aria-labelledby="g-threshold">
          <h3 id="g-threshold">阈值</h3>
          <div v-for="field in thresholds" :key="field.key" class="row">
            <div class="label"><label :for="`cfg-${field.key}`">{{ field.label }}</label><p :id="`cfg-${field.key}-help`" class="note">{{ field.help }}</p></div>
            <div class="control">
              <div class="slider-row">
                <UiSlider v-model="draft[field.key]" :min="0" :max="1" :step="0.01" :aria-label="field.label" />
                <input :id="`cfg-${field.key}`" v-model.number="draft[field.key]" class="input tnum num" type="number" min="0" max="1" step="0.01" :aria-invalid="!!errors[field.key]" :aria-describedby="`cfg-${field.key}-help cfg-${field.key}-error`" />
              </div>
              <p v-if="errors[field.key]" :id="`cfg-${field.key}-error`" class="error">{{ errors[field.key] }}</p>
            </div>
          </div>
        </section>

        <section class="group" aria-labelledby="g-throughput">
          <h3 id="g-throughput">吞吐</h3>
          <div v-for="field in integers" :key="field.key" class="row">
            <div class="label"><label :for="`cfg-${field.key}`">{{ field.label }}</label><p :id="`cfg-${field.key}-help`" class="note">{{ field.help }}</p></div>
            <div class="control">
              <div class="stepper">
                <button type="button" class="btn btn-sm btn-icon" :aria-label="`${field.label}减 1`" :disabled="!(draft[field.key] > 1)" @click="draft[field.key] = Math.max(1, (Number(draft[field.key]) || 1) - 1)"><IconMinus /></button>
                <input :id="`cfg-${field.key}`" v-model.number="draft[field.key]" class="input tnum num" type="number" min="1" step="1" :aria-invalid="!!errors[field.key]" :aria-describedby="`cfg-${field.key}-help cfg-${field.key}-error`" />
                <button type="button" class="btn btn-sm btn-icon" :aria-label="`${field.label}加 1`" @click="draft[field.key] = (Number(draft[field.key]) || 0) + 1"><IconPlus /></button>
                <span class="unit note">{{ field.unit }}</span>
              </div>
              <p v-if="errors[field.key]" :id="`cfg-${field.key}-error`" class="error">{{ errors[field.key] }}</p>
            </div>
          </div>
          <div class="row">
            <div class="label"><label for="cfg-half">半精度推理</label><p class="note">使用 FP16，仅在 CUDA 上生效；CPU 运行时自动关闭。</p></div>
            <div class="control switch-row"><UiSwitch id="cfg-half" v-model="draft.useHalf" /><span class="note">{{ draft.useHalf ? '开启' : '关闭' }}</span></div>
          </div>
        </section>

        <p class="note foot">通过表单保存时，文件按标准格式重写，注释和未知字段不会保留。需要保留时请切换到 TOML 编辑。</p>
      </form>
      <p v-else class="note intro">正在读取配置…</p>
    </div>

    <div v-if="tomlOpened" v-show="mode === 'toml'" class="code">
      <TomlEditor ref="toml" :content="content" @update:content="$emit('update:content', $event)" @save="save" />
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, nextTick, ref, watch } from 'vue'
import { IconAdjustmentsHorizontal, IconInfoCircle, IconMinus, IconPlus, IconX } from '@tabler/icons-vue'
import { confirmDialog } from '../lib/dialogs'
import UiSegmented from './ui/UiSegmented.vue'
import UiSlider from './ui/UiSlider.vue'
import UiSwitch from './ui/UiSwitch.vue'
import UiTooltip from './ui/UiTooltip.vue'

// CodeMirror stays out of the form view; it loads the first time the TOML view opens.
const TomlEditor = defineAsyncComponent(() => import('./TomlEditor.vue'))

const props = defineProps({
  fileName: { type: String, default: 'pipeline_settings.toml' },
  content: { type: String, default: '' },
  savedContent: { type: String, default: '' },
  settings: { type: Object, default: null },
  saveMessage: { type: String, default: '' },
  saveContent: { type: Function, required: true },
  saveSettings: { type: Function, required: true }
})
const emit = defineEmits(['update:content', 'close'])

const MODE_KEY = 'reefscope-config-mode'
const modeOptions = [{ value: 'form', label: '表单' }, { value: 'toml', label: 'TOML' }]
const mode = ref(localStorage.getItem(MODE_KEY) === 'toml' ? 'toml' : 'form')
const tomlOpened = ref(mode.value === 'toml')
const toml = ref(null)
const draft = ref(null)
const labelText = ref('')
const labelInput = ref(null)
const saving = ref(false)

const thresholds = [
  { key: 'confidenceThreshold', label: '置信度阈值', help: '低于此分数的框会被丢弃。' },
  { key: 'iouThreshold', label: 'IoU 阈值', help: '非极大值抑制的重叠阈值；越低，重叠的框去除得越多。' }
]
const integers = [
  { key: 'frameStride', label: '抽帧间隔', unit: '帧', help: '每隔 N 帧检测一次。数值越大处理越快，框的时间间隔也越大。' },
  { key: 'batchSize', label: '批大小', unit: '帧 / 批', help: '每次送入模型的帧数；显存不足时调小。' }
]

const fromSettings = s => ({
  modelPath: s.modelPath,
  labels: String(s.targetLabels || '').split(',').map(x => x.trim()).filter(Boolean),
  confidenceThreshold: s.confidenceThreshold,
  iouThreshold: s.iouThreshold,
  frameStride: s.frameStride,
  batchSize: s.batchSize,
  useHalf: !!s.useHalf
})
const toSettings = d => ({
  modelPath: d.modelPath,
  targetLabels: d.labels.join(', '),
  confidenceThreshold: d.confidenceThreshold,
  iouThreshold: d.iouThreshold,
  frameStride: d.frameStride,
  batchSize: d.batchSize,
  useHalf: d.useHalf
})
watch(() => props.settings, s => { draft.value = s ? fromSettings(s) : null }, { immediate: true })

const probability = v => typeof v === 'number' && v >= 0 && v <= 1 ? '' : '填写 0 到 1 之间的数。'
const positiveInt = v => Number.isInteger(v) && v >= 1 ? '' : '填写不小于 1 的整数。'
const errors = computed(() => {
  const d = draft.value
  if (!d) return {}
  const result = {
    modelPath: d.modelPath ? '' : '填写权重文件路径，例如 models/model_best.pt。',
    labels: d.labels.length ? '' : '至少保留一个类别。',
    confidenceThreshold: probability(d.confidenceThreshold),
    iouThreshold: probability(d.iouThreshold),
    frameStride: positiveInt(d.frameStride),
    batchSize: positiveInt(d.batchSize)
  }
  return Object.fromEntries(Object.entries(result).filter(([, v]) => v))
})
const formDirty = computed(() => !!draft.value && !!props.settings && JSON.stringify(toSettings(draft.value)) !== JSON.stringify(toSettings(fromSettings(props.settings))))
const tomlDirty = computed(() => props.content !== props.savedContent)
const dirty = computed(() => (mode.value === 'form' ? formDirty.value || !!labelText.value.trim() : tomlDirty.value))
const canSave = computed(() => !saving.value && (mode.value === 'form' ? formDirty.value && !Object.keys(errors.value).length : true))

function commitLabel() {
  const parts = labelText.value.split(/[,，]/).map(x => x.trim()).filter(Boolean)
  for (const part of parts) if (!draft.value.labels.some(l => l.toLowerCase() === part.toLowerCase())) draft.value.labels.push(part)
  labelText.value = ''
}
function onLabelKey(event) {
  if (event.isComposing) return
  if (event.key === 'Enter' || event.key === ',' || event.key === '，') { event.preventDefault(); commitLabel() }
  else if (event.key === 'Backspace' && !labelText.value && draft.value.labels.length) draft.value.labels.pop()
}

async function save() {
  if (mode.value === 'form') commitLabel()
  if (!canSave.value) return false
  saving.value = true
  try {
    return mode.value === 'form' ? await props.saveSettings(toSettings(draft.value)) : await props.saveContent()
  } finally {
    saving.value = false
  }
}
function revert() {
  labelText.value = ''
  if (mode.value === 'form') draft.value = props.settings ? fromSettings(props.settings) : null
  else emit('update:content', props.savedContent)
}

async function switchMode(next) {
  if (next === mode.value) return
  if (dirty.value) {
    const ok = await confirmDialog({ title: '切换前保存修改？', description: '表单和 TOML 读取同一份已保存的配置，未保存的修改不会带到另一种视图。', confirmLabel: '保存并切换', cancelLabel: '继续编辑' })
    if (!ok || !(await save())) return
  }
  mode.value = next
  localStorage.setItem(MODE_KEY, next)
  if (next === 'toml') { tomlOpened.value = true; await nextTick(); toml.value?.focus?.() }
}

function onKeydown(event) {
  if (mode.value !== 'form' || !(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 's') return
  event.preventDefault()
  save()
}
</script>

<style scoped>
.editor { display: flex; flex-direction: column; height: 100%; min-height: 0; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); overflow: hidden; container-type: inline-size; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; height: 44px; flex: none; padding: 0 8px 0 12px; box-shadow: inset 0 -1px 0 var(--line); white-space: nowrap; }
.title { display: flex; align-items: center; gap: 8px; min-width: 0; }
.title-icon { flex: none; color: var(--ink-3); }
.name { min-width: 0; overflow: hidden; text-overflow: ellipsis; font-weight: 500; font-family: var(--font-mono); font-size: var(--text-small); }
.title .tag { flex: none; }
.actions { display: flex; align-items: center; gap: 8px; flex: none; }
.unsaved { display: inline-flex; align-items: center; gap: 6px; }
.unsaved .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--warn); }
.form-scroll { flex: 1; min-height: 0; overflow-y: auto; }
.form { display: flex; flex-direction: column; gap: 28px; max-width: 760px; padding: 16px 20px 24px; }
.intro { display: flex; gap: 8px; align-items: flex-start; padding: 8px 10px; border-radius: var(--radius); background: var(--surface-2); }
.intro .tabler-icon { flex: none; --icon-size: 14px; margin-top: 2px; }
.group { display: flex; flex-direction: column; gap: 18px; }
h3 { font-size: var(--text-small); font-weight: 600; color: var(--ink-2); }
.row { display: grid; grid-template-columns: minmax(0, 240px) minmax(0, 1fr); gap: 8px 32px; align-items: start; }
.label label { font-size: var(--text-body); font-weight: 500; color: var(--ink); }
.label .note { margin-top: 2px; font-size: var(--text-caption); }
.control { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.num { width: 76px; text-align: end; }
.slider-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 14px; align-items: center; }
.stepper { display: flex; align-items: center; gap: 6px; }
.unit { margin-inline-start: 4px; }
.switch-row { flex-direction: row; align-items: center; gap: 10px; min-height: 30px; }
.error { font-size: var(--text-caption); color: var(--danger); }
.input[aria-invalid=true], .chips.invalid { box-shadow: inset 0 0 0 1px var(--danger); }
.chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; height: auto; min-height: 30px; padding: 4px 6px; cursor: text; }
.chips:focus-within { box-shadow: inset 0 0 0 1px var(--accent), 0 0 0 3px var(--accent-soft); }
.chip { display: inline-flex; align-items: center; gap: 2px; height: 22px; padding: 0 2px 0 8px; border-radius: var(--radius-sm); font-size: var(--text-small); color: var(--ink); background: var(--surface-3); }
.chip button { display: inline-flex; padding: 3px; border: 0; border-radius: 3px; background: none; color: var(--ink-3); cursor: pointer; }
.chip button:hover { color: var(--ink); background: var(--line); }
.chip .tabler-icon { --icon-size: 12px; }
.chip-input { flex: 1; min-width: 8em; height: 22px; border: 0; outline: none; background: none; font: inherit; color: var(--ink); }
.foot { font-size: var(--text-caption); }
.code { position: relative; flex: 1; min-height: 0; }
.code > * { position: absolute; inset: 0; }
@container (max-width: 620px) {
  .row { grid-template-columns: 1fr; }
  .title .tag { display: none; }
}
@container (max-width: 470px) {
  .name { display: none; }
}
</style>
