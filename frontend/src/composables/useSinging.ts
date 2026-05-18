import { getSocket } from './useSocket'
import { useSingingStore } from '@/stores/singing'

export function useSinging() {
  const store = useSingingStore()

  function process(url: string, autoConfirm = true) {
    store.url = url
    store.setProgress('downloading', 0, 'Starting...')
    const socket = getSocket()
    if (!socket?.connected) {
      store.setError('Cannot connect to server')
      return
    }
    socket.emit('sing:process', { url, auto_confirm: autoConfirm })
  }

  function confirmLyrics(assContent: string) {
    const socket = getSocket()
    if (socket?.connected) {
      socket.emit('sing:confirm_lyrics', { ass_content: assContent })
    }
  }

  function cancel() {
    const socket = getSocket()
    if (socket?.connected) {
      socket.emit('sing:cancel', {})
    }
  }

  return { process, confirmLyrics, cancel }
}
