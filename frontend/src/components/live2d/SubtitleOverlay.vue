<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSubtitle } from '@/composables/useSubtitle'
import { useSubtitleStore } from '@/stores/subtitle'

const {
  store,
  text,
  translation,
  visible,
  isStreaming,
} = useSubtitle()

const subStore = useSubtitleStore()

// ===== Font sizes (2-3x larger) =====
const fontSizeMap: Record<string, string> = {
  small: '1.5rem',
  medium: '2rem',
  large: '2.5rem',
}
const translationFontSizeMap: Record<string, string> = {
  small: '1.2rem',
  medium: '1.5rem',
  large: '1.8rem',
}

const fontSizeStyle = computed(() => ({ fontSize: fontSizeMap[store.fontSize] }))
const translationFontSizeStyle = computed(() => ({ fontSize: translationFontSizeMap[store.fontSize] }))

const showOriginal = computed(() =>
  store.displayMode === 'original' || store.displayMode === 'bilingual'
)

const showTranslation = computed(() =>
  (store.displayMode === 'translated' || store.displayMode === 'bilingual')
  && translation.value
)

// ===== Drag support =====
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragOriginX = ref(0)
const dragOriginY = ref(0)
const panelRef = ref<HTMLDivElement | null>(null)

/** Convert stored position to CSS style or null for default centered */
const PANEL_OFFSET = 200  // shift left by ~half of chat panel width to center in Live2D area

const hasCustomPosition = computed(() =>
  store.posX != null && store.posY != null
  && typeof store.posX === 'number'
  && typeof store.posY === 'number'
)

const positionStyle = computed(() => {
  if (hasCustomPosition.value) {
    return {
      left: `${store.posX}px`,
      bottom: `${store.posY}px`,
      transform: 'none',
      maxWidth: '80vw',
    }
  }
  // Default: centered in Live2D area (accounting for right-side chat panel)
  return {
    left: `calc(50% - ${PANEL_OFFSET}px)`,
    transform: 'translateX(-50%)',
    maxWidth: '80vw',
  }
})

function onDragStart(e: MouseEvent): void {
  // Only left-click
  if (e.button !== 0) return
  isDragging.value = true
  dragStartX.value = e.clientX
  dragStartY.value = e.clientY
  dragOriginX.value = store.posX !== null ? store.posX : 0
  dragOriginY.value = store.posY !== null ? store.posY : 0

  // If at default position, compute current left/bottom from DOM
  if (!hasCustomPosition.value && panelRef.value) {
    const rect = panelRef.value.getBoundingClientRect()
    const parentRect = panelRef.value.offsetParent?.getBoundingClientRect()
    if (parentRect) {
      dragOriginX.value = rect.left - parentRect.left
      dragOriginY.value = parentRect.bottom - rect.bottom
    }
  }

  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent): void {
  if (!isDragging.value) return
  const dx = e.clientX - dragStartX.value
  const dy = e.clientY - dragStartY.value
  const newX = Math.max(0, dragOriginX.value + dx)
  const newY = Math.max(0, dragOriginY.value - dy) // inverted: bottom Y
  subStore.setPosition(newX, newY)
}

function onDragEnd(): void {
  isDragging.value = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}
</script>

<template>
  <Transition name="subtitle">
    <div
      v-if="visible && text && store.enabled"
      class="absolute z-40"
      :class="!hasCustomPosition ? 'bottom-4' : ''"
      :style="positionStyle"
    >
      <div
        ref="panelRef"
        class="glass rounded-2xl px-6 py-4 flex flex-col items-center gap-2
               border border-c-border/40 shadow-lg select-none"
        :class="[
          isDragging ? 'cursor-grabbing' : 'cursor-grab',
          'pointer-events-auto'
        ]"
        @mousedown.prevent="onDragStart"
      >
        <!-- Drag handle (decorative dots + visual indicator) -->
        <div class="flex items-center gap-2 mb-1 opacity-60">
          <span class="w-2 h-2 rounded-full bg-c-accent/60" />
          <span class="w-2 h-2 rounded-full bg-c-blue/50" />
          <span class="w-2 h-2 rounded-full bg-c-accent/60" />
          <span class="text-10px text-c-text-muted ml-1">↕ 拖拽</span>
        </div>

        <!-- Original text -->
        <p
          v-if="showOriginal"
          class="text-c-text font-bold text-center leading-snug"
          :style="fontSizeStyle"
        >
          {{ text }}
          <span
            v-if="isStreaming"
            class="inline-block w-2 h-5 bg-c-accent/80 rounded-sm ml-1 animate-blink align-middle"
          />
        </p>

        <!-- Translation text -->
        <p
          v-if="showTranslation"
          class="text-c-text-dim/80 text-center leading-snug"
          :style="translationFontSizeStyle"
        >
          {{ translation }}
        </p>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.subtitle-enter-active {
  animation: popIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.subtitle-leave-active {
  animation: fadeOut 0.3s ease-in;
}

@keyframes popIn {
  0% {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes fadeOut {
  0% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}
</style>
