<script setup lang="ts">
defineProps<{
  variant?: 'accent' | 'ghost'
  disabled?: boolean
}>()
</script>

<template>
  <button
    :disabled="disabled"
    :class="variant === 'ghost'
      ? 'bg-transparent hover:bg-c-accent-soft text-c-text-dim hover:text-c-accent rounded-lg px-3.5 py-2 text-sm transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 font-inherit cursor-pointer'
      : 'bg-c-accent hover:bg-c-accent-hover text-white rounded-lg px-[18px] py-2.5 text-sm font-medium transition-all duration-200 active:scale-96 disabled:bg-c-card disabled:text-c-text-muted disabled:cursor-not-allowed disabled:shadow-none font-inherit cursor-pointer'"
  >
    <slot />
  </button>
</template>

<style scoped>
.font-inherit { font-family: inherit; }
.active\:scale-96:active { transform: scale(0.96); }
</style>
