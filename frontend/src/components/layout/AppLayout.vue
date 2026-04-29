<script setup lang="ts">
import { ref } from 'vue'
import Live2DRenderer from '@/components/live2d/Live2DRenderer.vue'
import PopOutButton from '@/components/live2d/PopOutButton.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'

const live2dPopout = ref(false)

function handlePopout(): void {
  // In single-window mode, just toggle visibility.
  // For actual popout, we'd need IPC to create a new BrowserWindow.
  // This is handled via the main process.
  live2dPopout.value = true
}

function handlePopoutClosed(): void {
  live2dPopout.value = false
}
</script>

<template>
  <div class="flex flex-1 overflow-hidden">
    <!-- Live2D area (hidden when popped out) -->
    <div
      v-if="!live2dPopout"
      class="w-1/2 min-w-0 relative"
    >
      <Live2DRenderer />
      <PopOutButton @popout="handlePopout" />
    </div>

    <!-- When popped out, show a compact indicator -->
    <div
      v-if="live2dPopout"
      class="w-12 flex flex-col items-center pt-4 border-r border-$c-border bg-$c-bg"
    >
      <button
        class="btn-ghost text-xs flex flex-col items-center gap-1 py-2"
        @click="handlePopoutClosed"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        <span class="text-10px">收回</span>
      </button>
    </div>

    <!-- Chat panel -->
    <ChatPanel :class="live2dPopout ? 'flex-1' : 'w-1/2'" />
  </div>
</template>
