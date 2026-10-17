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
    class="titlebar relative z-40 flex shrink-0 flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-c-border bg-c-surface/95 px-4 py-3 backdrop-blur-lg select-none sm:px-6 lg:px-8"
  >
    <a
      href="/dashboard"
      class="titlebar-left brand flex shrink-0 items-center gap-2.5 rounded-xl no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-c-accent"
      aria-label="Anima 后台首页"
    >
      <span
        class="grid h-9 w-9 place-items-center rounded-xl bg-c-accent-soft text-lg font-semibold text-c-accent"
        aria-hidden="true"
        >a.</span
      >
      <span class="text-base font-semibold tracking-tight text-c-text"
        >Anima<span class="brand-dot text-c-accent">.</span></span
      >
    </a>
    <nav
      class="titlebar-nav order-3 grid w-full grid-cols-3 items-center gap-1 rounded-xl bg-c-bg/80 p-1 md:order-none md:ml-2 md:flex md:w-auto lg:ml-6"
      aria-label="Main sections"
    >
      <a
        v-for="item in navItems"
        :key="item.key"
        :data-testid="`nav-${item.key}`"
        :href="item.path"
        :aria-current="isActive(item) ? 'page' : undefined"
        class="nav-btn btn-ghost min-h-8 px-3 no-underline"
        :class="isActive(item) ? 'active bg-c-panel text-c-accent shadow-control' : ''"
      >
        {{ item.label }}
      </a>
    </nav>

    <div class="titlebar-right ml-auto flex shrink-0">
      <div
        class="status-indicator flex items-center gap-2 rounded-xl border border-c-border bg-c-bg/50 px-3 py-2 text-xs text-c-text-dim"
        role="status"
      >
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
