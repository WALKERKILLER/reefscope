<template>
  <section class="research-library" aria-label="模型训练与质量报告">
    <header><div><h2>模型证据与报告</h2><p>训练、独立评估和报告分别保存。没有真值时保留 N/A，不以验证曲线替代测试精度。</p></div><button @click="loadModels" :disabled="loading">刷新</button></header>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <div class="selectors"><label>注册模型<select v-model="modelId"><option v-for="model in models" :key="model.id" :value="model.id">{{ model.id }}</option></select></label><label>报告版本<select v-model="reportId"><option value="">选择报告</option><option v-for="item in history?.reports || []" :key="item.id" :value="item.id">{{ new Date(item.created_at).toLocaleString() }} · {{ item.id.slice(0,8) }} · 待人工审阅</option></select></label></div>
    <p v-if="loading" role="status">正在读取不可变记录…</p>
    <p v-if="history && !history.reports.length && !loading">暂无报告。由维护者从受控训练目录导入数值产物；页面不接受服务器文件路径。</p>
    <details v-if="history" class="history"><summary>训练与独立评估历史</summary><p>训练记录 {{ history.training_runs.length }} 条，评估记录 {{ history.evaluations.length }} 条。</p><p v-if="!history.evaluations.length">N/A：尚无冻结真值评估记录。mAP 与 IDF1 不从训练曲线推导。</p><div v-for="evaluation in history.evaluations" :key="evaluation.id" class="evaluation"><strong>{{ evaluation.protocol_id }}</strong><span>{{ evaluation.dataset_version }} · {{ evaluation.id.slice(0,8) }}</span><pre>{{ JSON.stringify(evaluation.metrics,null,2) }}</pre></div></details>
    <template v-if="report">
      <div class="report-meta"><p>模型 {{ report.model_id }} · 报告 {{ report.report_id }} · 待人工审阅</p><p class="hash">权重 SHA256 {{ report.model_sha256 }}</p><p>框架 best fitness：{{ report.checkpoint_selection.framework_best_fitness ?? 'N/A' }}；best mAP50 epoch：{{ report.checkpoint_selection.best_map50_epoch ?? 'N/A' }}；best mAP50-95 epoch：{{ report.checkpoint_selection.best_map50_95_epoch ?? 'N/A' }}</p><div class="actions"><button @click="download" :disabled="downloading">下载 Markdown</button><a :href="reportPrintUrl(report.report_id)" target="_blank" rel="noopener">打开打印版 / 保存 PDF</a></div><p v-if="message" role="status">{{ message }}</p></div>
      <TrainingCurves :rows="report.training_curves" />
      <article aria-label="七章确定性报告"><section v-for="(section,index) in report.sections" :key="section.title"><h3>{{ index+1 }}. {{ section.title }}</h3><p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p><table v-if="section.rows.length"><tbody><tr v-for="(row,i) in section.rows" :key="i"><th>{{ row[0] }}</th><td>{{ display(row[1]) }}</td></tr></tbody></table><details v-if="section.evidence"><summary>来源数值与复现信息</summary><pre>{{ JSON.stringify(section.evidence,null,2) }}</pre></details></section></article>
    </template>
  </section>
