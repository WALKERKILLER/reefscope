<template>
  <section class="monitor-evidence" aria-label="鱼类活动监测证据">
    <div class="monitor-heading"><div><h1>鱼类活动监测</h1><p>{{ fileName || '先在控制台选择视频' }} · 画面坐标分析</p></div><span>{{ analysis?.runId ? `Run ${analysis.runId.slice(0,8)}` : '暂无分析结果' }}</span></div>
    <dl>
      <div v-for="(label,key) in metrics" :key="key"><dt>{{ label }}</dt><dd>{{ display(analysis?.summary?.metrics[key]) }}</dd></div>
    </dl>
    <p class="limitations">同一 Run 与已应用窗口的后端统计。ID 数不是生物个体数；无 GT 不报告精度，珊瑚健康 N/A。</p>
  </section>
</template>
<script setup>
defineProps({analysis:{type:Object,default:null},fileName:String})
const metrics={observed_track_count:'观测轨迹 ID',track_seconds:'有效停留 · track-s',mean_confidence:'平均置信度',ap50:'独立测试 AP50'}
function display(metric){return metric?.value==null?'N/A':Number.isInteger(metric.value)?metric.value:Number(metric.value).toFixed(3)}
</script>
<style scoped>
.monitor-evidence{flex:none;padding:12px 8px 16px}.monitor-heading{display:flex;gap:16px;align-items:center;justify-content:space-between}h1{font-size:18px;font-weight:650}.monitor-heading p,.monitor-heading span,.limitations{font-size:11px;color:var(--theme-on-surface-variant)}dl{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:14px 0}dt{font-size:11px;color:var(--theme-on-surface-variant)}dd{font-size:23px;font-family:var(--font-mono);font-variant-numeric:tabular-nums}.limitations{line-height:1.5}@media(max-width:800px){dl{grid-template-columns:repeat(2,minmax(0,1fr))}.monitor-heading{align-items:start;flex-direction:column;gap:4px}}
</style>
