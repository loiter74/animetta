<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as PIXI from 'pixi.js'
import type { Live2DStage } from '@/review/live2d-stage'
import type { LiveSocket } from '@/shared/transport/liveSocket'

const container = ref<HTMLElement>()
let stage: Live2DStage | undefined
let disposed = false
// This visual prototype reuses the live renderer without subscribing to the backend.
const socket: LiveSocket = {
  on() {
    return this
  },
  off() {
    return this
  },
}

onMounted(async () => {
  window.PIXI = PIXI
  const { createLive2DStage } = await import('@/review/live2d-stage')
  if (disposed || !container.value) return
  stage = createLive2DStage(socket, { resizeTo: container.value, idleVitality: true })
})

onBeforeUnmount(() => {
  disposed = true
  stage?.dispose()
})
</script>

<template>
  <div ref="container" aria-label="Animetta Live2D 伙伴" data-testid="earth-companion">
    <canvas id="live2dCanvas" class="block w-full h-full" aria-hidden="true" />
    <span
      id="modelStatus"
      data-state="connecting"
      class="absolute bottom-0 right-0 text-xs text-c-text-dim bg-c-panel/85 rounded-xl px-3 py-2 data-[state=live]:hidden"
      role="status"
      >Live2D 加载中</span
    >
  </div>
</template>
