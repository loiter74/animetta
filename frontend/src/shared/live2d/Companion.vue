<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as PIXI from 'pixi.js'
import type { Live2DRenderer } from '@/shared/live2d/renderer'

defineOptions({ name: 'Live2DCompanion' })

const container = ref<HTMLElement>()
const canvas = ref<HTMLCanvasElement>()
const status = ref<'connecting' | 'live' | 'error'>('connecting')
let stage: Live2DRenderer | undefined
let disposed = false

defineExpose({ setMouth: (value: number, taskId?: string) => stage?.setMouth(value, taskId) })

onMounted(async () => {
  window.PIXI = PIXI
  const { createLive2DRenderer } = await import('@/shared/live2d/renderer')
  if (disposed || !container.value || !canvas.value) return
  stage = createLive2DRenderer({
    canvas: canvas.value,
    resizeTo: container.value,
    idleVitality: true,
    onState: (value) => {
      status.value = value
    },
  })
})

onBeforeUnmount(() => {
  disposed = true
  stage?.dispose()
})
</script>

<template>
  <div ref="container" aria-label="Animetta Live2D 伙伴">
    <canvas ref="canvas" class="block w-full h-full" aria-hidden="true" />
    <span
      :data-state="status"
      class="absolute bottom-0 right-0 text-xs text-c-text-dim bg-c-panel/85 rounded-xl px-3 py-2 data-[state=live]:hidden"
      role="status"
      >{{
        status === 'error'
          ? 'Live2D 加载失败'
          : status === 'live'
            ? 'Live2D 已加载'
            : 'Live2D 加载中'
      }}</span
    >
  </div>
</template>
