<script setup lang="ts">
import { computed } from 'vue'
import { useModelLoadingStore } from '@/stores/modelLoading'

const store = useModelLoadingStore()

const hasModels = computed(() => store.models.size > 0)

/** Friendly label for each model name */
const modelLabel = (name: string) => {
  const labels: Record<string, string> = {
    asr: '语音识别',
    tts: '语音合成',
    llm: '语言模型',
    vad: '语音检测',
  }
  return labels[name] ?? name
}
</script>

<template>
  <Transition name="overlay">
    <div
      v-if="store.isLoading || (!store.isLoading && hasModels && store.progress < 1)"
      class="fixed inset-0 z-50 flex flex-col items-center justify-center select-none"
    >
      <!-- Background image -->
      <div
        class="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style="background-image: url('/loading/loading.png')"
      />

      <!-- Dark overlay -->
      <div class="absolute inset-0 bg-c-bg/60 backdrop-blur-sm" />

      <!-- Content -->
      <div class="relative flex flex-col items-center gap-8">
        <!-- Title -->
        <div class="text-center">
          <h1 class="text-3xl font-bold text-c-text tracking-wider">
            Anima
          </h1>
          <p class="mt-2 text-c-text-dim text-sm">
            {{ store.summary || '正在启动...' }}
          </p>
        </div>

        <!-- Model status cards -->
        <div class="flex flex-wrap justify-center gap-3 max-w-md">
          <div
            v-for="[name, model] in store.models"
            :key="name"
            class="glass px-5 py-3 flex items-center gap-3 min-w-[150px]"
            :class="{
              'border-c-accent/50': model.status === 'loading',
              'border-c-success/50': model.status === 'loaded',
              'border-c-error/50': model.status === 'error',
            }"
          >
            <!-- Status icon -->
            <div class="w-5 h-5 flex-shrink-0 flex items-center justify-center">
              <!-- Loading spinner -->
              <div
                v-if="model.status === 'loading'"
                class="w-4 h-4 border-2 border-c-accent border-t-transparent rounded-full animate-spin"
              />
              <!-- Loaded checkmark -->
              <svg
                v-else-if="model.status === 'loaded'"
                class="w-5 h-5 text-c-success"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clip-rule="evenodd"
                />
              </svg>
              <!-- Error icon -->
              <svg
                v-else
                class="w-5 h-5 text-c-error"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
            </div>

            <!-- Label -->
            <span
              class="text-sm font-medium"
              :class="{
                'text-c-text': model.status === 'loading',
                'text-c-success': model.status === 'loaded',
                'text-c-error': model.status === 'error',
              }"
            >
              {{ modelLabel(name) }}
            </span>
          </div>
        </div>

        <!-- Progress bar -->
        <div class="w-64">
          <div class="h-1.5 bg-c-surface rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500 ease-out"
              :class="store.progress >= 1 ? 'bg-c-success' : 'bg-gradient-to-r from-c-accent to-c-blue'"
              :style="{ width: `${Math.round(store.progress * 100)}%` }"
            />
          </div>
          <p class="mt-1.5 text-center text-xs text-c-text-muted">
            {{ Math.round(store.progress * 100) }}%
          </p>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.overlay-enter-active {
  transition: opacity 0.5s ease;
}
.overlay-leave-active {
  transition: opacity 0.6s ease;
}
.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}
</style>
