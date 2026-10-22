<template>
  <aside class="analysis-panel" aria-label="鱼类分析">
    <header><h2>鱼类分析</h2><button @click="boot" :disabled="busy">刷新</button></header>
    <p v-if="demo" class="notice">合成演示 · 训练拼图重复帧，不代表真实场景精度</p>
    <p v-if="error" class="error" role="alert">{{ error }} <button @click="boot">重新连接</button></p>
    <form @submit.prevent="createRun" class="section">
      <label>注册模型<select v-model="modelId" :disabled="busy"><option value="">选择模型</option><option v-for="model in models" :value="model.id" :key="model.id">{{ model.id }}</option></select></label>
      <p v-if="!models.length && !busy" class="muted">暂无注册模型。请先在后端注册授权权重。</p>
      <div class="pair"><label>置信度<input v-model.number="confidence" type="number" min="0.01" max="1" step="0.01" required /></label><label>镜头<select v-model="motion"><option value="unknown">未知</option><option value="fixed">固定</option><option value="moving">移动</option></select></label></div>
      <button class="primary" :disabled="busy || !modelId">{{ busy ? '请求中…' : '新建 GPU 优先分析' }}</button>
      <p class="muted">独立 Worker 执行；无 CUDA 时回退 CPU，结果注明实际设备。</p>
    </form>
    <section class="section">
      <label>分析历史<select v-model="selectedId"><option value="">尚未选择 Run</option><option v-for="(item,index) in runs" :key="item.run_id" :value="item.run_id">{{ index + 1 }} · {{ states[item.status] || item.status }} · {{ item.run_id.slice(0,8) }}</option></select></label>
      <div v-if="run" class="run-status" aria-live="polite"><strong>{{ states[run.status] || run.status }}</strong><span>{{ run.progress }}% · attempt {{ run.attempt }}/3</span></div>
      <p v-if="run?.status === 'queued'" class="muted">等待独立 Worker 领取，页面可以继续播放。</p>
      <p v-if="run?.status === 'running'" class="muted">正在顺序追踪，完成后读取已校验产物。</p>
      <p v-if="run?.status === 'failed'" class="error">{{ errorText(run.error_code) }}</p>
      <button v-if="run?.status === 'failed' && run.attempt < 3" @click="retryRun" :disabled="busy">重试此 Run</button>
      <p v-if="run?.summary?.device" class="muted">实际设备 {{ run.summary.device }} · {{ run.summary.frame_count }} 帧</p>
    </section>
    <section class="section"><h3>播放叠加</h3>
      <div class="checks"><label><input type="checkbox" v-model="layers.boxes" />框与真实 ID</label><label><input type="checkbox" v-model="layers.tails" />观测尾迹</label><label><input type="checkbox" v-model="layers.heatmap" />活动热图</label><label><input type="checkbox" v-model="layers.fullTracks" />全窗轨迹</label></div>
      <label>尾迹时长<select v-model.number="layers.tailSeconds"><option :value="5">5 秒</option><option :value="10">10 秒</option><option :value="30">30 秒</option></select></label>
      <label>热图透明度 {{ Math.round(layers.opacity*100) }}%<input type="range" min="0" max="1" step="0.05" v-model.number="layers.opacity" /></label>
      <p class="notice">画面相对占据度，非海底地理坐标。颜色为归一化显示，原始单位为 track-seconds。</p>
      <p v-if="trackLoading" class="muted" role="status">加载当前播放窗口…</p><p v-if="trackWarning" class="error">{{ trackWarning }}</p>
    </section>
    <form class="section" @submit.prevent="applyFilters"><h3>统计窗口与筛选</h3>
      <div class="pair"><label>起点（秒）<input v-model.number="filterStart" type="number" min="0" step="0.1" required /></label><label>终点（秒，空为全片）<input v-model="filterEnd" type="number" min="0" step="0.1" /></label></div>
      <div class="pair"><label>类别<select v-model="classId"><option value="">全部类别</option><option v-for="(label,id) in selectedModel?.labels || {}" :key="id" :value="id">{{ label }}</option></select></label><label>真实 track ID<input v-model="trackId" type="number" min="0" step="1" placeholder="全部" /></label></div>
      <label>画面 ROI<select v-model="roiPreset"><option value="all">全画面</option><option value="left">左半画面</option><option value="center">中央区域</option><option value="custom">自定义多边形</option></select></label>
      <template v-if="roiPreset === 'custom'"><label>归一化顶点 JSON<textarea v-model="roiText" rows="3" placeholder="[[0,0],[1,0],[1,1]]"></textarea></label><div class="pair"><button type="button" @click="startRoi">{{ layers.roiEditing ? '继续在视频点选' : '在视频上点选' }}</button><button type="button" @click="clearRoi">清空顶点</button></div></template>
      <button :disabled="run?.status !== 'completed' || statsLoading">{{ statsLoading ? '计算中…' : '应用窗口与筛选' }}</button>
      <p class="muted">ROI 筛选热图与统计；框和尾迹保留上下文。窗口左闭右开。控件修改后需点击应用。</p><p v-if="summary" class="muted">已应用：{{ applied.start_ms / 1000 }} 至 {{ applied.end_ms == null ? '全片结束' : applied.end_ms / 1000 }} 秒。导出沿用此窗口。</p>
    </form>
    <section class="section"><h3>播放窗口观测</h3><p v-if="!visibleTracks.length" class="muted">当前窗口无追踪观测。可播放或拖动进度条。</p><div class="track-events"><button v-for="point in visibleTracks" :key="point.track_id" @click="emit('seek',point.timestamp_ms/1000)">{{ (point.timestamp_ms/1000).toFixed(2) }}s · {{ point.label }} #{{ point.track_id }}</button></div><p class="muted">最多列出当前缓存窗口的 12 条轨迹入口。点击定位真实观测，使用 ID 筛选查看更多。</p></section>
    <section class="section"><h3>证据摘要</h3>
      <dl v-if="summary"><template v-for="(title,key) in metricNames" :key="key"><dt>{{ title }}</dt><dd :title="summary.metrics[key]?.reason || summary.metrics[key]?.denominator">{{ metricText(summary.metrics[key]) }}</dd></template></dl>
      <p v-else class="muted">完成 Run 后查看同源统计。缺失数据不会补为零。</p>
      <p class="muted">ID 数不是去重鱼类个体数；平均置信度不是准确率。无独立 GT，AP50 / IDF1 为 N/A。无珊瑚分割与底栖 ROI，珊瑚覆盖率为 N/A。</p>
      <div class="exports"><button @click="download('summary','json')" :disabled="!summary">分析 JSON</button><button @click="download('heatmap','csv')" :disabled="!summary">热图 CSV</button><button @click="download('heatmap','json')" :disabled="!summary">热图 JSON</button><button @click="exportTracks" :disabled="!tracks.length || !!trackWarning || trackLoading">当前播放窗口 JSONL</button></div>
      <p v-if="message" class="muted" role="status">{{ message }}</p>
      <details v-if="run"><summary>来源与限制</summary><p class="muted break">Run {{ run.run_id }}<br />模型 {{ run.config_snapshot.models.fish }}<br />SHA256 {{ run.config_snapshot.model_sha256 }}<br />{{ summary?.heatmap?.algorithm_version || '等待计算' }}</p></details>
    </section>
  </aside>
