import { onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { LlmChunk, Transcript } from '@/types/chat'
import { getSocket } from './useSocket'

export function useChat() {
  const store = useChatStore()

  // Store callback refs so onUnmounted removes ONLY our callbacks
  let _onSentence: ((data: { text: string; seq: number }) => void) | null = null
  let _onControl: ((data: { signal: string }) => void) | null = null
  let _onTranscript: ((data: Transcript) => void) | null = null
  let _onMemProgress: (() => void) | null = null
  let _onMemResult: (() => void) | null = null

  onMounted(() => {
    const socket = getSocket()
    if (!socket) return

    // Listen for streaming LLM chunks
    _onSentence = (data: { text: string; seq: number }) => {
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
    }

    // Listen for conversation end
    _onControl = (data: { signal: string }) => {
      if (data.signal === 'conversation-end') {
        store.finalizeResponse()
      }
    }

    // Listen for transcript (ASR result)
    _onTranscript = (data: Transcript) => {
      if (!data.text?.trim()) return
      store.createMessage('user', data.text, 'voice')
      store.isTyping = true
    }

    // Memory organize progress
    _onMemProgress = () => {
      // Handled in component for UI display
    }

    // Memory organize result
    _onMemResult = () => {
      store.memoryOrganizing = false
    }

    socket.on('sentence', _onSentence)
    socket.on('control', _onControl)
    socket.on('transcript', _onTranscript)
    socket.on('memory.organize.progress', _onMemProgress)
    socket.on('memory.organize.result', _onMemResult)
  })

  onUnmounted(() => {
    const socket = getSocket()
    if (!socket) return
    // Only remove OUR callbacks, not other components' listeners
    if (_onSentence) socket.off('sentence', _onSentence)
    if (_onControl) socket.off('control', _onControl)
    if (_onTranscript) socket.off('transcript', _onTranscript)
    if (_onMemProgress) socket.off('memory.organize.progress', _onMemProgress)
    if (_onMemResult) socket.off('memory.organize.result', _onMemResult)
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

    // Listen for result to reset state and refresh memory list
    const onResult = (_data: any) => {
      console.log('[useChat] memory.organize.result received, refreshing wiki pages')
      store.memoryOrganizing = false
      socket.off('memory.organize.result', onResult)
      socket.emit('get_wiki_pages', { session_id: 'default' })
    }
    socket.on('memory.organize.result', onResult)
  }

  return {
    store,
    sendText,
    sendInterrupt,
    organizeMemory
  }
}
