<script setup lang="ts">
import { ref } from 'vue'
import VoiceButton from './VoiceButton.vue'

const { sendText } = defineProps<{ sendText: (text: string) => void }>()
const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function handleInput(): void {
  if (!textareaRef.value) return
  textareaRef.value.style.height = 'auto'
  textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 120) + 'px'
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function sendMessage(): void {
  const text = inputText.value.trim()
  if (!text) return
  sendText(text)
  inputText.value = ''
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
}
</script>

<template>
  <div class="px-4 py-3 border-t border-c-border flex gap-2 items-end">
    <textarea
      ref="textareaRef"
      v-model="inputText"
      class="flex-1 bg-c-panel/60 border border-c-border rounded-xl px-3 py-2.5 text-sm text-c-text
             placeholder-c-text-muted/50 resize-none min-h-10 max-h-30
             outline-none transition-colors focus:border-c-accent/40"
      placeholder="输入消息..."
      rows="1"
      @input="handleInput"
      @keydown="handleKeydown"
    />
    <VoiceButton />
    <button
      class="btn-accent w-10 h-10 flex items-center justify-center"
      :disabled="!inputText.trim()"
      @click="sendMessage"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
      </svg>
    </button>
  </div>
</template>
