<script setup lang="ts">
defineProps<{
  variant?: 'default' | 'strong'
}>()
</script>

<template>
  <div
    :class="variant === 'strong'
      ? 'bg-c-surface/85 backdrop-blur-[40px] border border-c-border rounded-2xl shadow-lg'
      : 'bg-c-surface/70 backdrop-blur-xl border border-c-border rounded-2xl'"
  >
    <slot />
  </div>
</template>
