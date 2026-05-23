import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSocket } from '@/composables/useSocket'

export const usePersonalityStore = defineStore('personality', () => {
  const currentMode = ref<'default' | 'streaming'>('default')
  const currentMood = ref<string | null>(null)
  const availablePersonas = ref<string[]>([])
  const memoryInfluence = ref(0.3)
  const mbtiType = ref<string | null>(null)
  const mbtiDimensions = ref<{ ei: number; sn: number; tf: number; jp: number } | null>(null)

  function setPersona(name: string): void {
    const socket = getSocket()
    if (!socket) return

    socket.emit('set_persona', { persona: name })
  }

  function setMode(mode: 'default' | 'streaming'): void {
    currentMode.value = mode

    const socket = getSocket()
    if (!socket) return

    socket.emit('set_personality_mode', { mode })
  }

  function setMood(mood: string | null): void {
    currentMood.value = mood
  }

  function setMemoryInfluence(value: number): void {
    memoryInfluence.value = Math.max(0, Math.min(1, value))
  }

  function setMbtiType(type: string | null): void {
    mbtiType.value = type
  }

  function setMbtiDimensions(dimensions: { ei: number; sn: number; tf: number; jp: number } | null): void {
    mbtiDimensions.value = dimensions
  }

  return {
    currentMode,
    currentMood,
    availablePersonas,
    memoryInfluence,
    mbtiType,
    mbtiDimensions,
    setPersona,
    setMode,
    setMood,
    setMemoryInfluence,
    setMbtiType,
    setMbtiDimensions,
  }
})
