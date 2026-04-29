import { onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { LlmChunk, Transcript } from '@/types/chat'

export function useChat() {
  const store = useChatStore()
  const cleanups: (() => void)[] = []

  onMounted(() => {
    if (!window.electronAPI?.chat) return

    // Listen for LLM chunks
    cleanups.push(
      window.electronAPI.chat.onLlmChunk((data) => {
        const chunk = data as LlmChunk
        store.isTyping = false

        if (chunk.is_complete) {
          store.finalizeResponse()
          return
        }

        if (chunk.seq === 0 || store.lastMessage?.status !== 'streaming') {
          store.resetResponse(chunk.seq)
        }

        store.bufferChunk(chunk.seq, chunk.text)
        store.processBufferedChunks()

        if (!store.lastMessage || store.lastMessage.status !== 'streaming') {
          store.scheduleFlush(() => store.updateStreamingMessage())
          return
        }
        store.updateStreamingMessage()
      })
    )

    // Listen for complete
    cleanups.push(
      window.electronAPI.chat.onComplete(() => {
        store.finalizeResponse()
      })
    )

    // Listen for transcript
    cleanups.push(
      window.electronAPI.chat.onTranscript((data) => {
        const t = data as Transcript
        if (!t.text?.trim()) return
        store.createMessage('user', t.text, 'voice')
        store.isTyping = true
      })
    )

    // Style transfer sync
    cleanups.push(
      window.electronAPI.chat.onStyleTransfer((enabled) => {
        store.styleTransferEnabled = enabled
      })
    )

    // Memory organize
    cleanups.push(
      window.electronAPI.chat.onMemoryProgress(() => {
        // Handled in component
      })
    )
    cleanups.push(
      window.electronAPI.chat.onMemoryResult(() => {
        store.memoryOrganizing = false
      })
    )
  })

  onUnmounted(() => {
    cleanups.forEach((fn) => fn())
  })

  async function sendText(text: string): Promise<void> {
    if (!window.electronAPI?.chat) return

    store.createMessage('user', text, 'text')
    store.isTyping = true

    await window.electronAPI.chat.sendMessage({
      text,
      timestamp: Date.now()
    })
  }

  async function sendInterrupt(): Promise<void> {
    if (!window.electronAPI?.chat) return
    // Backend uses text_input with empty or a special interrupt event
    // For now, we can just finalize locally
    store.finalizeResponse()
  }

  async function toggleStyleTransfer(enabled: boolean): Promise<void> {
    if (!window.electronAPI?.chat) return
    store.styleTransferEnabled = enabled
    await window.electronAPI.chat.setStyleTransfer(enabled)
  }

  async function organizeMemory(): Promise<void> {
    if (!window.electronAPI?.chat) return
    store.memoryOrganizing = true
    await window.electronAPI.chat.organizeMemory()
  }

  return {
    store,
    sendText,
    sendInterrupt,
    toggleStyleTransfer,
    organizeMemory
  }
}
