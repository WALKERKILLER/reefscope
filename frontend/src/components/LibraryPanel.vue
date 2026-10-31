<template>
  <aside class="library" aria-label="视频库" @dragover.prevent="dragging = true" @dragleave.self="dragging = false" @drop.prevent="onDrop" :class="{ dragging }">
    <header class="head">
      <h2>视频库 <span class="count tnum">{{ history.length }}</span></h2>
      <div class="tools">
        <UiTooltip :text="selectionMode ? '退出多选' : '多选'">
          <button class="btn btn-ghost btn-sm btn-icon" :class="{ 'is-on': selectionMode }" :aria-pressed="selectionMode" aria-label="多选" @click="emit('selection-mode-change', !selectionMode)"><IconChecks /></button>
        </UiTooltip>
        <UiTooltip text="上传 MP4">
          <button class="btn btn-sm btn-icon" aria-label="上传 MP4" @click="fileInput?.click()"><IconUpload /></button>
        </UiTooltip>
        <input ref="fileInput" type="file" accept="video/mp4" class="sr-only" tabindex="-1" @change="onPick" />
      </div>
    </header>

    <div class="search">
      <IconSearch class="search-icon" />
      <input v-model="query" class="input" type="search" placeholder="按文件名筛选" aria-label="按文件名筛选视频" />
    </div>

    <ul class="list" role="list">
      <li v-for="item in filtered" :key="item.id" class="item" :class="{ active: String(item.taskId) === String(currentId), selected: isSelected(item) }">
        <input v-if="selectionMode" type="checkbox" class="check" :checked="isSelected(item)" @change="emit('toggle-select', item)" :aria-label="`选择 ${item.name}`" />
        <button class="open" @click="selectionMode ? emit('toggle-select', item) : emit('file-select', item)" :title="item.name">
          <IconMovie class="item-icon" />
          <span class="text">
            <span class="name">{{ item.name }}</span>
            <span class="meta tnum">#{{ item.taskId || item.id }}<template v-if="statusText(item)"> · {{ statusText(item) }}</template></span>
          </span>
        </button>
        <UiMenu v-if="!selectionMode" :items="menuItems" @select="entry => emit('file-action', { action: entry.key, item })">
          <button class="btn btn-ghost btn-sm btn-icon more" :aria-label="`${item.name} 的操作`"><IconDotsVertical /></button>
        </UiMenu>
      </li>
    </ul>
    <div v-if="!history.length" class="empty">
      <p class="empty-title">还没有视频</p>
      <p class="note">上传 MP4 后，视频与每次分析会保存在本地后端。也可以把文件拖到这里。</p>
      <button class="btn btn-sm" @click="fileInput?.click()"><IconUpload />上传 MP4</button>
    </div>
    <p v-else-if="!filtered.length" class="note empty-filter">没有名称包含“{{ query }}”的视频。<button class="link" @click="query = ''">清除筛选</button></p>

    <div v-if="selectionMode" class="batch">
      <span class="tnum">已选 {{ selectedIds.length }} 个</span>
      <div class="batch-actions">
        <button class="btn btn-sm" :disabled="!selectedIds.length" @click="emit('file-batch-action', { action: 'rerun' })">重新分析</button>
        <button class="btn btn-sm" :disabled="!selectedIds.length" @click="emit('file-batch-action', { action: 'copy' })">复制</button>
        <button class="btn btn-sm btn-danger" :disabled="!selectedIds.length" @click="emit('file-batch-action', { action: 'delete' })">删除</button>
      </div>
    </div>

    <footer class="foot">
      <button class="config" :class="{ active: configActive }" :aria-current="configActive ? 'true' : undefined" :title="configFile.path" @click="emit('file-select', configFile)">
        <IconAdjustmentsHorizontal class="config-icon" /><span class="config-label">旧检测管线配置</span><span class="config-ext">TOML</span><IconChevronRight class="config-chevron" />
      </button>
    </footer>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { IconUpload, IconChecks, IconSearch, IconMovie, IconDotsVertical, IconAdjustmentsHorizontal, IconChevronRight, IconRefresh, IconCopy, IconPencil, IconTrash } from '@tabler/icons-vue'
