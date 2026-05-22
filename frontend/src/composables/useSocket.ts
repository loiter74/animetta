import { io, Socket } from 'socket.io-client'
import { ref, onMounted, onUnmounted } from 'vue'
import { useConnectionStore } from '@/stores/connection'
import { useModelLoadingStore } from '@/stores/modelLoading'
import { useSingingStore } from '@/stores/singing'
import type { ModelStatusPayload } from '@/types/model-loading'
import type { ConnectionStatus } from '@/types/socket-events'
import type { PipelineStage, SongResult } from '@/types/singing'

// Direct connection to backend. CORS is enabled (cors_allowed_origins='*').
const SOCKET_URL = 'http://localhost:12394'

let socket: Socket | null = null
let _initialized = false

/**
 * Create a singleton Socket.IO connection to the Anima backend.
 * Call once at app startup. Composables import the socket ref for use.
 */
export function useSocket() {
  const store = useConnectionStore()

  if (!_initialized && !socket) {
    socket = io(SOCKET_URL, {
      path: '/socket.io/',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 3000,
      reconnectionAttempts: Infinity,
      timeout: 120000
    })

    socket.on('connect', () => {
      store.setStatus('connected')
    })

    socket.on('disconnect', () => {
      store.setStatus('disconnected')
    })

    socket.on('connect_error', (err) => {
      store.setStatus('error', err.message)
    })

    // Listen for model loading status
    const modelStore = useModelLoadingStore()
    socket.on('model_status', (payload: ModelStatusPayload) => {
      modelStore.updateModelStatus(payload)
    })

    // Clear loading state on reconnect
    socket.on('connect', () => {
      // Don't clear on reconnect - warmup may still be in progress
    })

    // Register singing event listeners globally (survive tab switches)
    const singStore = useSingingStore()
    socket.on('sing:progress', (data: any) => {
      singStore.setProgress(data.stage, data.progress, data.message || '')
    })
    socket.on('sing:complete', (data: any) => {
      singStore.setResult({
        audio_url: data.audio_url,
        subtitle_url: data.subtitle_url || '',
        tts_audio_url: data.tts_audio_url || '',
        vocals_url: data.vocals_url || '',
        video_title: data.video_title || '',
        duration: data.duration,
        lyrics: data.lyrics || [],
        volumes: data.volumes || [],
      })
    })
    socket.on('sing:error', (data: any) => {
      singStore.setError(data.error)
    })
    socket.on('sing:lyrics_ready', (data: any) => {
      singStore.setProgress('waiting_lyrics' as PipelineStage, 0, data.message || 'Lyrics ready')
    })

    _initialized = true
  }

  onMounted(() => {
    // Pull initial status
    store.setStatus(socket?.connected ? 'connected' : 'disconnected')
  })

  return { socket, connectionStatus: store.status }
}

/** Get the global socket instance for use in composables */
export function getSocket(): Socket | null {
  return socket
}
