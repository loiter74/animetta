import { playAudio, unlockAudioPlayback } from '@/shared/audio/playback'
import type { Narration } from '../contracts'

export function createNarration(options: {
  mouth(value: number): void
  started(taskId: string): void
  observed?(taskId: string, status: 'started' | 'ended' | 'cancelled'): void
}): Narration {
  let cancel: (() => void) | undefined
  return {
    play(taskId, audio, completed) {
      cancel?.()
      cancel = playAudio(
        audio,
        {
          onStart: () => {
            options.observed?.(taskId, 'started')
            options.started(taskId)
          },
          onComplete: () => {
            cancel = undefined
            options.mouth(0)
            options.observed?.(taskId, 'ended')
            completed('ended')
          },
          onCancel: () => {
            cancel = undefined
            options.mouth(0)
            options.observed?.(taskId, 'cancelled')
            completed('cancelled')
          },
        },
        options.mouth,
      )
    },
    cancel() {
      cancel?.()
      cancel = undefined
      options.mouth(0)
    },
    unlock: unlockAudioPlayback,
  }
}
