import { onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { LlmChunk, Transcript } from '@/types/chat'
import { getSocket } from './useSocket'

export function useChat() {
  const store = useChatStore()
  const cleanups: (() => void)[] = []

  onMounted(() => {
    const socket = getSocket()
    if (!socket) return

    // Listen for streaming LLM chunks
    socket.on('sentence', (data: { text: string; seq: number }) => {
      store.isTyping = false

      if (data.text === '' || (data as any).is_complete) {
        store.finalizeResponse()
        return
      }

      if (data.seq === 0 || store.lastMessage?.status !== 'streaming') {
        store.resetResponse(data.seq)
      }

      store.bufferChunk(data.seq, data.text)
      store.processBufferedChunks()

      if (!store.lastMessage || store.lastMessage.status !== 'streaming') {
        store.scheduleFlush(() => store.updateStreamingMessage())
        return
      }
      store.updateStreamingMessage()
    })

    // Listen for conversation end
    socket.on('control', (data: { signal: string }) => {
      if (data.signal === 'conversation-end') {
        store.finalizeResponse()
      }
    })

    // Listen for transcript (ASR result)
    socket.on('transcript', (data: Transcript) => {
      if (!data.text?.trim()) return
      store.createMessage('user', data.text, 'voice')
      store.isTyping = true
    })

    // Memory organize progress
    socket.on('memory.organize.progress', () => {
      // Handled in component for UI display
    })

    // Memory organize result
    socket.on('memory.organize.result', () => {
      store.memoryOrganizing = false
    })
  })

  onUnmounted(() => {
    const socket = getSocket()
    if (!socket) return
    socket.off('sentence')
    socket.off('control')
    socket.off('transcript')
    socket.off('memory.organize.progress')
    socket.off('memory.organize.result')
  })

  async function sendText(text: string): Promise<void> {
    const socket = getSocket()
    if (!socket) return

    store.createMessage('user', text, 'text')
    store.isTyping = true

    socket.emit('text_input', { text })
  }

  async function sendInterrupt(): Promise<void> {
    store.finalizeResponse()
  }

  async function organizeMemory(): Promise<void> {
    const socket = getSocket()
    if (!socket) return

    store.memoryOrganizing = true
    socket.emit('memory_organize', {})
  }

  return {
    store,
    sendText,
    sendInterrupt,
    organizeMemory
  }
}
