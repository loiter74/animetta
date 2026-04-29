<script setup lang="ts">
import { ref, watch } from 'vue'
import MessageList from './MessageList.vue'
import InputBar from './InputBar.vue'
import TypingIndicator from './TypingIndicator.vue'
import SpeakingIndicator from './SpeakingIndicator.vue'
import { useChat } from '@/composables/useChat'
import { useChatStore } from '@/stores/chat'

const { sendText, sendInterrupt, toggleStyleTransfer, organizeMemory } = useChat()
const store = useChatStore()

// Memory organize progress
const memoryProgress = ref('')
const memoryProgressPercent = ref(0)

// Style transfer toggle
const styleTransferOn = ref(false)

// Memory progress listener (set up once)
if (window.electronAPI?.chat?.onMemoryProgress) {
  window.electronAPI.chat.onMemoryProgress((data: any) => {
    memoryProgress.value = data.text || ''
    memoryProgressPercent.value = data.progress || 0
  })
}

function handleStyleTransferToggle(): void {
  styleTransferOn.value = !styleTransferOn.value
  toggleStyleTransfer(styleTransferOn.value)
}

async function handleMemoryOrganize(): Promise<void> {
  await organizeMemory()
}

// Reset memory progress when result comes
watch(() => store.memoryOrganizing, (organizing) => {
  if (!organizing) {
    memoryProgress.value = ''
    memoryProgressPercent.value = 0
  }
})
</script>

<template>
  <div class="flex flex-col h-full glass m-2">
    <!-- Toolbar -->
    <div class="flex items-center gap-2 px-4 py-2 border-b border-$c-border text-xs">
      <!-- Style Transfer -->
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded-lg transition-all"
        :class="styleTransferOn ? 'bg-$c-accent text-white' : 'bg-$c-panel/50 text-$c-text-dim hover:bg-$c-accent-soft'"
        @click="handleStyleTransferToggle"
      >
        <span>🎭</span>
        <span>风格迁移</span>
        <span
          class="text-10px font-bold px-1 rounded"
          :class="styleTransferOn ? 'bg-white/20' : 'bg-$c-card'"
        >
          {{ styleTransferOn ? 'ON' : 'OFF' }}
        </span>
      </button>

      <!-- Memory organize -->
      <button
        class="flex items-center gap-1.5 px-2 py-1 rounded-lg transition-all"
        :class="store.memoryOrganizing
          ? 'bg-$c-accent text-white pointer-events-none animate-pulse'
          : 'bg-$c-panel/50 text-$c-text-dim hover:bg-$c-accent-soft'"
        @click="handleMemoryOrganize"
      >
        <span>🧠</span>
        <span>{{ store.memoryOrganizing ? '整理中...' : '记忆整理' }}</span>
      </button>

      <div class="flex-1" />

      <!-- Interrupt button (only when streaming) -->
      <button
        v-if="store.lastMessage?.status === 'streaming'"
        class="flex items-center gap-1 px-2 py-1 rounded-lg bg-$c-error/20 text-$c-error hover:bg-$c-error/30 transition-all"
        @click="sendInterrupt"
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
          <rect x="4" y="4" width="16" height="16" rx="2" />
        </svg>
        停止
      </button>
    </div>

    <!-- Memory progress bar -->
    <div
      v-if="memoryProgress"
      class="px-4 py-1.5 bg-$c-card/80 border-b border-$c-border flex items-center gap-2 text-xs text-$c-text-dim animate-fade-in"
    >
      <span class="flex-1">{{ memoryProgress }}</span>
      <div class="w-20 h-1 bg-$c-bg rounded-full overflow-hidden">
        <div
          class="h-full bg-$c-accent rounded-full transition-all duration-300"
          :style="{ width: memoryProgressPercent + '%' }"
        />
      </div>
    </div>

    <!-- Typing indicator -->
    <TypingIndicator v-if="store.isTyping" />

    <!-- Speaking indicator -->
    <SpeakingIndicator v-if="store.isSpeaking" />

    <!-- Messages -->
    <MessageList class="flex-1" />

    <!-- Input -->
    <InputBar />
  </div>
</template>
