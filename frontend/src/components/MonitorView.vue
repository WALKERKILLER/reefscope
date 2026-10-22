<template>
  <div class="flex-1 flex flex-col h-full bg-m3-bg overflow-hidden p-6 gap-6 relative">
    <div class="flex items-center justify-between z-10">
      <div>
        <h1 class="text-xl font-semibold text-m3-on-surface flex items-center gap-3">
          <i class="w-6 h-6 text-m3-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6 block">
              <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/>
              <circle cx="12" cy="13" r="3"/>
            </svg>
          </i>
          实时监控台
          <span class="text-[10px] bg-m3-primary/20 text-m3-primary border border-m3-primary/30 px-2 py-0.5 rounded uppercase tracking-widest font-bold">开发中</span>
        </h1>
        <p class="text-sm text-m3-on-surface-variant mt-1">接入边缘计算节点的实时流媒体信号</p>
      </div>
      <div class="flex gap-2">
        <div class="flex items-center gap-2 px-3 py-1.5 bg-m3-surface-container rounded-lg border border-m3-outline-variant/50 text-[12px] font-medium text-m3-on-surface-variant">
          <div class="w-2 h-2 rounded-full bg-m3-success animate-pulse"></div>
          连接池就绪
        </div>
      </div>
    </div>

    <div class="flex-1 grid grid-cols-2 lg:grid-cols-3 gap-4 z-10">
      <div v-for="i in 6" :key="i" class="bg-m3-surface rounded-xl border border-m3-outline-variant/30 overflow-hidden flex flex-col relative group">
        <div class="absolute inset-0 bg-m3-surface-container-high/50 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20 backdrop-blur-sm">
          <i class="w-8 h-8 text-m3-on-surface-variant mb-2 opacity-50">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-8 h-8 block">
              <circle cx="12" cy="12" r="2"/>
              <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>
            </svg>
          </i>
          <span class="text-[12px] font-medium text-m3-on-surface-variant">等待信令交互...</span>
        </div>

        <div class="h-8 bg-m3-surface-container/50 border-b border-m3-outline-variant/30 flex items-center justify-between px-3 shrink-0">
          <span class="text-[11px] font-mono text-m3-on-surface-variant">CAM_NODE_{{ String(i).padStart(2, '0') }}</span>
          <span class="text-[10px] bg-m3-surface-container-high px-1.5 rounded text-m3-on-surface-variant">OFFLINE</span>
        </div>
        <div class="flex-1 bg-black/5 flex items-center justify-center relative overflow-hidden">
          <div class="absolute inset-0 opacity-10 bg-[radial-gradient(ellipse_at_center,var(--tw-gradient-stops))] from-m3-on-surface-variant to-transparent"></div>
          <i class="w-8 h-8 text-m3-outline/30">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-8 h-8 block">
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </i>
        </div>
      </div>
    </div>

    <!-- Background Decorative -->
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.03]">
      <i class="w-[40vw] h-[40vw] text-m3-primary">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-full h-full block">
          <circle cx="12" cy="12" r="2"/>
          <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>
        </svg>
      </i>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
</style>
