/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

declare module 'pixi-live2d-display' {
  import type { Live2DModel } from 'pixi-live2d-display'
  export { Live2DModel }
  export const Live2DModel: any
}

interface Window {
  electronAPI: {
    getVersion: () => Promise<string>
    getConfig: (key: string) => Promise<unknown>
    live2d: {
      loadModel: (modelPath: string) => Promise<void>
      setExpression: (name: string) => Promise<void>
      playMotion: (group: string, index: number) => Promise<void>
      setParam: (name: string, value: number) => Promise<void>
      setMouthOpen: (value: number) => Promise<void>
      executeAction: (action: unknown) => Promise<void>
      getModelInfo: () => Promise<unknown>
      onAction: (cb: (data: unknown) => void) => () => void
      onAudioStream: (cb: (data: unknown) => void) => () => void
      onAudioWithExpression: (cb: (data: unknown) => void) => () => void
    }
    chat: {
      sendMessage: (msg: { text: string; timestamp: number }) => Promise<{ ok: boolean }>
      sendAudio: (data: number[]) => Promise<{ ok: boolean }>
      startVoiceInput: () => Promise<{ ok: boolean }>
      stopVoiceInput: () => Promise<{ ok: boolean }>
      sendAudioChunk: (data: number[]) => void
      setSpeaking: (v: boolean) => Promise<{ ok: boolean }>
      setStyleTransfer: (v: boolean) => Promise<{ ok: boolean }>
      organizeMemory: () => Promise<{ ok: boolean }>
      onLlmChunk: (cb: (data: unknown) => void) => () => void
      onMessage: (cb: (data: unknown) => void) => () => void
      onSpeaking: (cb: (v: boolean) => void) => () => void
      onStyleTransfer: (cb: (v: boolean) => void) => () => void
      onTranscript: (cb: (data: unknown) => void) => () => void
      onMemoryOrganizeProgress: (cb: (data: unknown) => void) => () => void
      onMemoryOrganizeResult: (cb: (data: unknown) => void) => () => void
    }
    window: {
      minimize: () => void
      maximize: () => void
      close: () => void
    }
  }
}