</template>

<script setup>
import { ref, reactive, computed, watch, onBeforeUnmount } from 'vue'
import { listAnalysisModels, listAnalysisRuns, createAnalysisRun, getAnalysisRun, retryAnalysisRun, getAnalysisTracks, getAnalysisHeatmap, getAnalysisSummary, downloadAnalysis } from '../api'
const props = defineProps({ taskId: Number, currentTime: { type:Number, default:0 }, fileName:String })
const emit = defineEmits(['analysis','seek'])
const models=ref([]), runs=ref([]), modelId=ref(''), selectedId=ref(''), run=ref(null), tracks=ref([]), heatmap=ref(null), summary=ref(null)
const busy=ref(false), error=ref(''), message=ref(''), statsLoading=ref(false), trackLoading=ref(false), trackWarning=ref('')
const confidence=ref(0.25), motion=ref('unknown'), filterStart=ref(0), filterEnd=ref(''), classId=ref(''), trackId=ref(''), roiPreset=ref('all'), roiText=ref('[]')
const layers=reactive({boxes:true,tails:true,heatmap:false,opacity:0.45,tailSeconds:10,roiEditing:false,fullTracks:false})
const applied=ref({start_ms:0})
const states={queued:'排队中',running:'分析中',completed:'已完成',failed:'失败'}
const metricNames={observed_track_count:'观测 ID 数',tracked_observation_count:'追踪观测次数',track_seconds:'有效停留（track-s）',mean_confidence:'平均置信度',ap50:'独立测试 AP50',idf1:'人工真值 IDF1',coral_cover:'珊瑚覆盖率'}
const visibleTracks=computed(()=>[...new Map(tracks.value.map(p=>[p.track_id,p])).values()].slice(0,12))
const demo=computed(()=>/synthetic|合成|DEMO/i.test(props.fileName || ''))
const selectedModel=computed(()=>models.value.find(m=>m.id===(run.value?.config_snapshot.models.fish || modelId.value)))
let generation=0, pollTimer, bootAbort, pollAbort, statsAbort, trackAbort, disposed=false
function cancelled(e) { return e?.code==='ERR_CANCELED' || e?.name==='AbortError' }
function errorText(code) {
  const messages = {
    invalid_settings:'参数无效，请检查阈值和图像尺寸', unknown_model:'模型不存在，请刷新模型列表',
    retry_not_allowed:'该 Run 当前不可重试，或已达到次数上限', worker_lease_expired:'Worker 心跳已过期，请确认 Worker 已恢复后重试',
    model_hash_mismatch:'权重与注册 hash 不一致，请重新注册为新模型版本', invalid_video:'源视频不可读取，请检查本地文件和权限',
    video_decode_failed:'视频解码失败，请检查 MP4 文件是否完整', video_incomplete:'视频提前结束，请检查源文件',
    video_time_reversed:'视频时间戳倒退，已停止分析以保护轨迹时间', video_time_unavailable:'缺少可靠时间戳与帧率，无法生成轨迹',
    analysis_failed:'分析失败，请查看本地 Worker 的运行状态', invalid_artifacts:'产物校验失败，未发布不完整结果'
  }
  return messages[code] || code || '分析失败'
}
function problem(e) { return e?.response?.data?.error?.code ? errorText(e.response.data.error.code) : (e?.response ? `请求失败（${e.response.status}）` : '网络连接失败，请检查本地后端') }
function publish() { emit('analysis',{runId:run.value?.run_id,summary:summary.value,tracks:tracks.value,heatmap:heatmap.value,layers:{...layers},roi:applied.value.roi || null,allowedGap:run.value?.config_snapshot.settings.allowed_gap_seconds || 0.5,fps:run.value?.summary?.fps || 30}) }
watch(layers,publish,{deep:true})
async function boot() {
  const version=++generation
  clearTimeout(pollTimer); bootAbort?.abort(); pollAbort?.abort(); statsAbort?.abort(); trackAbort?.abort()
  bootAbort=new AbortController(); run.value=null; selectedId.value=''; tracks.value=[]; heatmap.value=null; summary.value=null; runs.value=[]; error.value=''; busy.value=true; publish()
  try {
    const [m,r]=await Promise.all([listAnalysisModels(bootAbort.signal),listAnalysisRuns(props.taskId,bootAbort.signal)])
    if(version!==generation || disposed) return
    models.value=m.data.items; runs.value=r.data.items; modelId.value=models.value[0]?.id || ''; selectedId.value=runs.value[0]?.run_id || ''
  } catch(e) { if(!cancelled(e) && version===generation) error.value=problem(e) }
  finally { if(version===generation) busy.value=false }
}
watch(()=>props.taskId,boot,{immediate:true})
watch(selectedId,async id=>{
  if(!id) return
  const version=++generation
  clearTimeout(pollTimer); pollAbort?.abort(); statsAbort?.abort(); trackAbort?.abort()
  applied.value={start_ms:0}; filterStart.value=0; filterEnd.value=''; classId.value=''; trackId.value=''; roiPreset.value='all'; layers.roiEditing=false
  run.value=runs.value.find(r=>r.run_id===id) || null; tracks.value=[]; heatmap.value=null; summary.value=null; trackWarning.value=''; publish()
  if(!id || disposed) return
  await poll(version)
})
async function poll(version) {
  if(version!==generation || disposed) return
  pollAbort=new AbortController()
  try {
    const response=await getAnalysisRun(selectedId.value,pollAbort.signal)
    if(version!==generation || disposed) return
    run.value=response.data; error.value=''
    runs.value=runs.value.map(r=>r.run_id===run.value.run_id?run.value:r)
    if(run.value.status==='completed') { await Promise.all([loadStats(),loadTracks()]); return }
    if(run.value.status==='failed') return
  } catch(e) { if(!cancelled(e) && version===generation) error.value=problem(e) }
  if(version===generation && !disposed) pollTimer=setTimeout(()=>poll(version),1500)
}
async function createRun() {
  if(busy.value) return
  busy.value=true; error.value=''; const task=props.taskId
  try {
    const response=await createAnalysisRun(task,{kind:'fish',models:{fish:modelId.value},settings:{confidence_threshold:confidence.value,camera_motion:motion.value}})
    if(task!==props.taskId || disposed) return
    runs.value=[response.data,...runs.value]; selectedId.value=response.data.run_id
  } catch(e) { error.value=problem(e) } finally { busy.value=false }
}
async function retryRun() {
  if(busy.value) return
  busy.value=true
  const id=selectedId.value
  try { const response=await retryAnalysisRun(id); if(id!==selectedId.value || disposed) return; run.value=response.data; poll(generation) }
  catch(e) { error.value=problem(e) } finally { busy.value=false }
}
function applyFilters() {
  const params={start_ms:Number(filterStart.value)*1000}
  if(filterEnd.value!=='') params.end_ms=Number(filterEnd.value)*1000
  if(!Number.isFinite(params.start_ms) || params.start_ms<0 || ('end_ms' in params && (!Number.isFinite(params.end_ms) || params.end_ms<=params.start_ms))) { error.value='终点必须大于起点，时间必须为有限非负数'; return }
  for(const [key,value] of [['class_id',classId.value],['track_id',trackId.value]]) if(value!=='') { if(!Number.isInteger(Number(value)) || Number(value)<0) {error.value='筛选 ID 必须为非负整数';return}; params[key]=Number(value) }
  let roi=null
  if(roiPreset.value==='left') roi=[[0,0],[0.5,0],[0.5,1],[0,1]]
  if(roiPreset.value==='center') roi=[[0.25,0.25],[0.75,0.25],[0.75,0.75],[0.25,0.75]]
  if(roiPreset.value==='custom') { try {roi=JSON.parse(roiText.value); if(!Array.isArray(roi)||roi.length<3||roi.length>64||roi.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>typeof v!=='number'||!Number.isFinite(v)||v<0||v>1))) throw new Error() } catch {error.value='ROI 需为 3–64 个归一化顶点';return} }
  if(roi) params.roi=roi
  layers.roiEditing=false; applied.value=params; error.value=''; loadStats();loadTracks()
}
function queryParams() { return {...applied.value,...(applied.value.roi?{roi:JSON.stringify(applied.value.roi)}:{})} }
async function loadStats() {
  if(run.value?.status!=='completed') return
  statsAbort?.abort(); const controller=new AbortController(); statsAbort=controller; const id=selectedId.value
  statsLoading.value=true; summary.value=null; heatmap.value=null; publish()
  try {const [h,s]=await Promise.all([getAnalysisHeatmap(id,queryParams(),controller.signal),getAnalysisSummary(id,queryParams(),controller.signal)]); if(controller.signal.aborted||id!==selectedId.value||disposed)return; heatmap.value=h.data;summary.value=s.data;error.value='';publish()}
  catch(e){if(!cancelled(e))error.value=problem(e)} finally{if(statsAbort===controller)statsLoading.value=false}
}
async function loadTracks() {
  if(run.value?.status!=='completed') return
  trackAbort?.abort(); const controller=new AbortController();trackAbort=controller; const id=selectedId.value
  const start=Math.max(applied.value.start_ms, layers.fullTracks ? 0 : Math.floor(props.currentTime/4)*4000-layers.tailSeconds*1000)
  const end=Math.min(applied.value.end_ms ?? Infinity,layers.fullTracks ? Infinity : Math.floor(props.currentTime/4)*4000+4500)
  tracks.value=[];trackWarning.value='';trackLoading.value=true;publish()
  if(end<=start){trackLoading.value=false;return}
  const params={start_ms:start,limit:2000}
  if(Number.isFinite(end)) params.end_ms=end
  for(const key of ['class_id','track_id'])if(key in applied.value)params[key]=applied.value[key]
  try {
    let cursor=null;const result=[]
    do {const response=await getAnalysisTracks(id,{...params,...(cursor?{cursor}:{})},controller.signal); if(controller.signal.aborted||id!==selectedId.value||disposed)return; result.push(...response.data.items);cursor=response.data.next_cursor} while(cursor&&result.length<20000)
    if(cursor)trackWarning.value='当前窗口超过 20000 条，请缩短尾迹或筛选类别。窗口导出已禁用。'
    tracks.value=result;publish()
  } catch(e){if(!cancelled(e)){trackWarning.value=problem(e);tracks.value=[];publish()}} finally{if(trackAbort===controller)trackLoading.value=false}
}
watch([()=>layers.fullTracks ? -1 : Math.floor(props.currentTime/4),()=>layers.tailSeconds,()=>layers.fullTracks],loadTracks)
function startRoi(){roiPreset.value='custom';layers.roiEditing=true;message.value='在视频画面点选顶点，至少三个点后应用筛选。'}
function clearRoi(){roiText.value='[]'}
function addRoiPoint(point){if(!layers.roiEditing)return;let points=[];try{points=JSON.parse(roiText.value)}catch{};if(!Array.isArray(points))points=[];if(points.length<64){points.push(point);roiText.value=JSON.stringify(points)}}
defineExpose({addRoiPoint,refresh:boot})
function metricText(m){return m?.value==null?'N/A':Number.isInteger(m.value)?m.value:Number(m.value).toFixed(3)}
function saveBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
async function download(resource,format){try{const response=await downloadAnalysis(selectedId.value,resource,{...queryParams(),export:format});saveBlob(response.data,`${resource==='summary'?'analysis_report':'heatmap'}.${format}`);message.value='已导出当前统计窗口与来源元数据'}catch{error.value='导出失败，请刷新后重试'}}
function exportTracks(){saveBlob(new Blob([tracks.value.map(p=>JSON.stringify(p)).join('\n')+'\n'],{type:'application/x-ndjson'}),'playback-window-tracks.jsonl');message.value='已导出当前播放缓存窗口的真实观测，不包含全片轨迹。'}
onBeforeUnmount(()=>{disposed=true;generation++;clearTimeout(pollTimer);for(const c of [bootAbort,pollAbort,statsAbort,trackAbort])c?.abort()})
</script>

