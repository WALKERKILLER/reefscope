<template>
  <div class="flex-1 flex flex-col h-full bg-m3-bg overflow-hidden p-6 gap-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-m3-on-surface flex items-center gap-3">
          <i class="w-6 h-6 text-m3-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6 block">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M3 5V19a9 3 0 0 0 18 0V5"/>
              <path d="M3 12a9 3 0 0 0 18 0"/>
            </svg>
          </i>
          处理记录与索引
        </h1>
        <p class="text-sm text-m3-on-surface-variant mt-1">查看历史处理的视频任务，点击以重新加载分析结果</p>
      </div>
      <div class="text-[12px] font-medium text-m3-on-surface-variant bg-m3-surface-container px-3 py-1.5 rounded-lg border border-m3-outline-variant/30">
        共 {{ history.length }} 条记录
      </div>
    </div>

    <div class="flex-1 overflow-y-auto pr-2 space-y-3">
      <div v-if="history.length === 0" class="h-40 flex flex-col items-center justify-center text-m3-on-surface-variant/50 border-2 border-dashed border-m3-outline-variant/30 rounded-xl">
        <i class="w-10 h-10 mb-3 opacity-50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-10 h-10 block">
            <ellipse cx="12" cy="5" rx="9" ry="3"/>
            <path d="M3 5V19a9 3 0 0 0 18 0V5"/>
            <path d="M3 12a9 3 0 0 0 18 0"/>
          </svg>
        </i>
        <span>暂无处理记录</span>
      </div>

      <div
        v-for="item in history"
        :key="item.id"
        @click="item.status === 'processed' ? $emit('play-record', item) : null"
        class="flex items-center justify-between p-4 rounded-xl border border-m3-outline-variant/30 bg-m3-surface"
        :class="item.status === 'processed' ? 'cursor-pointer hover:border-m3-primary/50 hover:shadow-sm group transition-all' : 'opacity-70 grayscale'"
      >
        <div class="flex items-center gap-4">
          <div
            class="w-12 h-12 rounded-lg flex items-center justify-center"
            :class="item.status === 'processed' ? 'bg-m3-primary/10 text-m3-primary group-hover:bg-m3-primary group-hover:text-m3-on-primary transition-colors' : 'bg-m3-error/10 text-m3-error'"
          >
            <i class="w-6 h-6">
              <svg v-if="item.status === 'processed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6 block">
                <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
                <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
                <path d="m10 11 5 3-5 3v-6Z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6 block">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </i>
          </div>
          <div>
            <h3 class="font-medium text-[14px] text-m3-on-surface group-hover:text-m3-primary transition-colors">{{ item.name }}</h3>
            <div class="flex items-center gap-4 mt-1 text-[11px] text-m3-on-surface-variant font-mono">
              <span class="flex items-center gap-1.5">
                <i class="w-3.5 h-3.5">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-3.5 h-3.5 block">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                </i>
                {{ (item.duration / 60).toFixed(1) }} 分钟
              </span>
              <span class="uppercase tracking-wider">{{ String(item.id).substring(0, 8) }}</span>
            </div>
          </div>
        </div>

        <div class="flex flex-col items-end gap-2">
          <span v-if="item.status === 'processed'" class="text-[11px] font-medium tracking-widest text-m3-success uppercase bg-m3-success/10 px-2 py-0.5 rounded">分析完成</span>
          <span v-else class="text-[11px] font-medium tracking-widest text-m3-error uppercase bg-m3-error/10 px-2 py-0.5 rounded">由于错误中止</span>
          <div v-if="item.status === 'processed'" class="text-[11px] text-m3-primary items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex font-medium">
            加载并回放
            <i class="w-3 h-3">
              <svg viewBox="0 0 24 24" fill="currentColor" class="w-3 h-3 block">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            </i>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  history: {
    type: Array,
    default: () => []
  }
})

defineEmits(['play-record'])
</script>

<style scoped>
</style>
