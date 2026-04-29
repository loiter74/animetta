<script setup lang="ts">
import { useConnectionStore } from '@/stores/connection'

const store = useConnectionStore()

const statusColors: Record<string, string> = {
  connected: 'bg-$c-success shadow-[0_0_8px_rgba(74,222,128,0.6)]',
  disconnected: 'bg-$c-error',
  connecting: 'bg-$c-warning animate-pulse',
  error: 'bg-$c-error'
}

const statusLabels: Record<string, string> = {
  connected: '已连接',
  disconnected: '未连接',
  connecting: '连接中...',
  error: '连接错误'
}
</script>

<template>
  <div class="flex items-center justify-between h-9 bg-$c-surface/80 backdrop-blur-md border-b border-$c-border select-none">
    <!-- Drag area -->
    <div class="flex-1 flex items-center pl-4 app-drag">
      <span class="text-sm font-medium text-$c-text tracking-wide">Anima</span>

      <!-- Connection status -->
      <div class="flex items-center gap-2 ml-4">
        <span class="w-2 h-2 rounded-full" :class="statusColors[store.status]" />
        <span class="text-xs text-$c-text-dim">{{ statusLabels[store.status] }}</span>
      </div>
    </div>

    <!-- Window controls -->
    <div class="flex">
      <button
        class="w-10 h-9 flex items-center justify-center text-$c-text-dim hover:bg-white/10 hover:text-$c-text transition-colors"
        @click="window.electronAPI?.window?.minimize()"
      >
        <svg width="12" height="1" viewBox="0 0 12 1"><rect width="12" height="1" fill="currentColor" /></svg>
      </button>
      <button
        class="w-10 h-9 flex items-center justify-center text-$c-text-dim hover:bg-$c-accent hover:text-white transition-colors"
        @click="window.electronAPI?.window?.close()"
      >
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M1 1L11 11M11 1L1 11" stroke="currentColor" stroke-width="1.5" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.app-drag {
  -webkit-app-region: drag;
}
button {
  -webkit-app-region: no-drag;
}
</style>
