<script setup lang="ts">
import type { ChatMessage } from '@/types/chat'

const props = defineProps<{ message: ChatMessage }>()

const isUser = props.message.role === 'user'
</script>

<template>
  <div
    class="flex flex-col max-w-85% mb-3 animate-slide-up"
    :class="isUser ? 'self-end items-end' : 'self-start items-start'"
  >
    <div
      class="px-4 py-2.5 text-sm leading-relaxed break-words"
      :class="[
        isUser
          ? 'bg-$c-user-bubble border border-blue-400/10 rounded-2xl rounded-br-sm'
          : 'bg-$c-ai-bubble border border-$c-accent/10 rounded-2xl rounded-bl-sm',
        message.status === 'streaming' ? 'streaming' : ''
      ]"
    >
      {{ message.text }}
      <span v-if="message.status === 'streaming'" class="inline-block w-0.5 h-4 bg-$c-accent ml-0.5 animate-blink align-text-bottom" />
    </div>
    <span class="text-10px text-$c-text-muted mt-1 px-1">
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
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
