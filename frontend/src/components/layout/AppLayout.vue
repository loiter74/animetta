<script setup lang="ts">
import { ref } from 'vue'
import Live2DRenderer from '@/components/live2d/Live2DRenderer.vue'
import SceneEffects from '@/components/shared/SceneEffects.vue'
import InteractivePanel from '@/components/layout/InteractivePanel.vue'

const live2dPopout = ref(false)

function handlePopout(): void {
  live2dPopout.value = true
}

function handlePopoutClosed(): void {
  live2dPopout.value = false
}
</script>

<template>
  <div class="flex-1 relative overflow-hidden">
    <!-- Layer 0: Live2D Scene (full viewport) -->
    <div
      v-if="!live2dPopout"
      class="absolute inset-0 z-0"
    >
      <Live2DRenderer />
    </div>

    <!-- Layer 1: Scene Effects (particles, glows) -->
    <SceneEffects v-if="!live2dPopout" class="z-10" />

    <!-- Layer 2: Interactive Panel (floating right side) -->
    <InteractivePanel
      :class="live2dPopout ? 'w-full' : ''"
      @popout="handlePopout"
      @popout-closed="handlePopoutClosed"
      :live2d-popout="live2dPopout"
    />
  </div>
</template>
