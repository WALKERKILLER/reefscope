<template>
  <div class="record-page">
    <header><h1>记录与研究证据</h1><nav aria-label="记录分类"><button @click="view='videos'" :aria-pressed="view==='videos'">视频任务</button><button @click="view='models'" :aria-pressed="view==='models'">模型与报告</button></nav></header>
    <template v-if="view==='videos'"><p>视频源与多次分析 Run 分别保存。点击视频进入工作台，切换对应分析历史。</p><p v-if="!history.length" class="empty">暂无视频。请在控制台上传 MP4。</p><ul><li v-for="item in history" :key="item.id"><div><strong>{{ item.name }}</strong><span>Task {{ item.taskId || item.id }} · {{ item.status==='failed'?'旧检测任务失败，源视频仍可重新分析':item.status==='processing'?'旧检测任务处理中':'视频已保存' }}</span></div><button @click="emit('play-record',item)">打开分析历史</button></li></ul></template>
    <ModelResearch v-else />
  </div>
</template>
<script setup>
import {ref,defineAsyncComponent} from 'vue'
const ModelResearch=defineAsyncComponent(()=>import('./ModelResearch.vue'))
defineProps({history:{type:Array,default:()=>[]}})
const emit=defineEmits(['play-record'])
const view=ref('videos')
</script>
<style scoped>
.record-page{flex:1;min-width:0;height:100%;overflow:auto;padding:24px;color:var(--theme-on-surface)}header{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:24px}h1{font-size:22px;font-weight:650}nav{display:flex;gap:8px}button{padding:8px 12px;background:var(--theme-surface-container);border:1px solid var(--theme-outline);border-radius:6px;color:var(--theme-on-surface);font-size:12px;cursor:pointer}button[aria-pressed=true]{background:var(--theme-primary);color:var(--theme-on-primary);border-color:transparent}p{font-size:12px;color:var(--theme-on-surface-variant);line-height:1.8}.empty{padding:32px 0}ul{padding:0;list-style:none;max-width:1120px;margin:20px auto}li{display:flex;justify-content:space-between;align-items:center;gap:18px;background:var(--theme-surface);padding:16px;margin:10px 0;border-radius:8px;border:1px solid var(--theme-outline-variant)}strong{font-size:14px;overflow-wrap:anywhere}li span{display:block;font-size:11px;color:var(--theme-on-surface-variant);margin-top:6px}:focus-visible{outline:2px solid var(--theme-primary);outline-offset:2px}@media(max-width:600px){header{align-items:start;flex-direction:column}li{align-items:start;flex-direction:column}.record-page{padding:16px}}
</style>
