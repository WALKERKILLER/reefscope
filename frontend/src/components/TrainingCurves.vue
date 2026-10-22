<template>
  <section class="training-curves" aria-label="真实训练与验证曲线">
    <h3>逐 epoch 数值</h3>
    <p>来源为原始 results.csv。下方精度属于训练过程的验证集，不是独立 test，也不提供 MOT 指标。</p>
    <p v-if="!rows.length">N/A：没有数值曲线。不会从曲线截图估算指标。</p>
    <template v-else><div ref="validationHost" class="chart" role="img" aria-label="验证 mAP50 与 mAP50-95，非独立测试"></div><div ref="lossHost" class="chart" role="img" aria-label="训练与验证损失曲线"></div></template>
    <details v-if="rows.length"><summary>查看原始数值（{{ rows.length }} 个 epoch）</summary><div class="numeric-table"><table><thead><tr><th>epoch</th><th>验证 mAP50</th><th>验证 mAP50-95</th><th>train/box_loss</th><th>val/box_loss</th></tr></thead><tbody><tr v-for="row in rows" :key="row.epoch"><td>{{ row.epoch }}</td><td>{{ row['metrics/mAP50(B)'] ?? 'N/A' }}</td><td>{{ row['metrics/mAP50-95(B)'] ?? 'N/A' }}</td><td>{{ row['train/box_loss'] ?? 'N/A' }}</td><td>{{ row['val/box_loss'] ?? 'N/A' }}</td></tr></tbody></table></div></details>
  </section>
</template>
<script setup>
import { ref,watch,nextTick,onBeforeUnmount } from 'vue'
import { init,use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,AriaComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
// Official modular API: https://echarts.apache.org/handbook/en/basics/import/
use([LineChart,GridComponent,TooltipComponent,LegendComponent,DataZoomComponent,AriaComponent,CanvasRenderer])
const props=defineProps({rows:{type:Array,default:()=>[]}})
const validationHost=ref(null),lossHost=ref(null)
let charts=[],observer=null,disposed=false
function destroy(){observer?.disconnect();observer=null;for(const chart of charts)chart.dispose();charts=[]}
watch(()=>props.rows,async()=>{
  destroy();await nextTick()
  if(disposed||!validationHost.value||!lossHost.value||!props.rows.length)return
  const color=getComputedStyle(document.documentElement).getPropertyValue('--theme-on-surface').trim() || '#334155'
  const groups=[[["验证 mAP50","metrics/mAP50(B)"],["验证 mAP50-95","metrics/mAP50-95(B)"]],[["训练 box loss","train/box_loss"],["验证 box loss","val/box_loss"]]]
  for(const [index,host] of [validationHost.value,lossHost.value].entries()){
    const chart=init(host)
    chart.setOption({animation:false,aria:{enabled:true},color:['#0284c7','#0d9488'],textStyle:{color},tooltip:{trigger:'axis'},legend:{top:8,textStyle:{color}},grid:{left:50,right:24,top:46,bottom:70},xAxis:{type:'category',name:'epoch',data:props.rows.map(r=>r.epoch),axisLabel:{color}},yAxis:{type:'value',min:0,...(index===0?{max:1}:{}),axisLabel:{color}},dataZoom:[{type:'inside'},{type:'slider',height:18,bottom:16}],series:groups[index].map(([name,key])=>({name,type:'line',showSymbol:false,connectNulls:false,sampling:'lttb',data:props.rows.map(r=>r[key]??null)}))})
    charts.push(chart)
  }
  observer=new ResizeObserver(()=>{for(const chart of charts)chart.resize()})
  observer.observe(validationHost.value);observer.observe(lossHost.value)
},{immediate:true})
onBeforeUnmount(()=>{disposed=true;destroy()})
</script>
<style scoped>
.training-curves h3{font-size:16px;font-weight:650}.training-curves p{color:var(--theme-on-surface-variant);font-size:12px;line-height:1.7}.chart{height:280px;width:100%;margin:16px 0;background:var(--theme-surface);border-radius:8px}.numeric-table{overflow:auto;max-height:320px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px;text-align:left;border-bottom:1px solid var(--theme-outline-variant)}summary{cursor:pointer;font-size:12px}
</style>
