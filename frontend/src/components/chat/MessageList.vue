<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'

const store = useChatStore()
const listRef = ref<HTMLElement | null>(null)
const userScrolled = ref(false)

function scrollToBottom(): void {
  nextTick(() => {
    if (!listRef.value || userScrolled.value) return
    listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

function handleScroll(): void {
  if (!listRef.value) return
  const { scrollTop, scrollHeight, clientHeight } = listRef.value
  userScrolled.value = scrollHeight - scrollTop - clientHeight > 50
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.lastMessage?.text, scrollToBottom)
</script>

<template>
  <div
    ref="listRef"
    class="overflow-y-auto px-4 py-3"
    :class="$attrs.class"
    @scroll="handleScroll"
  >
    <!-- Empty state -->
    <div v-if="store.messages.length === 0" class="flex flex-col items-center justify-center h-full text-$c-text-muted">
      <p class="text-lg mb-2">✨ Start a conversation</p>
      <p class="text-sm">Type a message below or click the mic to speak</p>
    </div>

    <!-- Messages -->
    <MessageBubble
      v-for="msg in store.messages"
      :key="msg.id"
      :message="msg"
    />
  </div>
</template>

<style scoped>
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
</style>
