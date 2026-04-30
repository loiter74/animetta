<script setup lang="ts">
import { useConnectionStore } from '@/stores/connection'

const store = useConnectionStore()

const statusColors: Record<string, string> = {
  connected: 'bg-c-success shadow-[0_0_8px_rgba(74,222,128,0.6)]',
  disconnected: 'bg-c-error',
  connecting: 'bg-c-warning animate-pulse',
  error: 'bg-c-error'
}

const statusLabels: Record<string, string> = {
  connected: '已连接',
  disconnected: '未连接',
  connecting: '连接中...',
  error: '连接错误'
}
</script>

<template>
  <div class="relative flex items-center justify-between h-9 select-none z-40">
    <!-- Glass background -->
    <div class="absolute inset-0 bg-c-bg/80 backdrop-blur-2xl" />

    <!-- Accent glow border -->
    <div class="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-c-accent/20 to-transparent" />

    <!-- Content -->
    <div class="relative flex items-center justify-between w-full">
      <div class="flex-1 flex items-center pl-4">
        <span class="text-sm font-medium text-c-text tracking-wide">Anima</span>

        <!-- Connection status -->
        <div class="flex items-center gap-2 ml-4">
          <span class="w-2 h-2 rounded-full" :class="statusColors[store.status]" />
          <span class="text-xs text-c-text-dim">{{ statusLabels[store.status] }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
