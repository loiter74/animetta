import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ConnectionStatus } from '@/types/socket-events'

export const useConnectionStore = defineStore('connection', () => {
  const status = ref<ConnectionStatus>('disconnected')
  const errorMessage = ref<string>('')

  function setStatus(s: ConnectionStatus, msg?: string) {
    status.value = s
    errorMessage.value = msg ?? ''
  }

  return { status, errorMessage, setStatus }
})
