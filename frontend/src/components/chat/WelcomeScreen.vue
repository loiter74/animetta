<script setup lang="ts">
const emit = defineEmits<{
  dismiss: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center h-full px-6 text-center select-none">
    <!-- Character name -->
    <h2
      class="text-xl font-medium text-c-accent mb-3"
      style="animation: charFadeIn 0.4s ease both"
    >
      Anima
    </h2>

    <!-- Greeting -->
    <p
      class="text-sm text-c-text-dim leading-relaxed mb-4"
      style="animation: charFadeIn 0.4s ease 0.15s both"
    >
      你好呀～有什么想聊的吗？
    </p>

    <!-- Hint -->
    <p
      class="text-xs text-c-text-muted"
      style="animation: charFadeIn 0.4s ease 0.3s both"
    >
      在下方输入消息开始对话 ✨
    </p>
  </div>
</template>
