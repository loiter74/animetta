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

function toggleDashboard() {
  if (route.name === 'dashboard') {
    router.push('/')
  } else {
    router.push('/dashboard')
  }
}
</script>

<template>
  <div class="relative flex items-center justify-between h-9 select-none z-40">
    <div class="absolute inset-0 bg-c-bg/80 backdrop-blur-2xl" />
    <div class="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-c-accent/20 to-transparent" />

    <div class="relative flex items-center justify-between w-full">
      <div class="flex-1 flex items-center pl-4">
        <span class="text-sm font-medium text-c-text tracking-wide">Anima</span>
        <div class="flex items-center gap-2 ml-4">
          <span class="w-2 h-2 rounded-full" :class="statusColors[store.status]" />
          <span class="text-xs text-c-text-dim">{{ statusLabels[store.status] }}</span>
        </div>
      </div>

      <div class="flex items-center pr-4 gap-2">
        <button
          @click="toggleDashboard"
          class="px-3 py-1 text-xs rounded-lg transition-colors"
          :class="route.name === 'dashboard'
            ? 'bg-c-accent text-white'
            : 'bg-white/10 text-c-text-dim hover:bg-white/20'"
        >
          {{ route.name === 'dashboard' ? 'Chat' : 'Dashboard' }}
        </button>
      </div>
    </div>
  </div>
</template>
