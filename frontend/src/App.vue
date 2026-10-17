<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ensureAuthenticatedSession, useSocket } from '@/composables/useSocket'
import { useConnectionStore } from '@/stores/connection'

useSocket() // Initialize Socket.IO connection
const connectionStore = useConnectionStore()
const route = useRoute()
const router = useRouter()

const STORAGE_KEY = 'animetta_background'
const bgSrc = ref('')
const authRequired = computed(
  () =>
    connectionStore.authStatus === 'unauthenticated' ||
    connectionStore.authStatus === 'unavailable',
)
const username = ref('admin')
const password = ref('')
const authError = ref('')
const authBusy = ref(false)

const bgStyle = computed(() => {
  if (!bgSrc.value) return {}
  return {
    backgroundImage: 'url("' + bgSrc.value.replace(/"/g, '%22') + '")',
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
  }
})

onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) bgSrc.value = saved
})

watch(
  () => [connectionStore.authStatus, connectionStore.passwordChangeRequired, route.path] as const,
  ([status, passwordChangeRequired, path]) => {
    if (status === 'authenticated' && passwordChangeRequired && path !== '/account') {
      void router.replace('/account')
    }
  },
  { immediate: true },
)

async function login(): Promise<void> {
  authBusy.value = true
  authError.value = ''
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    })
    if (!response.ok) {
      connectionStore.setAuthStatus(response.status === 503 ? 'unavailable' : 'unauthenticated')
      authError.value =
        response.status === 429
          ? '尝试过于频繁，请稍后再试。'
          : response.status === 403
            ? '账号已被禁用。'
            : response.status === 503
              ? '登录服务不可用。'
              : '用户名或密码错误。'
      return
    }
    const status = await ensureAuthenticatedSession()
    if (status !== 'authenticated') {
      authError.value = status === 'unavailable' ? '登录服务不可用。' : '登录会话无效。'
    }
  } catch {
    connectionStore.setAuthStatus('unavailable')
    authError.value = '登录服务不可用。'
  } finally {
    password.value = ''
    authBusy.value = false
  }
}

window.__setAppBg = (url: string) => {
  bgSrc.value = url
}
</script>

<template>
  <div class="relative flex h-[100dvh] w-full min-w-0 flex-col overflow-hidden text-c-text">
    <!-- Background layer: lives at z-index 0 so the global preset image shows
         through the transparent .app-container / .stage. The root div carries
         no bg-c-bg itself — the body element keeps --c-bg as the ultimate
         fallback if the user clears the background. -->
    <div v-if="bgSrc" class="pointer-events-none absolute inset-0 z-0" :style="bgStyle" />
    <div class="relative z-1 flex h-full min-h-0 flex-col">
      <router-view />
    </div>
    <div
      v-if="authRequired"
      class="absolute inset-0 z-50 grid overflow-y-auto bg-c-bg/95 px-5 py-8 backdrop-blur-xl sm:px-8"
      data-testid="auth-gate"
    >
      <div
        class="m-auto grid w-full max-w-5xl items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] lg:gap-20"
      >
        <section class="hidden min-w-0 lg:block" aria-label="Anima 工作空间">
          <p class="text-base font-semibold tracking-tight">
            Anima<span class="text-c-accent">.</span>
          </p>
          <p class="mt-8 max-w-sm text-4xl font-semibold leading-tight tracking-tight">
            你的直播<br />工作空间
          </p>
          <p class="mt-5 max-w-sm text-sm leading-7 text-c-text-dim">
            从角色、节目到每一次对话，在这里整理并掌控直播现场。
          </p>
          <div
            class="mt-10 grid max-w-sm gap-4 border-t border-c-border pt-6 text-xs text-c-text-muted"
          >
            <p>现场 · 监看直播与执行</p>
            <p>创作 · 编排节目与内容</p>
            <p>验证 · 私密演练与角色调试</p>
          </div>
        </section>
        <form
          class="w-full rounded-xl border border-c-border bg-c-panel p-6 shadow-panel sm:p-8"
          @submit.prevent="login"
        >
          <p class="mb-6 text-sm font-semibold text-c-accent">Anima · 后台登录</p>
          <h1 class="mt-2 text-xl font-semibold">
            {{ connectionStore.authStatus === 'unavailable' ? '登录服务不可用' : '未登录' }}
          </h1>
          <p class="mt-2 text-sm leading-6 text-c-text-dim">
            使用账号登录后台，会话将在 8 小时后到期。
          </p>
          <label class="mt-5 block text-xs text-c-text-dim" for="auth-username">用户名</label>
          <input
            id="auth-username"
            v-model="username"
            class="input-field mt-2 w-full"
            type="text"
            name="username"
            autocomplete="username"
            required
          />
          <label class="mt-4 block text-xs text-c-text-dim" for="auth-password">密码</label>
          <input
            id="auth-password"
            v-model="password"
            class="input-field mt-2 w-full"
            type="password"
            name="password"
            autocomplete="current-password"
            required
          />
          <p v-if="authError" class="mt-3 text-xs text-c-error" role="alert">{{ authError }}</p>
          <button class="btn-accent mt-5 w-full" type="submit" :disabled="authBusy">
            {{ authBusy ? '验证中…' : '登录' }}
          </button>
          <a href="/live.html" class="btn-ghost mt-3 w-full no-underline">前往直播画面</a>
        </form>
      </div>
    </div>
  </div>
</template>
