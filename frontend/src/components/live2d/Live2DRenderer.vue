<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLive2D } from './useLive2D'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const live2d = useLive2D(canvasRef)

onMounted(async () => {
  live2d.init()

  // Try loading default model
  try {
    const fallbackPath = 'live2d/haru/haru_greeter_t03.model3.json'
    const modelPath = (await window.electronAPI?.getConfig?.('model.defaultPath')) || fallbackPath
    await live2d.loadModel(modelPath)
  } catch {
    // Model not found is OK, user can load one later
  }
})
</script>

<template>
  <div class="relative w-full h-full">
    <canvas ref="canvasRef" class="w-full h-full" />

    <!-- Loading state -->
    <div
      v-if="live2d.isLoading.value"
      class="absolute inset-0 flex items-center justify-center"
    >
      <div class="glass px-6 py-3 text-sm text-$c-text-dim flex items-center gap-2">
        <span class="animate-pulse">Loading Live2D...</span>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="live2d.loadError.value"
      class="absolute inset-0 flex items-center justify-center"
    >
      <div class="glass px-6 py-3 text-sm text-$c-error">
        Failed to load model
      </div>
    </div>

    <!-- Idle state (no model) -->
    <div
      v-if="!live2d.isLoaded.value && !live2d.isLoading.value && !live2d.loadError.value"
      class="absolute inset-0 flex items-center justify-center"
    >
      <div class="text-center text-$c-text-muted">
        <p class="text-2xl mb-2">🎭</p>
        <p class="text-sm">No Live2D model loaded</p>
      </div>
    </div>
  </div>
</template>
