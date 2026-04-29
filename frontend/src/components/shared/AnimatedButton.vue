<script setup lang="ts">
interface Props {
  variant?: 'accent' | 'ghost'
}

const props = withDefaults(defineProps<Props>(), { variant: 'ghost' })
</script>

<template>
  <button
    :class="[
      variant === 'accent'
        ? 'btn-accent'
        : 'btn-ghost',
      'flex items-center justify-center',
    ]"
    v-bind="$attrs"
  >
    <slot />
  </button>
</template>
