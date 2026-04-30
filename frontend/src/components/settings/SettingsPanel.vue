<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getSocket } from '@/composables/useSocket'

interface ServiceInfo {
  name: string
  value: string
}

const services = ref<ServiceInfo[]>([
  { name: 'ASR 语音识别', value: '-' },
  { name: 'TTS 语音合成', value: '-' },
  { name: 'LLM 语言模型', value: '-' },
  { name: 'VAD 语音检测', value: '-' },
])
const personaName = ref('neuro-vtuber')
const modelInfo = ref('haru (默认)')
const loading = ref(true)

onMounted(async () => {
  // In browser mode, config is managed server-side via YAML
  // These are display-only defaults
  loading.value = false
})
</script>

<template>
  <div class="flex flex-col h-full overflow-y-auto px-4 py-3">
    <div v-if="loading" class="flex items-center justify-center py-8">
      <span class="text-sm text-c-text-dim animate-pulse">加载配置...</span>
    </div>

    <template v-else>
      <!-- Persona section -->
      <div class="mb-5">
        <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">角色</h3>
        <div class="bg-c-card/50 rounded-xl px-3 py-2.5 flex items-center gap-2">
          <span class="text-sm">🎭</span>
          <span class="text-sm text-c-text">{{ personaName }}</span>
        </div>
      </div>

      <!-- Live2D Model section -->
      <div class="mb-5">
        <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">Live2D 模型</h3>
        <div class="bg-c-card/50 rounded-xl px-3 py-2.5 flex items-center gap-2">
          <span class="text-sm">✨</span>
          <span class="text-sm text-c-text">{{ modelInfo }}</span>
        </div>
      </div>

      <!-- Services section -->
      <div class="mb-4">
        <h3 class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2">服务配置</h3>
        <div class="space-y-1.5">
          <div
            v-for="svc in services"
            :key="svc.name"
            class="bg-c-card/50 rounded-xl px-3 py-2 flex items-center justify-between"
          >
            <span class="text-xs text-c-text-dim">{{ svc.name }}</span>
            <span class="text-xs text-c-accent font-medium">{{ svc.value }}</span>
          </div>
        </div>
      </div>

      <!-- Footer note -->
      <div class="mt-auto pt-4 border-t border-c-border/40">
        <p class="text-10px text-c-text-muted text-center">
          配置通过 config.yaml 管理 · 重启后生效
        </p>
      </div>
    </template>
  </div>
</template>

<style scoped>
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
</style>
