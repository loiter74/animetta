import { onMounted, onUnmounted } from 'vue'
import { useDanmakuStore } from '@/stores/danmaku'
import { useChatStore } from '@/stores/chat'
import type { DanmakuItem, DanmakuStatus, DanmakuReply } from '@/types/chat'
import { getSocket } from './useSocket'

export function useDanmaku() {
  const store = useDanmakuStore()
  const chatStore = useChatStore()

  function connect(roomId: number): void {
    const socket = getSocket()
    if (!socket) return
    store.setConnecting(true)
    socket.emit('bilibili.connect', { room_id: roomId })
  }

  function disconnect(): void {
    const socket = getSocket()
    if (!socket) return
    socket.emit('bilibili.disconnect')
  }

  function updateRoom(roomId: number): void {
    const socket = getSocket()
    if (!socket) return
    store.setConnecting(true)
    socket.emit('bilibili.update_room', { room_id: roomId })
  }

  onMounted(() => {
    const socket = getSocket()
    if (!socket) return

    socket.on('danmaku', (data: DanmakuItem) => {
      store.addMessage(data)
    })

    socket.on('danmaku.status', (data: DanmakuStatus) => {
      store.setStatus(data)
    })

    socket.on('danmaku.ai_reply', (data: DanmakuReply) => {
      // Store last reply for reference
      store.setLastReply(data)
      // Forward to chat message list as assistant message
      chatStore.createMessage(
        'assistant',
        `回复 @${data.user_name}: ${data.reply_text}`,
      )
    })
  })

  onUnmounted(() => {
    const socket = getSocket()
    if (!socket) return
    socket.off('danmaku')
    socket.off('danmaku.status')
    socket.off('danmaku.ai_reply')
  })

  return { store, connect, disconnect, updateRoom }
}
