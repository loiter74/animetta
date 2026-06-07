<script setup lang="ts">
import { ref } from 'vue'
import { useHoverPhysics } from '@/composables/useHoverPhysics'

interface Props {
  variant?: 'accent' | 'ghost'
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'accent',
  disabled: false
})

const btnRef = ref<HTMLElement | null>(null)

// Hover physics with scale
const { onEnter, onLeave } = useHoverPhysics(btnRef, {
  scale: 1.05,
  duration: 0.3,
  ease: 'back.out(1.7)'
})
</script>

<template>
  <button
    ref="btnRef"
    :disabled="disabled"
    :class="[
      variant === 'ghost'
        ? 'bg-transparent hover:bg-c-accent-soft text-c-text-dim hover:text-c-accent rounded-lg px-3.5 py-2 text-sm transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50'
        : 'bg-c-accent hover:bg-c-accent-hover text-white rounded-lg px-[18px] py-2.5 text-sm font-medium transition-colors duration-200 disabled:bg-c-card disabled:text-c-text-muted disabled:cursor-not-allowed disabled:shadow-none',
      'font-inherit cursor-pointer'
    ]"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <slot />
  </button>
</template>

<style scoped>
.font-inherit { font-family: inherit; }
</style>
