<script setup lang="ts">
import { ref } from 'vue'
import { useHoverPhysics } from '@/composables/useHoverPhysics'

interface Props {
  variant?: 'default' | 'strong'
  hover?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  hover: true
})

const panelRef = ref<HTMLElement | null>(null)

// Hover physics (only if enabled)
const { onEnter, onLeave } = props.hover
  ? useHoverPhysics(panelRef, { scale: 1.02 })
  : { onEnter: undefined, onLeave: undefined }
</script>

<template>
  <div
    ref="panelRef"
    :class="[
      variant === 'strong'
        ? 'bg-c-surface/85 backdrop-blur-[40px] border border-c-border rounded-2xl shadow-lg'
        : 'bg-c-surface/70 backdrop-blur-xl border border-c-border rounded-2xl',
      hover && 'cursor-pointer'
    ]"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <slot />
  </div>
</template>
