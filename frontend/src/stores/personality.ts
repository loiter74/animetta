import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSocket } from '@/composables/useSocket'

export const usePersonalityStore = defineStore('personality', () => {
  const currentMode = ref<'default' | 'streaming'>('default')
  const currentMood = ref<string | null>(null)
  const availablePersonas = ref<string[]>([])
  const memoryInfluence = ref(0.3)

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

  return {
    currentMode,
    currentMood,
    availablePersonas,
    memoryInfluence,
    setPersona,
    setMode,
    setMood,
    setMemoryInfluence,
  }
})