<style scoped>
.analysis-panel{height:100%;overflow:auto;background:var(--theme-surface);padding:16px;color:var(--theme-on-surface);font-size:12px}header,.run-status{display:flex;justify-content:space-between;align-items:center;gap:8px}h2{font-size:16px;font-weight:650}h3{font-size:13px;font-weight:600;margin-bottom:12px}.section{padding:18px 0;border-bottom:1px solid var(--theme-outline-variant)}label{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}.pair>*{min-width:0}input:not([type=checkbox]),select,textarea{width:100%;padding:8px;border:1px solid var(--theme-on-surface-variant);border-radius:6px;background:var(--theme-bg);color:var(--theme-on-surface);font:inherit}input[type=range]{padding:0}button{padding:7px 11px;border:1px solid var(--theme-outline);border-radius:6px;background:var(--theme-surface-container);cursor:pointer;white-space:nowrap}button:hover{border-color:var(--theme-primary)}button:disabled{opacity:.45;cursor:not-allowed}.primary{background:var(--theme-primary);color:var(--theme-on-primary);width:100%;border-color:transparent}.muted{color:var(--theme-on-surface-variant);line-height:1.6;margin-top:8px}.notice{padding:10px;border-left:2px solid var(--theme-primary);background:var(--theme-primary-container);color:var(--theme-on-primary-container);line-height:1.6;margin-top:10px}.error{color:var(--theme-error);line-height:1.6;margin:8px 0}.checks{display:flex;gap:12px;flex-wrap:wrap}.checks label{flex-direction:row;align-items:center;gap:5px}.run-status{padding-top:12px}dl{display:grid;grid-template-columns:1fr auto;gap:10px}dd{font-family:var(--font-mono);font-variant-numeric:tabular-nums}.exports{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.track-events{display:flex;gap:6px;flex-wrap:wrap}.track-events button{font-size:11px}.break{overflow-wrap:anywhere}details{margin-top:14px}summary{cursor:pointer}:focus-visible{outline:2px solid var(--theme-primary);outline-offset:2px}
</style>
