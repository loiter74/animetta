import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage, MessageRole, MessageStatus } from '@/types/chat'

let messageIdCounter = 0

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isTyping = ref(false)
  const isSpeaking = ref(false)
  const styleTransferEnabled = ref(false)
  const memoryOrganizing = ref(false)

  // Streaming state
  const currentResponse = ref('')
  const currentResponseSeq = ref(0)
  const responseBuffer = new Map<number, string>()
  let flushTimeout: ReturnType<typeof setTimeout> | null = null

  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  function createMessage(role: MessageRole, text: string, source?: 'text' | 'voice'): ChatMessage {
    const msg: ChatMessage = {
      id: `msg-${Date.now()}-${++messageIdCounter}`,
      role,
      text,
      timestamp: Date.now(),
      status: 'complete',
      source
    }
    messages.value.push(msg)
    return msg
  }

  function resetResponse(startSeq = 0): void {
    currentResponse.value = ''
    currentResponseSeq.value = startSeq
    responseBuffer.clear()
    if (flushTimeout) {
      clearTimeout(flushTimeout)
      flushTimeout = null
    }
  }

  function bufferChunk(seq: number, text: string): void {
    responseBuffer.set(seq, text)
  }

  function processBufferedChunks(flushAll = false): void {
    while (responseBuffer.has(currentResponseSeq.value)) {
      const chunk = responseBuffer.get(currentResponseSeq.value)!
      currentResponse.value += chunk
      responseBuffer.delete(currentResponseSeq.value)
      currentResponseSeq.value++
    }
    if (flushAll && responseBuffer.size > 0) {
      const sorted = Array.from(responseBuffer.keys()).sort((a, b) => a - b)
      for (const seq of sorted) {
        currentResponse.value += responseBuffer.get(seq)!
        responseBuffer.delete(seq)
      }
    }
  }

  function updateStreamingMessage(): void {
    if (!currentResponse.value) return
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant' && last.status === 'streaming') {
      last.text = currentResponse.value
    } else {
      const msg: ChatMessage = {
        id: `msg-${Date.now()}-${++messageIdCounter}`,
        role: 'assistant',
        text: currentResponse.value,
        timestamp: Date.now(),
        status: 'streaming'
      }
      messages.value.push(msg)
    }
  }

  function finalizeResponse(): void {
    processBufferedChunks(true)
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant' && last.status === 'streaming') {
      last.text = currentResponse.value
      last.status = 'complete'
    } else if (currentResponse.value) {
      // 🐛 Fix: Backend sends full text + is_complete in quick succession.
      // scheduleFlush (500ms) hasn't fired yet, so no streaming message exists.
      // Create the assistant message directly.
      const msg: ChatMessage = {
        id: `msg-${Date.now()}-${++messageIdCounter}`,
        role: 'assistant',
        text: currentResponse.value,
        timestamp: Date.now(),
        status: 'complete'
      }
      messages.value.push(msg)
    }
    currentResponse.value = ''
    isTyping.value = false
  }

  function scheduleFlush(callback: () => void, delay = 500): void {
    if (flushTimeout) clearTimeout(flushTimeout)
    flushTimeout = setTimeout(() => {
      if (responseBuffer.size > 0) {
        processBufferedChunks(true)
        callback()
      }
    }, delay)
  }

  return {
    messages,
    isTyping,
    isSpeaking,
    styleTransferEnabled,
    memoryOrganizing,
    lastMessage,
    createMessage,
    resetResponse,
    bufferChunk,
    processBufferedChunks,
    updateStreamingMessage,
    finalizeResponse,
    scheduleFlush
  }
})
