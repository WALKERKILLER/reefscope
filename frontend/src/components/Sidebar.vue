<template>
  <aside class="w-full flex flex-col h-full z-10 bg-m3-surface/30 border-r border-m3-outline-variant/30 transition-colors duration-200">
    <template v-if="activePanel === 'files'">
      <div class="px-4 py-3 shrink-0 flex items-center justify-between border-b border-m3-outline-variant/30 relative">
        <span class="text-[11px] text-m3-on-surface-variant uppercase tracking-widest font-medium">资源管理器</span>
        <button
          type="button"
          class="text-[14px] text-m3-on-surface-variant uppercase tracking-wider font-medium cursor-pointer hover:text-m3-on-surface transition-colors px-1.5 rounded hover:bg-m3-surface-container"
          @click.stop="toggleWorkspaceMenu"
        >...</button>

        <div
          v-if="showWorkspaceMenu"
          class="absolute right-4 top-11 z-30 w-44 rounded-xl border border-m3-outline-variant/30 bg-m3-surface shadow-lg p-2"
        >
          <button
            type="button"
            class="w-full text-left px-3 py-2 rounded-lg text-[12px] text-m3-on-surface hover:bg-m3-surface-container transition-colors"
            @click="enableSelectionMode"
          >多选模式</button>
          <button
            type="button"
            class="w-full text-left px-3 py-2 rounded-lg text-[12px] text-m3-on-surface hover:bg-m3-surface-container transition-colors"
            @click="emit('file-batch-action', { action: 'clear-selection' })"
          >清空选择</button>
        </div>
      </div>

      <div v-if="selectionMode" class="px-4 py-3 border-b border-m3-outline-variant/20 bg-m3-surface/60">
        <div class="flex items-center justify-between gap-2 text-[11px] text-m3-on-surface-variant uppercase tracking-wider">
          <span>已选 {{ selectedCount }} 项</span>
          <button
            type="button"
            class="px-2 py-1 rounded-md text-m3-on-surface-variant hover:text-m3-on-surface hover:bg-m3-surface-container transition-colors"
            @click="emit('selection-mode-change', false)"
          >退出</button>
        </div>
        <div class="grid grid-cols-2 gap-2 mt-3">
          <button type="button" class="batch-btn" @click="emitBatch('rerun')">批量重做</button>
          <button type="button" class="batch-btn" @click="emitBatch('copy')">批量拷贝</button>
          <button type="button" class="batch-btn" @click="emitBatch('rename')">批量重命名</button>
          <button type="button" class="batch-btn danger" @click="emitBatch('delete')">批量删除</button>
        </div>
      </div>

      <div class="flex flex-col flex-1 min-h-0 py-2">
        <div
          class="flex items-center px-4 py-2 cursor-pointer transition-colors font-medium text-[11px] uppercase tracking-wider text-m3-on-surface hover:bg-m3-surface-container mx-2 rounded-md"
          @click="isExpanded = !isExpanded"
        >
          <i class="w-4 h-4 mr-2 text-m3-on-surface-variant">
            <svg v-if="isExpanded" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </i>
          工作区
        </div>

        <div v-if="isExpanded" class="flex flex-col flex-1 overflow-y-auto pb-4" @click="closeMenus">
          <div
            @click="$emit('file-select', configFile)"
            class="flex items-center py-1.5 px-3 cursor-pointer text-[12px] text-m3-on-surface-variant hover:bg-m3-surface-container transition-colors rounded-md mx-4 mb-2 gap-2.5"
          >
            <i class="w-4 h-4">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
                <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
                <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
                <path d="M10 9H8"/>
                <path d="M16 13H8"/>
                <path d="M16 17H8"/>
              </svg>
            </i>
            <span class="truncate flex-1">{{ configFile.name }}</span>
          </div>

          <div v-if="history.length === 0" class="text-m3-on-surface-variant text-[12px] py-4 px-4 text-center">未找到工作区文件。</div>

          <div
            v-for="(item, idx) in history"
            :key="item.id"
            class="relative flex items-center py-1.5 px-3 text-[12px] mx-4 gap-2.5 rounded-md transition-colors"
            :class="itemClasses(item, idx)"
            @click="handleItemClick(item)"
          >
            <input
              v-if="selectionMode"
              :checked="isSelected(item)"
              type="checkbox"
              class="h-3.5 w-3.5 shrink-0 accent-[color:var(--m3-primary)]"
              @click.stop="toggleSelection(item)"
            />

            <div class="relative flex items-center justify-center w-4 h-4 shrink-0">
              <i v-if="item.status === 'processed'" class="w-4 h-4" :class="idx === 0 ? 'text-m3-primary' : 'text-m3-on-surface-variant'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
                  <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
                  <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
                  <path d="m10 11 5 3-5 3v-6Z"/>
                </svg>
              </i>
              <i v-else-if="item.status === 'failed'" class="w-4 h-4 text-m3-error">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/>
                  <line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
              </i>
              <i v-else class="w-4 h-4 text-m3-warning">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 block">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
              </i>
            </div>

            <span class="truncate flex-1">{{ item.name }}</span>

            <span v-if="item.status === 'processing'" class="text-[9px] font-medium tracking-widest text-m3-warning opacity-90 uppercase bg-m3-warning/10 px-1.5 rounded">执行</span>

            <button
              v-if="!selectionMode"
              type="button"
              class="shrink-0 rounded-md p-1 text-m3-on-surface-variant hover:text-m3-on-surface hover:bg-m3-surface-container transition-colors"
              @click.stop="toggleItemMenu(item.id)"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 block">
                <circle cx="12" cy="5" r="1.8"/>
                <circle cx="12" cy="12" r="1.8"/>
                <circle cx="12" cy="19" r="1.8"/>
              </svg>
            </button>

            <div
              v-if="openItemMenuId === item.id"
              class="absolute right-2 top-9 z-30 w-40 rounded-xl border border-m3-outline-variant/30 bg-m3-surface shadow-lg p-2"
              @click.stop
            >
              <button type="button" class="item-menu-btn" @click="emitAction('rerun', item)">重做</button>
              <button type="button" class="item-menu-btn" @click="emitAction('copy', item)">拷贝</button>
              <button type="button" class="item-menu-btn" @click="emitAction('rename', item)">重命名</button>
              <button type="button" class="item-menu-btn danger" @click="emitAction('delete', item)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-if="activePanel === 'activity'">
      <div class="px-6 py-5 shrink-0 flex items-center justify-between border-b border-m3-outline-variant/30">
        <span class="text-[12px] text-m3-on-surface-variant uppercase tracking-widest font-bold">活动日志</span>
      </div>
      <div class="flex-1 p-6 text-sm text-m3-on-surface-variant">
        <i class="w-10 h-10 mb-4 text-m3-primary/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-10 h-10 block">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </i>
        <p>系统活动正常。</p>
      </div>
    </template>

    <template v-if="activePanel === 'box'">
      <div class="px-6 py-5 shrink-0 flex items-center justify-between border-b border-m3-outline-variant/30">
        <span class="text-[12px] text-m3-on-surface-variant uppercase tracking-widest font-bold">依赖包</span>
      </div>
      <div class="flex-1 p-6 text-sm text-m3-on-surface-variant">
        <i class="w-10 h-10 mb-4 text-m3-primary/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-10 h-10 block">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
            <line x1="12" y1="22.08" x2="12" y2="12"/>
          </svg>
        </i>
        <p>依赖包已是最新。</p>
      </div>
    </template>

    <template v-if="activePanel === 'terminal'">
      <div class="px-6 py-5 shrink-0 flex items-center justify-between border-b border-m3-outline-variant/30">
        <span class="text-[12px] text-m3-on-surface-variant uppercase tracking-widest font-bold">终端</span>
      </div>
      <div class="flex-1 p-6 text-sm text-m3-on-surface-variant font-mono">
        <i class="w-10 h-10 mb-4 text-m3-primary/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-10 h-10 block">
            <polyline points="4 17 10 11 4 5"/>
            <line x1="12" y1="19" x2="20" y2="19"/>
          </svg>
        </i>
        <p>$ root@ocean-node ~</p>
        <p>_</p>
      </div>
    </template>

    <template v-if="activePanel === 'settings'">
      <div class="px-6 py-5 shrink-0 flex items-center justify-between border-b border-m3-outline-variant/30">
        <span class="text-[12px] text-m3-on-surface-variant uppercase tracking-widest font-bold">设置</span>
      </div>
      <div class="flex-1 p-6 text-sm text-m3-on-surface-variant overflow-y-auto">
        <i class="w-10 h-10 mb-4 text-m3-primary/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-10 h-10 block">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </i>
        <p class="mb-5 leading-relaxed">设置鱼类标注管线参数</p>

        <div class="space-y-4">
          <label class="flex flex-col gap-1.5 text-[11px] uppercase tracking-widest text-m3-on-surface-variant">
            模型权重路径
            <input
              :value="settings.modelPath"
              type="text"
              placeholder="留空则使用 backend/models/model_best.pt"
              class="rounded-md border border-m3-outline-variant/40 bg-m3-bg px-3 py-2 text-[12px] normal-case tracking-normal text-m3-on-surface outline-none focus:border-m3-primary"
              @input="emit('update-settings', { modelPath: $event.target.value })"
            />
          </label>

          <label class="flex flex-col gap-1.5 text-[11px] uppercase tracking-widest text-m3-on-surface-variant">
            目标类别
            <input
              :value="settings.targetLabels"
              type="text"
              placeholder="fish"
              class="rounded-md border border-m3-outline-variant/40 bg-m3-bg px-3 py-2 text-[12px] normal-case tracking-normal text-m3-on-surface outline-none focus:border-m3-primary"
              @input="emit('update-settings', { targetLabels: $event.target.value })"
            />
          </label>

          <label class="flex flex-col gap-1.5 text-[11px] uppercase tracking-widest text-m3-on-surface-variant">
            置信度阈值
            <input
              :value="settings.confidenceThreshold"
              type="number"
              min="0"
              max="1"
              step="0.01"
              class="rounded-md border border-m3-outline-variant/40 bg-m3-bg px-3 py-2 text-[12px] normal-case tracking-normal text-m3-on-surface outline-none focus:border-m3-primary"
              @input="emit('update-settings', { confidenceThreshold: $event.target.value })"
            />
          </label>

          <label class="flex flex-col gap-1.5 text-[11px] uppercase tracking-widest text-m3-on-surface-variant">
            IoU 阈值
            <input
              :value="settings.iouThreshold"
              type="number"
              min="0"
              max="1"
              step="0.01"
              class="rounded-md border border-m3-outline-variant/40 bg-m3-bg px-3 py-2 text-[12px] normal-case tracking-normal text-m3-on-surface outline-none focus:border-m3-primary"
              @input="emit('update-settings', { iouThreshold: $event.target.value })"
            />
          </label>

          <label class="flex flex-col gap-1.5 text-[11px] uppercase tracking-widest text-m3-on-surface-variant">
            抽帧间隔
            <input
              :value="settings.frameStride"
              type="number"
              min="1"
              step="1"
              class="rounded-md border border-m3-outline-variant/40 bg-m3-bg px-3 py-2 text-[12px] normal-case tracking-normal text-m3-on-surface outline-none focus:border-m3-primary"
              @input="emit('update-settings', { frameStride: $event.target.value })"
            />
          </label>

          <label class="flex flex-col gap-1.5 text-[11px] uppercase tracking-widest text-m3-on-surface-variant">
            推理批大小
            <input
              :value="settings.batchSize"
              type="number"
              min="1"
              step="1"
              class="rounded-md border border-m3-outline-variant/40 bg-m3-bg px-3 py-2 text-[12px] normal-case tracking-normal text-m3-on-surface outline-none focus:border-m3-primary"
              @input="emit('update-settings', { batchSize: $event.target.value })"
            />
          </label>

          <label class="flex items-center justify-between gap-3 text-[11px] uppercase tracking-widest text-m3-on-surface-variant rounded-md border border-m3-outline-variant/30 bg-m3-bg px-3 py-3">
            <span>半精度推理</span>
            <input
              :checked="Boolean(settings.useHalf)"
              type="checkbox"
              class="h-4 w-4 accent-[color:var(--m3-primary)]"
              @change="emit('update-settings', { useHalf: $event.target.checked })"
            />
          </label>
        </div>
      </div>
    </template>
  </aside>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  history: {
    type: Array,
    default: () => []
  },
  activePanel: {
    type: String,
    default: 'files'
  },
  settings: {
    type: Object,
    default: () => ({
      modelPath: '',
      targetLabels: 'fish',
      confidenceThreshold: 0.25,
      iouThreshold: 0.45,
      frameStride: 5,
      batchSize: 8,
      useHalf: true
    })
  },
  configFile: {
    type: Object,
    default: () => ({
      id: 'config:pipeline_settings.toml',
      type: 'config',
      name: 'pipeline_settings.toml'
    })
  },
  selectionMode: {
    type: Boolean,
    default: false
  },
  selectedIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'file-select',
  'update-settings',
  'file-action',
  'file-batch-action',
  'toggle-select',
  'selection-mode-change'
])