</template>
<script setup>
import {ref,watch,onMounted,onBeforeUnmount,defineAsyncComponent} from 'vue'
import {listAnalysisModels,getModelResearch,getTrainingReport,downloadTrainingReport,reportPrintUrl} from '../api'
const TrainingCurves=defineAsyncComponent(()=>import('./TrainingCurves.vue'))
const models=ref([]),modelId=ref(''),history=ref(null),reportId=ref(''),report=ref(null),loading=ref(false),error=ref(''),message=ref(''),downloading=ref(false)
let modelsAbort,historyAbort,reportAbort,disposed=false
function cancelled(e){return e?.code==='ERR_CANCELED'}
async function loadModels(){
  modelsAbort?.abort();const controller=new AbortController();modelsAbort=controller;error.value=''
  try{const response=await listAnalysisModels(controller.signal);if(controller.signal.aborted||disposed)return;models.value=response.data.items;if(!models.value.some(m=>m.id===modelId.value))modelId.value=models.value[0]?.id||'';else loadHistory()}
  catch(e){if(!cancelled(e))error.value='模型列表读取失败，请检查本地后端'}
}
async function loadHistory(){
  historyAbort?.abort();reportAbort?.abort();const controller=new AbortController();historyAbort=controller
  reportId.value='';history.value=null;report.value=null;loading.value=true;error.value=''
  if(!modelId.value){loading.value=false;return}
  try{const response=await getModelResearch(modelId.value,controller.signal);if(controller.signal.aborted||disposed)return;history.value=response.data;reportId.value=response.data.reports[0]?.id||''}
  catch(e){if(!cancelled(e))error.value='模型历史读取失败，请刷新重试'}finally{if(historyAbort===controller)loading.value=false}
}
watch(modelId,loadHistory)
watch(reportId,async id=>{
  reportAbort?.abort();const controller=new AbortController();reportAbort=controller;report.value=null;message.value=''
  if(!id)return
  try{const response=await getTrainingReport(id,controller.signal);if(!controller.signal.aborted&&!disposed)report.value=response.data}
  catch(e){if(!cancelled(e))error.value='报告读取失败，请重试'}
})
function display(value){if(value==null)return 'N/A';if(typeof value==='object')return 'value' in value?display(value.value):JSON.stringify(value);return String(value)}
async function download(){
  downloading.value=true
  try{const response=await downloadTrainingReport(reportId.value);const url=URL.createObjectURL(response.data),a=document.createElement('a');a.href=url;a.download='training-report.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message.value='已导出当前不可变报告'}catch{error.value='报告导出失败'}finally{downloading.value=false}
}
onMounted(loadModels)
onBeforeUnmount(()=>{disposed=true;for(const c of [modelsAbort,historyAbort,reportAbort])c?.abort()})
</script>
<style scoped>
.research-library{max-width:1120px;margin:auto;width:100%;color:var(--theme-on-surface)}header{display:flex;gap:20px;align-items:start;justify-content:space-between}h2{font-size:21px;font-weight:650}h3{font-size:17px;font-weight:650}p{font-size:12px;line-height:1.8;margin:8px 0;color:var(--theme-on-surface-variant)}button,a{font:inherit;font-size:12px;padding:8px 12px;background:var(--theme-surface-container);border:1px solid var(--theme-outline);border-radius:6px;color:var(--theme-on-surface);cursor:pointer;display:inline-block}a{text-decoration:none}button:disabled{opacity:.5;cursor:not-allowed}.selectors{display:grid;grid-template-columns:1fr 2fr;gap:20px;margin:22px 0}label{display:flex;flex-direction:column;gap:8px;font-size:12px}select{padding:9px;background:var(--theme-surface);color:var(--theme-on-surface);border:1px solid var(--theme-on-surface-variant);border-radius:6px;width:100%;min-width:0}.history,.report-meta{padding:16px;background:var(--theme-surface);border:1px solid var(--theme-outline-variant);border-radius:8px;margin:16px 0}.hash{overflow-wrap:anywhere;font-family:var(--font-mono);font-size:11px}.actions{display:flex;gap:10px;flex-wrap:wrap}article>section{margin:24px 0;padding-top:20px;border-top:1px solid var(--theme-outline-variant)}table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--theme-outline-variant);overflow-wrap:anywhere}th{width:35%;font-weight:500}pre{font-size:11px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere;margin-top:10px}summary{cursor:pointer;font-size:12px}.error{color:var(--theme-error)}.evaluation{padding:10px 0;font-size:12px}.evaluation span{display:block}:focus-visible{outline:2px solid var(--theme-primary);outline-offset:2px}@media(max-width:650px){.selectors{grid-template-columns:1fr}header{flex-direction:column}}
</style>
