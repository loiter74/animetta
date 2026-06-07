<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useConnectionStore } from '@/stores/connection'

const router = useRouter()
const route = useRoute()
const store = useConnectionStore()

const statusColors: Record<string, string> = {
  connected: 'bg-c-success shadow-[0_0_8px_rgba(74,222,128,0.6)]',
  disconnected: 'bg-c-error',
  connecting: 'bg-c-warning animate-pulse',
  error: 'bg-c-error'
}

const statusLabels: Record<string, string> = {
  connected: 'Connected',
  disconnected: 'Disconnected',
  connecting: 'Connecting...',
  error: 'Connection Error'
}

function goTo(name: string) {
  if (route.name === name) {
    router.push('/')
  } else {
    router.push('/' + (name === 'chat' ? '' : name))
  }
}
</script>

<template>
    <div class="relative flex items-center justify-between h-12 select-none z-50 border border-c-border rounded-lg max-w-[720px] mx-auto px-4">
    <div class="absolute inset-0 bg-c-surface/85 backdrop-blur-[16px]" />
    <div class="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-c-accent/20 to-transparent" />

    <div class="relative flex items-center justify-between w-full">
      <!-- Left: traffic lights + brand -->
      <div class="flex items-center gap-2 min-w-0 shrink-0">
        <span class="w-[10px] h-[10px] rounded-full bg-c-error shrink-0" />
        <span class="w-[10px] h-[10px] rounded-full bg-c-warning shrink-0" />
        <span class="w-[10px] h-[10px] rounded-full bg-c-success shrink-0" />
        <span class="text-base font-bold text-c-text tracking-wide ml-2 font-quicksand truncate">Anima</span>
      </div>

      <!-- Center: nav buttons -->
      <div class="flex items-center gap-1 sm:gap-3 min-w-0 overflow-hidden">
        <button
          @click="goTo('music')"
          aria-label="音乐制作"
          class="px-2 sm:px-3 py-1.5 text-xs rounded-md transition-colors whitespace-nowrap"
          :class="route.name === 'music'
            ? 'text-c-accent bg-c-accent-soft'
            : 'bg-transparent text-c-text-dim hover:bg-white/4'"
        >
          音乐制作
        </button>
        <button
          @click="goTo('meme-review')"
          aria-label="梗筛选"
          class="px-2 sm:px-3 py-1.5 text-xs rounded-md transition-colors whitespace-nowrap"
          :class="route.name === 'meme-review'
            ? 'text-c-accent bg-c-accent-soft'
            : 'bg-transparent text-c-text-dim hover:bg-white/4'"
        >
          梗筛选
        </button>
        <button
          @click="goTo('dashboard')"
          :aria-label="route.name === 'dashboard' ? '返回聊天' : '仪表盘'"
          class="px-2 sm:px-3 py-1.5 text-xs rounded-md transition-colors whitespace-nowrap"
          :class="route.name === 'dashboard'
            ? 'text-c-accent bg-c-accent-soft'
            : 'bg-transparent text-c-text-dim hover:bg-white/4'"
        >
          {{ route.name === 'dashboard' ? 'Chat' : 'Dashboard' }}
        </button>
      </div>

      <!-- Right: connection status -->
      <div class="flex items-center gap-2">
        <span class="w-[7px] h-[7px] rounded-full" :class="statusColors[store.status]" />
        <span class="text-10px text-c-text-dim whitespace-nowrap">{{ statusLabels[store.status] }}</span>
      </div>
    </div>
  </div>
</template>
