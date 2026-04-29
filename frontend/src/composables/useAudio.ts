import { ref } from 'vue'

export function useAudio() {
  const isPlaying = ref(false)
  const currentAudio: HTMLAudioElement | null = null

  function play(base64Data: string, format = 'wav'): void {
    stop()
    const audio = new Audio(`data:audio/${format};base64,${base64Data}`)
    audio.onended = () => {
      isPlaying.value = false
    }
    audio.play()
    isPlaying.value = true
  }

  function playUrl(url: string): void {
    stop()
    const audio = new Audio(url)
    audio.onended = () => {
      isPlaying.value = false
    }
    audio.play()
    isPlaying.value = true
  }

  function stop(): void {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.currentTime = 0
    }
    isPlaying.value = false
  }

  return { isPlaying, play, playUrl, stop }
}
