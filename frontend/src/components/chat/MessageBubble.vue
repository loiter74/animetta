<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types/chat'

const props = defineProps<{ message: ChatMessage }>()

const isUser = props.message.role === 'user'

// For streaming AI messages, wrap text in spans for per-char animation
const displayText = computed(() => {
  return props.message.text
})
</script>

<template>
  <div
    class="flex flex-col max-w-90% mb-2"
    :class="isUser ? 'self-end items-end' : 'self-start items-start'"
  >
    <div
      class="px-3 py-2 text-sm leading-relaxed break-words"
      :class="[
        isUser
          ? 'bg-c-user-bubble border border-blue-400/10 rounded-2xl rounded-br-sm'
          : 'bg-c-ai-bubble border border-c-accent/10 rounded-2xl rounded-bl-sm',
        message.status === 'streaming' ? 'streaming' : 'animate-[slideUp_0.25s_ease]'
      ]"
    >
      <span v-if="!isUser && message.status === 'streaming'" class="streaming-text">
        <span
          v-for="(char, i) in displayText"
          :key="i"
          class="inline-block"
          :style="{ animationDelay: `${Math.max(0, (displayText.length - 10) - i) * 8}ms` }"
        >{{ char }}</span>
      </span>
      <template v-else>{{ displayText }}</template>
      <span v-if="message.status === 'streaming'" class="inline-block w-0.5 h-4 bg-c-accent ml-0.5 animate-blink align-text-bottom" />
    </div>
    <span class="text-9px text-c-text-muted mt-0.5 px-1">
      {{ new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}
    </span>
  </div>
</template>

<style scoped>
.streaming {
  animation: none;
}
.animate-blink {
  animation: blink 1s infinite;
}

.streaming-text span {
  animation: charFadeIn 0.15s ease both;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