import UiMenu from './ui/UiMenu.vue'
import UiTooltip from './ui/UiTooltip.vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  currentId: { type: [Number, String], default: null },
  configFile: { type: Object, required: true },
  configActive: Boolean,
  selectionMode: Boolean,
  selectedIds: { type: Array, default: () => [] }
})
const emit = defineEmits(['file-select', 'file-action', 'file-batch-action', 'toggle-select', 'selection-mode-change', 'file-drop'])
const query = ref('')
const dragging = ref(false)
const fileInput = ref(null)
const menuItems = [
  { key: 'rerun', label: '重新分析', icon: IconRefresh },
  { key: 'copy', label: '复制', icon: IconCopy },
  { key: 'rename', label: '重命名', icon: IconPencil },
  { separator: true, key: 'sep' },
  { key: 'delete', label: '删除', icon: IconTrash, danger: true }
]
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? props.history.filter(item => item.name.toLowerCase().includes(q)) : props.history
})
function isSelected(item) { return props.selectedIds.includes(String(item.id)) }
function statusText(item) {
  if (item.status === 'processing') return '旧检测处理中'
  if (item.status === 'failed') return '旧检测失败，可重新分析'
  return ''
}
function onPick(event) {
  const file = event.target.files?.[0]
  if (file) emit('file-drop', file)
  event.target.value = ''
}
function onDrop(event) {
  dragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) emit('file-drop', file)
}
</script>

<style scoped>
.library { display: flex; flex-direction: column; height: 100%; min-height: 0; background: var(--surface); transition: box-shadow 150ms var(--ease); }
.library.dragging { box-shadow: inset 0 0 0 1.5px var(--accent); }
.head { display: flex; align-items: center; justify-content: space-between; padding: 12px 12px 8px 16px; }
h2 { font-size: var(--text-title); font-weight: 600; }
.count { margin-inline-start: 4px; font-size: var(--text-small); font-weight: 400; color: var(--ink-3); }
.tools { display: flex; gap: 4px; }
.is-on { color: var(--accent); background: var(--accent-soft); }
.search { position: relative; margin: 0 12px 8px; }
.search-icon { position: absolute; inset-inline-start: 9px; top: 8px; --icon-size: 14px; color: var(--ink-3); pointer-events: none; }
.search .input { padding-inline-start: 28px; }
.list { flex: 1; min-height: 0; overflow-y: auto; padding: 0 8px 8px; }
.item { position: relative; display: flex; align-items: center; gap: 4px; border-radius: var(--radius); transition: background-color 120ms var(--ease); }
.item:hover { background: var(--surface-2); }
.item.active { background: var(--accent-soft); }
.item.active::before { content: ""; position: absolute; inset-inline-start: 0; top: 8px; bottom: 8px; width: 2px; border-radius: 1px; background: var(--accent); }
.item.selected { background: var(--surface-3); }
.check { margin-inline-start: 8px; accent-color: var(--accent); }
.open { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; padding: 7px 4px 7px 10px; border: 0; background: none; font: inherit; text-align: start; color: var(--ink); cursor: pointer; border-radius: var(--radius); }
.item-icon { color: var(--ink-3); }
.item.active .item-icon { color: var(--accent); }
.text { display: flex; flex-direction: column; min-width: 0; }
.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta { font-size: var(--text-caption); color: var(--ink-3); }
.more { opacity: 0; margin-inline-end: 4px; }
.item:hover .more, .item.active .more, .more:focus-visible, .more[data-state=open] { opacity: 1; }
.empty { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 8px 16px; }
.empty-title { font-weight: 500; }
.empty .btn { margin-top: 6px; }
.empty-filter { padding: 8px 16px; }
.link { border: 0; background: none; font: inherit; color: var(--accent); cursor: pointer; padding: 0; }
.batch { display: flex; flex-direction: column; gap: 8px; margin: 0 8px 8px; padding: 10px; border-radius: var(--radius-lg); background: var(--surface-2); box-shadow: inset 0 0 0 1px var(--line); font-size: var(--text-small); }
.batch-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.foot { padding: 6px 8px 8px; box-shadow: inset 0 1px 0 var(--line); }
.config { display: flex; align-items: center; gap: 8px; width: 100%; height: 32px; padding: 0 8px; border: 0; border-radius: var(--radius); background: none; font: inherit; font-size: var(--text-small); color: var(--ink-2); cursor: pointer; text-align: start; white-space: nowrap; transition: background-color 120ms var(--ease), color 120ms var(--ease); }
.config:hover { background: var(--surface-2); color: var(--ink); }
.config.active { background: var(--accent-soft); color: var(--ink); }
.config-icon { flex: none; color: var(--ink-3); }
.config.active .config-icon { color: var(--accent); }
.config-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.config-ext { flex: none; font-family: var(--font-mono); font-size: var(--text-caption); color: var(--ink-3); }
.config-chevron { flex: none; --icon-size: 14px; color: var(--ink-3); }
</style>
