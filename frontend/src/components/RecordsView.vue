<template>
  <div class="records">
    <header class="page-head">
      <div>
        <h1>记录</h1>
        <p class="note">视频源与每次分析分开保存。打开视频后，可在分析记录中切换历次结果。</p>
      </div>
    </header>
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
  </div>
</template>

<script setup>
import { IconMovie, IconArrowRight } from '@tabler/icons-vue'
defineProps({ history: { type: Array, default: () => [] } })
const emit = defineEmits(['play-record'])
function statusText(item) {
  if (item.status === 'failed') return '旧检测失败 · 可重新分析'
  if (item.status === 'processing') return '旧检测处理中'
  return '已保存'
}
function statusClass(item) { return item.status === 'failed' ? 'tag-danger' : item.status === 'processing' ? 'tag-warn' : '' }
</script>

<style scoped>
.records { height: 100%; overflow-y: auto; padding: 24px; }
.page-head { max-width: 1120px; margin: 0 auto 16px; }
h1 { font-size: var(--text-heading); font-weight: 600; letter-spacing: -0.01em; }
.page-head .note { margin-top: 4px; }
.panel { max-width: 1120px; margin: 0 auto; border-radius: var(--radius-lg); background: var(--surface); box-shadow: 0 0 0 1px var(--line); overflow: hidden; }
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
