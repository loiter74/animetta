import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { DanmakuItem, DanmakuStatus, DanmakuReply } from '@/types/chat'

export const useDanmakuStore = defineStore('danmaku', () => {
  const messages = ref<DanmakuItem[]>([])
  const connected = ref(false)
  const statusMessage = ref('')
  const lastReply = ref<DanmakuReply | null>(null)
  const roomId = ref<number | null>(null)
  const isConnecting = ref(false)

  const messageCount = computed(() => messages.value.length)

  const MAX_MESSAGES = 500

  function addMessage(msg: DanmakuItem): void {
    messages.value.push(msg)
    // Evict oldest when exceeding limit
    if (messages.value.length > MAX_MESSAGES) {
      messages.value = messages.value.slice(-MAX_MESSAGES)
    }
  }

  function setStatus(status: DanmakuStatus): void {
    connected.value = status.connected
    statusMessage.value = status.message || ''
    if (!status.connected) {
      isConnecting.value = false
    }
  }

  function setLastReply(reply: DanmakuReply): void {
    lastReply.value = reply
  }

  function setRoomId(id: number | null): void {
    roomId.value = id
  }

  function setConnecting(connecting: boolean): void {
    isConnecting.value = connecting
  }

  function clearMessages(): void {
    messages.value = []
  }

  return {
    messages,
    connected,
    statusMessage,
    lastReply,
    roomId,
    isConnecting,
    messageCount,
    addMessage,
    setStatus,
    setLastReply,
    setRoomId,
    setConnecting,
    clearMessages,
  }
})
