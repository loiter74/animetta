import { ref, onMounted, onUnmounted } from 'vue'
import { useSubtitleStore } from '@/stores/subtitle'
import { getSocket } from './useSocket'
import type { SentenceEvent } from '@/types/socket-events'

export function useSubtitle() {
  const store = useSubtitleStore()

  const text = ref('')
  const translation = ref('')
  const sourceLang = ref('')
  const targetLang = ref('')
  const visible = ref(false)
  const isStreaming = ref(false)

  /** Strip emotion tags like [neutral], [happy], [thinking] from text */
  function stripEmotionTags(text: string): string {
    return text.replace(/\[(happy|sad|angry|surprised|thinking|neutral)\]/g, '').trim()
  }

  let hideTimeout: ReturnType<typeof setTimeout> | null = null
  let accumulatedText = ''
  let accumulatedTranslation = ''

  function scheduleHide(delay = 6000): void {
    if (hideTimeout) clearTimeout(hideTimeout)
    hideTimeout = setTimeout(() => {
      visible.value = false
      text.value = ''
      translation.value = ''
    }, delay)
  }

  function cancelHide(): void {
    if (hideTimeout) {
      clearTimeout(hideTimeout)
      hideTimeout = null
    }
  }

  function showSubtitle(finalText: string, finalTranslation?: string, lang?: string, tLang?: string): void {
    cancelHide()
    text.value = stripEmotionTags(finalText)
    translation.value = finalTranslation || ''
    sourceLang.value = lang || ''
    targetLang.value = tLang || ''
    visible.value = true
  }

  /** Translation received async (non-blocking, from background task) */
  interface SubtitleTranslationEvent {
    translation: string
    target_lang?: string
  }

  // Store refs so socket.off removes ONLY our callbacks
  let _onSentence: ((data: SentenceEvent) => void) | null = null
  let _onControl: ((data: { signal: string }) => void) | null = null
  let _onStopAudio: (() => void) | null = null
  let _onSubtitleTranslation: ((data: SubtitleTranslationEvent) => void) | null = null

  onMounted(() => {
    const socket = getSocket()
    if (!socket) return

    _onSentence = (data: SentenceEvent) => {
      if (!store.enabled) return

      // Final / complete signal
      if (data.is_complete || data.text === '') {
        isStreaming.value = false
        if (accumulatedText) {
          showSubtitle(accumulatedText, accumulatedTranslation, data.lang, data.target_lang)
          // Subtitle stays visible while TTS plays — hide 6s after last text
          scheduleHide(6000)
        }
        accumulatedText = ''
        accumulatedTranslation = ''
        return
      }

      // Streaming chunk
      isStreaming.value = true
      if (data.seq === 0) {
        accumulatedText = stripEmotionTags(data.text)
        accumulatedTranslation = data.translation || ''
      } else {
        accumulatedText += stripEmotionTags(data.text)
      }

      // Show immediately on first chunk
      if (data.seq === 0 && accumulatedText) {
        showSubtitle(accumulatedText, accumulatedTranslation, data.lang, data.target_lang)
        cancelHide() // keep visible while streaming
      }
    }

    _onControl = (data: { signal: string }) => {
      if (data.signal === 'conversation-end') {
        isStreaming.value = false
        // Don't hide immediately — wait for 6s timeout or stop_audio
      }
    }

    // Hide subtitle early when audio stops (TTS finished playing)
    _onStopAudio = () => {
      scheduleHide(1500)
    }

    // Receive translation asynchronously (non-blocking backend)
    _onSubtitleTranslation = (data: SubtitleTranslationEvent) => {
      translation.value = data.translation
      targetLang.value = data.target_lang || ''
      // Reset the hide timer since we got new content
      cancelHide()
      scheduleHide(6000)
    }

    socket.on('sentence', _onSentence)
    socket.on('control', _onControl)
    socket.on('stop_audio', _onStopAudio)
    socket.on('subtitle.translation', _onSubtitleTranslation)
  })

  onUnmounted(() => {
    const socket = getSocket()
    if (!socket) return
    // Only remove OUR callbacks, not other components' listeners
    if (_onSentence) socket.off('sentence', _onSentence)
    if (_onControl) socket.off('control', _onControl)
    if (_onStopAudio) socket.off('stop_audio', _onStopAudio)
    if (_onSubtitleTranslation) socket.off('subtitle.translation', _onSubtitleTranslation)
    if (hideTimeout) clearTimeout(hideTimeout)
  })

  return {
    store,
    text,
    translation,
    sourceLang,
    targetLang,
    visible,
    isStreaming,
  }
}
