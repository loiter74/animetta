<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getSocket } from '@/composables/useSocket'
import BackgroundSettings from './BackgroundSettings.vue'

function resetLive2dView(): void {
  if (typeof window.__live2dResetView === 'function') {
    window.__live2dResetView()
  }
}

interface ServiceInfo {
  name: string
  value: string
}

interface ConfigData {
  persona: string
  services: Record<string, string>
  active_services: Record<string, string | null>
  system: { host: string; port: number; log_level: string }
  live2d: { model_path: string; enabled: boolean }
  available_personas: string[]
}

const services = ref<ServiceInfo[]>([])
const personaName = ref('')
const modelInfo = ref('')
const backendInfo = ref('')
const loading = ref(true)
const error = ref('')
const activeSection = ref<'status' | 'background' | 'controls'>('status')

let cleanup: (() => void) | null = null

onMounted(() => {
  const socket = getSocket()
  if (!socket) {
    loading.value = false
    error.value = '未连接后端'
    return
  }

  const handler = (data: ConfigData) => {
    services.value = [
      { name: 'ASR 语音识别', value: data.active_services.asr || data.services.asr || '-' },
      { name: 'TTS 语音合成', value: data.active_services.tts || data.services.tts || '-' },
      { name: 'LLM 语言模型', value: data.active_services.llm || data.services.agent || '-' },
      { name: 'VAD 语音检测', value: data.active_services.vad || data.services.vad || '-' },
    ]
    personaName.value = data.persona || 'neuro-vtuber'
    const modelPath = data.live2d?.model_path || ''
    modelInfo.value = modelPath ? modelPath.split('/').pop() || modelPath : '默认'
    backendInfo.value = `${data.system?.host || 'localhost'}:${data.system?.port || 12394}`
    loading.value = false
  }

  socket.on('config_data', handler)
  cleanup = () => socket.off('config_data', handler)
  socket.emit('get_config', {})
})

onUnmounted(() => {
  cleanup?.()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Section tabs -->
    <div class="flex gap-1 px-3 pt-3 pb-2 border-b border-c-border/40 shrink-0">
      <button
        class="px-2.5 py-1 rounded-lg text-10px font-medium transition-all"
        :class="activeSection === 'status' ? 'bg-c-accent/20 text-c-accent' : 'bg-c-bg/40 text-c-text-dim hover:text-c-text'"
        @click="activeSection = 'status'"
      >📊 状态</button>
      <button
        class="px-2.5 py-1 rounded-lg text-10px font-medium transition-all"
        :class="activeSection === 'background' ? 'bg-c-accent/20 text-c-accent' : 'bg-c-bg/40 text-c-text-dim hover:text-c-text'"
        @click="activeSection = 'background'"
      >🖼️ 背景</button>
      <button
        class="px-2.5 py-1 rounded-lg text-10px font-medium transition-all"
        :class="activeSection === 'controls' ? 'bg-c-accent/20 text-c-accent' : 'bg-c-bg/40 text-c-text-dim hover:text-c-text'"
        @click="activeSection = 'controls'"
      >🎮 控制</button>
    </div>

    <!-- Status section -->
    <div v-if="activeSection === 'status'" class="flex-1 overflow-y-auto px-4 py-3">
      <div v-if="loading" class="flex items-center justify-center py-8">
        <span class="text-sm text-c-text-dim animate-pulse">加载配置...</span>
      </div>
      <div v-else-if="error" class="flex items-center justify-center py-8">
        <span class="text-sm text-c-error">{{ error }}</span>
      </div>
      <template v-else>
        <div class="mb-5">
          <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">角色</h3>
          <div class="bg-c-card/50 rounded-xl px-3 py-2.5 flex items-center gap-2">
            <span class="text-sm">🎭</span>
            <span class="text-sm text-c-text">{{ personaName }}</span>
          </div>
        </div>
        <div class="mb-5">
          <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">Live2D 模型</h3>
          <div class="bg-c-card/50 rounded-xl px-3 py-2.5 flex items-center gap-2">
            <span class="text-sm">✨</span>
            <span class="text-sm text-c-text truncate" :title="modelInfo">{{ modelInfo }}</span>
          </div>
        </div>
        <div class="mb-4">
          <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">服务配置</h3>
          <div class="space-y-1.5">
            <div v-for="svc in services" :key="svc.name" class="bg-c-card/50 rounded-xl px-3 py-2 flex items-center justify-between">
              <span class="text-xs text-c-text-dim">{{ svc.name }}</span>
              <span class="text-xs text-c-accent font-medium">{{ svc.value }}</span>
            </div>
          </div>
        </div>
        <div class="mb-4">
          <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">后端</h3>
          <div class="bg-c-card/50 rounded-xl px-3 py-2 flex items-center gap-2">
            <span class="text-xs">🖥️</span>
            <span class="text-xs text-c-text-dim">{{ backendInfo }}</span>
          </div>
        </div>
        <div class="pt-4 border-t border-c-border/40">
          <p class="text-10px text-c-text-muted text-center">配置通过 config.yaml 管理 · 重启后生效</p>
        </div>
      </template>
    </div>

    <!-- Background section -->
    <div v-if="activeSection === 'background'" class="flex-1 overflow-y-auto px-4 py-3">
      <BackgroundSettings />
    </div>

    <!-- Controls section -->
    <div v-if="activeSection === 'controls'" class="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">Live2D</h3>
      <button
        class="w-full px-3 py-2.5 rounded-xl bg-c-card/50 text-xs text-c-text hover:bg-c-card transition-colors flex items-center gap-2"
        @click="resetLive2dView()"
      >
        <span>🔄</span>
        <span>重置视图</span>
      </button>
      <p class="text-10px text-c-text-muted">将 Live2D 模型缩放重置为 1x 并居中</p>
    </div>
  </div>
</template>

<style scoped>
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
</style>
