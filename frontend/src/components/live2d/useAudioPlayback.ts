import { startLipSync, stopLipSync } from './useLipSync'
import { setExpression } from './useLive2DModel'

// ===== Audio State =====

let currentAudio: HTMLAudioElement | null = null
let currentBlobUrl: string | null = null

// ===== Audio Playback =====

function cleanup(): void {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.onended = null
    currentAudio = null
  }
  if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null }
}

export function playAudio(data: {
  audio_data?: string
  format?: string
  volumes?: number[]
  expressions?: any
  return_to_idle?: boolean
}): void {
  if (!data?.audio_data) return
  cleanup()

  const binary = atob(data.audio_data)
  const buffer = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) buffer[i] = binary.charCodeAt(i)

  const blob = new Blob([buffer], { type: `audio/${data.format || 'mp3'}` })
  const url = URL.createObjectURL(blob)
  currentBlobUrl = url
  const audio = new Audio(url)
  currentAudio = audio

  if (data.volumes?.length) startLipSync(audio, data.volumes)

  audio.onended = () => {
    stopLipSync()
    if (data.return_to_idle) setExpression('idle')
    cleanup()
  }

  audio.play().catch(() => cleanup())
}

export function stopAudio(): void {
  if (currentAudio) {
    currentAudio.pause()
    currentAudio.currentTime = 0
  }
  stopLipSync()
  cleanup()
}

export function cleanupAudio(): void {
  cleanup()
}
