import { defineStore } from 'pinia'
import { ref, onMounted, onUnmounted } from 'vue'
import { getSocket } from '@/composables/useSocket'

export interface MinecraftStatus {
  connected: boolean
  username?: string
  error?: string
}

export const useMinecraftStore = defineStore('minecraft', () => {
  const connected = ref(false)
  const isConnecting = ref(false)
  const username = ref('')
  const error = ref('')

  let cleanup: (() => void) | null = null

  function setupListener(): void {
    const socket = getSocket()
    if (!socket) return

    const handler = (data: MinecraftStatus) => {
      connected.value = data.connected
      isConnecting.value = false
      if (data.username) username.value = data.username
      if (data.error) error.value = data.error
      else if (data.connected) error.value = ''
    }

    socket.on('minecraft.status', handler)
    cleanup = () => socket.off('minecraft.status', handler)
  }

  function teardownListener(): void {
    cleanup?.()
  }

  function start(): void {
    const socket = getSocket()
    if (!socket) return
    isConnecting.value = true
    error.value = ''
    socket.emit('minecraft.start', {})
  }

  function stop(): void {
    const socket = getSocket()
    if (!socket) return
    socket.emit('minecraft.stop')
  }

  return {
    connected,
    isConnecting,
    username,
    error,
    setupListener,
    teardownListener,
    start,
    stop,
  }
})
