<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as PIXI from 'pixi.js'
import type { Live2DRenderer } from '@/shared/live2d/renderer'
import type { Live2DModelProfile } from './modelProfile'
import { DEFAULT_LIVE2D_MODEL_PROFILE } from './modelProfiles'

defineOptions({ name: 'Live2DCompanion' })
const props = defineProps<{ profile?: Live2DModelProfile }>()

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
    profile: props.profile ?? DEFAULT_LIVE2D_MODEL_PROFILE,
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
  <div ref="container" class="isolate overflow-hidden" aria-label="Animetta Live2D 伙伴">
    <canvas ref="canvas" class="block w-full h-full" aria-hidden="true" />
    <span
      :data-state="status"
      class="absolute inset-x-3 bottom-3 rounded-xl border border-c-border bg-c-panel/95 px-3 py-2 text-center text-xs text-c-text-dim data-[state=live]:hidden"
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
