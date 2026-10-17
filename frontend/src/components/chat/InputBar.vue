<script setup lang="ts">
import { ref } from 'vue'
import { unlockAudioPlayback } from '@/shared/audio/playback'
import { useMobile } from '@/composables/useMobile'
import VoiceButton from './VoiceButton.vue'

const {
  sendText,
  placeholder = '输入消息...',
  showVoice = true,
  appearance = 'glass',
} = defineProps<{
  sendText: (text: string) => void
  placeholder?: string
  showVoice?: boolean
  appearance?: 'glass' | 'surface'
}>()
const { isMobile } = useMobile()
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
  <div
    data-testid="chat-input-bar"
    class="flex w-full min-w-0 items-end gap-3 rounded-xl border border-c-border p-3 transition-colors duration-150 ease-out-expo touch-manipulation focus-within:border-c-border-accent focus-within:ring-2 focus-within:ring-c-accent/20"
    :class="[
      appearance === 'surface' ? 'bg-c-panel' : 'bg-c-surface/85 backdrop-blur-md',
      { 'mobile-input-bar pb-[max(0.75rem,env(safe-area-inset-bottom))]': isMobile },
    ]"
    @pointerdown.capture="unlockAudioPlayback"
    @keydown.capture="unlockAudioPlayback"
  >
    <textarea
      ref="textareaRef"
      v-model="inputText"
      class="min-h-10 min-w-0 max-h-30 flex-1 resize-none border-0 bg-transparent py-2 text-sm leading-6 text-c-text outline-none placeholder:text-c-text-muted"
      :class="{ 'mobile-input-textarea': isMobile }"
      :placeholder="placeholder"
      aria-label="消息内容"
      rows="1"
      @input="handleInput"
      @keydown="handleKeydown"
    />
    <div class="flex shrink-0 items-center gap-2">
      <VoiceButton v-if="showVoice" type="button" aria-label="切换语音输入" />
      <button
        class="btn-accent h-10 w-10 shrink-0 p-0"
        type="button"
        aria-label="发送消息"
        title="发送消息（Enter）"
        :disabled="!inputText.trim()"
        @click="sendMessage"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
        </svg>
      </button>
    </div>
  </div>
</template>