const isExpanded = ref(true)
const openItemMenuId = ref(null)
const showWorkspaceMenu = ref(false)

const selectedCount = computed(() => props.selectedIds.length)

function itemClasses(item, idx) {
  return [
    props.selectionMode ? 'cursor-pointer hover:bg-m3-surface-container' : 'cursor-pointer',
    item.status === 'processed' ? 'text-m3-on-surface' : 'text-m3-on-surface-variant',
    idx === 0 && !props.selectionMode ? 'bg-m3-primary/10 text-m3-primary font-medium' : 'hover:bg-m3-surface-container',
    isSelected(item) ? 'ring-1 ring-m3-primary bg-m3-primary/10' : ''
  ]
}

function isSelected(item) {
  return props.selectedIds.includes(item.id)
}

function toggleItemMenu(itemId) {
  showWorkspaceMenu.value = false
  openItemMenuId.value = openItemMenuId.value === itemId ? null : itemId
}

function toggleWorkspaceMenu() {
  openItemMenuId.value = null
  showWorkspaceMenu.value = !showWorkspaceMenu.value
}

function closeMenus() {
  openItemMenuId.value = null
  showWorkspaceMenu.value = false
}

function handleOutsideClick() {
  closeMenus()
}

function handleItemClick(item) {
  if (props.selectionMode) {
    toggleSelection(item)
    return
  }
  emit('file-select', item)
}

