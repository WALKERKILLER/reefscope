<template>
  <div class="records">
    <header class="page-head">
      <h1>记录</h1>
      <p class="note">{{ intro }}</p>
    </header>
    <UiTabs v-model="tab" :items="tabs" aria-label="记录分类" class="tabs">
      <template #videos>
        <section class="panel" aria-label="视频">
          <div v-if="!history.length" class="empty">
            <p class="empty-title">还没有视频</p>
            <p class="note">在工作台上传 MP4 后，视频会出现在这里。</p>
          </div>
          <table v-else class="table">
            <thead><tr><th>视频</th><th class="num">编号</th><th>状态</th><th><span class="sr-only">操作</span></th></tr></thead>
            <tbody>
              <tr v-for="item in history" :key="item.id">
                <td class="name"><IconMovie /><span :title="item.name">{{ item.name }}</span></td>
                <td class="num tnum">{{ item.taskId || item.id }}</td>
                <td><span class="tag" :class="statusClass(item)">{{ statusText(item) }}</span></td>
                <td class="action"><button class="btn btn-sm" @click="emit('play-record', item)">打开<IconArrowRight /></button></td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>
      <template #models>
        <ModelResearch v-if="modelsOpened" />
      </template>
    </UiTabs>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { IconMovie, IconArrowRight } from '@tabler/icons-vue'
import UiTabs from './ui/UiTabs.vue'

const ModelResearch = defineAsyncComponent(() => import('./ModelResearch.vue'))
const props = defineProps({ history: { type: Array, default: () => [] } })
const emit = defineEmits(['play-record'])
const tab = ref('videos')
const tabs = computed(() => [{ value: 'videos', label: '视频', badge: props.history.length }, { value: 'models', label: '模型与报告' }])
const intro = computed(() => tab.value === 'videos'
  ? '视频源与每次分析分开保存。打开视频后，可在分析面板切换历次结果。'
  : '训练记录、独立评估和质量报告按模型分别保存，导入后不可修改。')
// Mount the research view on first visit so opening the video list does not fetch model history.
const modelsOpened = ref(false)
watch(tab, value => { if (value === 'models') modelsOpened.value = true })

function statusText(item) {
  if (item.status === 'failed') return '旧检测失败 · 可重新分析'
  if (item.status === 'processing') return '旧检测处理中'
  return '已保存'
}
function statusClass(item) { return item.status === 'failed' ? 'tag-danger' : item.status === 'processing' ? 'tag-warn' : '' }
</script>

<style scoped>
.records { height: 100%; overflow-y: auto; padding: 24px; }
.page-head, .tabs { max-width: 1120px; margin-inline: auto; }
.page-head { margin-bottom: 12px; }
h1 { font-size: var(--text-heading); font-weight: 600; letter-spacing: -0.01em; }
.page-head .note { margin-top: 4px; }
.tabs :deep(.ui-tabs-list) { padding: 0; margin-bottom: 16px; }
.panel { border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); overflow: hidden; }
.table { width: 100%; border-collapse: collapse; font-size: var(--text-body); }
th { height: 34px; padding: 0 14px; text-align: start; font-size: var(--text-caption); font-weight: 500; color: var(--ink-3); background: var(--surface-2); }
td { height: 44px; padding: 0 14px; box-shadow: inset 0 1px 0 var(--line); }
tr:hover td { background: var(--surface-2); }
.num { text-align: end; width: 80px; }
.name { display: flex; align-items: center; gap: 10px; height: 44px; min-width: 0; }
.name .tabler-icon { color: var(--ink-3); }
.name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 56ch; }
.action { width: 1%; text-align: end; }
.action .tabler-icon { --icon-size: 14px; }
.empty { padding: 32px 20px; }
.empty-title { font-weight: 500; margin-bottom: 4px; }
@media (max-width: 640px) { .records { padding: 12px; } .num { display: none; } }
</style>
