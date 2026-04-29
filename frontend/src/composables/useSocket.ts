import { onMounted, onUnmounted } from 'vue'
import { useConnectionStore } from '@/stores/connection'

export function useSocket() {
  const store = useConnectionStore()
  let cleanup: (() => void) | null = null

  onMounted(() => {
    if (!window.electronAPI?.connection) return

    cleanup = window.electronAPI.connection.onStatus((data) => {
      store.setStatus(data.status, data.message)
    })
  })

  onUnmounted(() => {
    cleanup?.()
  })

  return { connectionStatus: store.status }
}