function toggleSelection(item) {
  emit('toggle-select', item)
}

function emitAction(action, item) {
  closeMenus()
  emit('file-action', { action, item })
}

function emitBatch(action) {
  closeMenus()
  emit('file-batch-action', { action })
}

function enableSelectionMode() {
  closeMenus()
  emit('selection-mode-change', true)
}

onMounted(() => {
  window.addEventListener('click', handleOutsideClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handleOutsideClick)
})
</script>

<style scoped>
.item-menu-btn {
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-radius: 0.75rem;
  font-size: 12px;
  color: rgb(var(--m3-on-surface));
  transition: background-color 0.2s ease, color 0.2s ease;
}

.item-menu-btn:hover {
  background: rgb(var(--m3-surface-container));
}

.item-menu-btn.danger {
  color: rgb(var(--m3-error));
}

.batch-btn {
  padding: 0.5rem 0.75rem;
  border-radius: 0.75rem;
  font-size: 12px;
  color: rgb(var(--m3-on-surface));
  background: rgb(var(--m3-surface));
  border: 1px solid rgba(var(--m3-outline-variant), 0.3);
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.batch-btn:hover {
  background: rgb(var(--m3-surface-container));
  border-color: rgba(var(--m3-primary), 0.4);
}

.batch-btn.danger {
  color: rgb(var(--m3-error));
}
</style>
