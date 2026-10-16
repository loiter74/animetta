<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { useConnectionStore } from '@/stores/connection'

const route = useRoute()
const store = useConnectionStore()

const statusColors: Record<string, string> = {
  checking: 'bg-c-warning animate-pulse',
  unauthenticated: 'bg-c-warning',
  unavailable: 'bg-c-error',
  'password-required': 'bg-c-warning',
  connected: 'bg-c-success',
  disconnected: 'bg-c-error',
  connecting: 'bg-c-warning animate-pulse',
  error: 'bg-c-error',
}

const statusLabels: Record<string, string> = {
  checking: '正在检查登录状态',
  unauthenticated: '未登录',
  unavailable: '登录服务不可用',
  'password-required': '需修改密码',
  connected: '服务已连接',
  disconnected: '服务已断开',
  connecting: '服务连接中',
  error: '服务连接异常',
}

const displayStatus = computed(() => {
  if (store.authStatus !== 'authenticated') return store.authStatus
  return store.passwordChangeRequired ? 'password-required' : store.status
})

const navItems = [
  { key: 'live', label: '直播画面', path: '/live.html' },
  { key: 'dashboard', label: '后台控制', routeName: 'dashboard', path: '/dashboard' },
  { key: 'account', label: '账号', routeName: 'account', path: '/account' },
] as const

function isActive(item: (typeof navItems)[number]) {
  return 'routeName' in item && route.name === item.routeName
}
</script>

<template>
  <header
    class="titlebar relative z-40 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-c-border bg-c-surface/95 px-4 backdrop-blur-lg select-none sm:px-6"
  >
    <!-- Left: brand + primary nav grouped together -->
    <div class="titlebar-left flex min-w-0 items-center gap-4 sm:gap-8">
      <div class="brand shrink-0 text-lg font-semibold tracking-tight">
        Anima<span class="brand-dot text-c-accent">.</span>
      </div>
      <nav class="titlebar-nav flex items-center gap-1" aria-label="Main sections">
        <a
          v-for="item in navItems"
          :key="item.key"
          :data-testid="`nav-${item.key}`"
          :href="item.path"
          :aria-current="isActive(item) ? 'page' : undefined"
          class="nav-btn btn-ghost min-h-8 px-2.5 no-underline sm:px-3"
          :class="isActive(item) ? 'active bg-c-accent-soft text-c-accent' : ''"
        >
          {{ item.label }}
        </a>
      </nav>
    </div>

    <!-- Right: connection status -->
    <div class="titlebar-right hidden shrink-0 sm:flex">
      <div class="status-indicator flex items-center gap-2 text-xs text-c-text-dim" role="status">
        <span
          class="status-dot h-1.5 w-1.5 shrink-0 rounded-full"
          :class="statusColors[displayStatus]"
          aria-hidden="true"
        ></span>
        <span class="status-text">{{ statusLabels[displayStatus] }}</span>
      </div>
    </div>
  </header>
</template>
