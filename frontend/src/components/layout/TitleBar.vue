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
  <div class="relative flex items-center justify-between h-11 select-none z-40 border border-c-border rounded-lg max-w-[720px] mx-auto px-4">
    <div class="absolute inset-0 bg-c-surface/85 backdrop-blur-[16px]" />
    <div class="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-c-accent/20 to-transparent" />

    <div class="relative flex items-center justify-between w-full">
      <div class="flex-1 flex items-center">
        <div class="flex items-center gap-2 mr-2">
          <span class="w-[10px] h-[10px] rounded-full bg-c-error" />
          <span class="w-[10px] h-[10px] rounded-full bg-c-warning" />
          <span class="w-[10px] h-[10px] rounded-full bg-c-success" />
        </div>
        <span class="text-sm font-medium text-c-text tracking-wide">Anima</span>
        <div class="flex items-center gap-2 ml-4">
          <span class="w-[7px] h-[7px] rounded-full" :class="statusColors[store.status]" />
          <span class="text-10px text-c-text-dim">{{ statusLabels[store.status] }}</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="goTo('music')"
          class="px-3 py-1.5 text-xs rounded-md transition-colors"
          :class="route.name === 'music'
            ? 'text-c-accent bg-c-accent-soft'
            : 'bg-transparent text-c-text-dim hover:bg-white/4'"
        >
          音乐制作
        </button>
        <button
          @click="goTo('meme-review')"
          class="px-3 py-1.5 text-xs rounded-md transition-colors"
          :class="route.name === 'meme-review'
            ? 'text-c-accent bg-c-accent-soft'
            : 'bg-transparent text-c-text-dim hover:bg-white/4'"
        >
          梗筛选
        </button>
        <button
          @click="goTo('dashboard')"
          class="px-3 py-1.5 text-xs rounded-md transition-colors"
          :class="route.name === 'dashboard'
            ? 'text-c-accent bg-c-accent-soft'
            : 'bg-transparent text-c-text-dim hover:bg-white/4'"
        >
          {{ route.name === 'dashboard' ? 'Chat' : 'Dashboard' }}
        </button>
      </div>
    </div>
  </div>
</template>
