<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePersonalityStore } from '@/stores/personality'

const store = usePersonalityStore()

const collapsed = ref(false)
const selectedPersona = ref('')

watch(() => store.availablePersonas, (personas) => {
  if (personas.length > 0 && !selectedPersona.value) {
    selectedPersona.value = personas[0]
  }
}, { immediate: true })

function applyPersona(): void {
  if (selectedPersona.value) {
    store.setPersona(selectedPersona.value)
  }
}

function toggleMode(): void {
  store.setMode(store.currentMode === 'default' ? 'streaming' : 'default')
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center gap-1.5 px-3 py-1.5 border-b border-c-border/60 shrink-0">
      <span class="text-sm">🎭</span>
      <span class="text-sm font-medium text-c-text">人格配置</span>
      <div class="flex-1" />
      <button
        class="w-7 h-7 flex items-center justify-center rounded-lg bg-c-bg/40 text-c-text-dim hover:text-c-text hover:bg-c-bg/60 transition-colors"
        @click="collapsed = !collapsed"
      >
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
          :class="collapsed ? '' : 'rotate-180'"
          class="transition-transform"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
    </div>

    <div v-show="!collapsed" class="flex-1 overflow-y-auto px-4 py-3 space-y-4">
      <!-- Current mode badge -->
      <div>
        <label class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2 block">当前模式</label>
        <span
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium"
          :class="store.currentMode === 'streaming'
            ? 'bg-c-accent/20 text-c-accent'
            : 'bg-c-card/50 text-c-text-dim'"
        >
          {{ store.currentMode === 'streaming' ? '流式' : '默认' }}
        </span>
      </div>

      <!-- Persona switcher -->
      <div>
        <label class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2 block">角色人设</label>
        <select
          v-model="selectedPersona"
          class="w-full px-3 py-2 rounded-xl bg-c-bg/60 border border-c-border/40 text-sm text-c-text
                 focus:outline-none focus:border-c-accent/50 transition-colors appearance-none cursor-pointer"
        >
          <option value="" disabled>选择人设...</option>
          <option v-for="p in store.availablePersonas" :key="p" :value="p">{{ p }}</option>
        </select>
        <button
          class="mt-2 w-full px-3 py-2 rounded-xl text-xs font-medium transition-all
                 bg-c-accent/15 text-c-accent hover:bg-c-accent/25
                 flex items-center justify-center gap-1.5"
          @click="applyPersona"
        >
          应用
        </button>
      </div>

      <!-- Streaming mode toggle -->
      <div>
        <label class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2 block">流式模式</label>
        <div class="flex items-center justify-between bg-c-card/50 rounded-xl px-3 py-2.5">
          <span class="text-xs text-c-text">{{ store.currentMode === 'streaming' ? '已开启' : '已关闭' }}</span>
          <button
            class="w-10 h-5 rounded-full transition-colors relative shrink-0"
            :class="store.currentMode === 'streaming' ? 'bg-c-accent' : 'bg-c-bg/60 border border-c-border/40'"
            @click="toggleMode"
          >
            <span
              class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200"
              :class="store.currentMode === 'streaming' ? 'translate-x-[22px]' : 'translate-x-[2px]'"
            />
          </button>
        </div>
      </div>

      <!-- Memory influence slider -->
      <div>
        <label class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2 block">记忆影响度</label>
        <div class="bg-c-card/50 rounded-xl px-3 py-2.5">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs text-c-text-dim">影响权重</span>
            <span class="text-xs text-c-accent font-medium tabular-nums">{{ store.memoryInfluence.toFixed(1) }}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            :value="store.memoryInfluence"
            class="range-slider w-full"
            @input="store.setMemoryInfluence(Number(($event.target as HTMLInputElement).value))"
          />
          <div class="flex justify-between text-10px text-c-text-muted mt-1">
            <span>最小</span>
            <span>最大</span>
          </div>
        </div>
      </div>

      <!-- Current mood -->
      <div>
        <label class="text-xs font-medium text-c-text-dim uppercase tracking-wider mb-2 block">当前情绪</label>
        <div class="bg-c-card/50 rounded-xl px-3 py-2.5 flex items-center gap-2">
          <span class="text-sm">💭</span>
          <span v-if="store.currentMood" class="text-sm text-c-text capitalize">{{ store.currentMood }}</span>
          <span v-else class="text-sm text-c-text-muted">暂无检测数据</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.range-slider {
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  outline: none;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(168, 130, 255, 1); /* TODO: add token — no matching violet token in uno.config.ts */
  box-shadow: 0 0 8px rgba(168, 130, 255, 0.5); /* TODO: add token */
  transition: box-shadow 0.2s;
}

.range-slider::-webkit-slider-thumb:hover {
  box-shadow: 0 0 12px rgba(168, 130, 255, 0.7); /* TODO: add token */
}

.range-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: rgba(168, 130, 255, 1); /* TODO: add token */
  border: none;
  box-shadow: 0 0 8px rgba(168, 130, 255, 0.5); /* TODO: add token */
}

.range-slider::-moz-range-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
}
</style>
