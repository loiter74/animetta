<script setup lang="ts">
import { ref } from 'vue'

defineEmits<{
  popout: []
}>()

const showHint = ref(false)
</script>

<template>
  <div class="absolute top-3 right-3 z-10 flex gap-2">
    <button
      class="btn-ghost text-xs flex items-center gap-1.5"
      @mouseenter="showHint = true"
      @mouseleave="showHint = false"
      @click="$emit('popout')"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
      </svg>
      <span>Pop Out</span>
    </button>

    <!-- Zoom controls -->
    <div class="flex gap-1">
      <button class="btn-ghost text-xs w-8 h-8 flex items-center justify-center" title="Zoom In">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
      <button class="btn-ghost text-xs w-8 h-8 flex items-center justify-center" title="Zoom Out">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    </div>
  </div>
</template>
