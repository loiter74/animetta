import { contextBridge, ipcRenderer } from 'electron'

const api = {
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  getConfig: (key: string) => ipcRenderer.invoke('app:getConfig', key),

  live2d: {
    setExpression: (name: string) => ipcRenderer.invoke('live2d:setExpression', name),
    onAction: (cb: (data: unknown) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data)
      ipcRenderer.on('live2d:action', listener)
      return () => ipcRenderer.removeListener('live2d:action', listener as any)
    },
    onAudioStream: (cb: (data: unknown) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data)
      ipcRenderer.on('audio:stream', listener)
      return () => ipcRenderer.removeListener('audio:stream', listener as any)
    },
    onAudioWithExpression: (cb: (data: unknown) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data)
      ipcRenderer.on('audio:with-expression', listener)
      return () => ipcRenderer.removeListener('audio:with-expression', listener as any)
    },
    onStopAudio: (cb: () => void) => {
      const listener = () => cb()
      ipcRenderer.on('audio:stop', listener)
      return () => ipcRenderer.removeListener('audio:stop', listener)
    }
  },

  chat: {
    sendMessage: (msg: { text: string; timestamp: number }) =>
      ipcRenderer.invoke('chat:sendMessage', msg),
    startVoiceInput: () => ipcRenderer.invoke('chat:startVoiceInput'),
    stopVoiceInput: () => ipcRenderer.invoke('chat:stopVoiceInput'),
    sendAudioChunk: (data: number[]) => ipcRenderer.send('chat:sendAudioChunk', data),
    setSpeaking: (v: boolean) => ipcRenderer.invoke('chat:setSpeaking', v),
    setStyleTransfer: (v: boolean) => ipcRenderer.invoke('chat:setStyleTransfer', v),
    organizeMemory: () => ipcRenderer.invoke('chat:organizeMemory'),

    onLlmChunk: (cb: (data: unknown) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data)
      ipcRenderer.on('llm:chunk', listener)
      return () => ipcRenderer.removeListener('llm:chunk', listener as any)
    },
    onComplete: (cb: () => void) => {
      const listener = () => cb()
      ipcRenderer.on('chat:complete', listener)
      return () => ipcRenderer.removeListener('chat:complete', listener)
    },
    onTranscript: (cb: (data: unknown) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data)
      ipcRenderer.on('chat:transcript', listener)
      return () => ipcRenderer.removeListener('chat:transcript', listener as any)
    },
    onStyleTransfer: (cb: (v: boolean) => void) => {
      const listener = (_: unknown, v: boolean) => cb(v)
      ipcRenderer.on('chat:styleTransfer', listener)
      return () => ipcRenderer.removeListener('chat:styleTransfer', listener as any)
    },
    onMemoryProgress: (cb: (data: unknown) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data)
      ipcRenderer.on('memory:organize-progress', listener)
      return () => ipcRenderer.removeListener('memory:organize-progress', listener as any)
    },
    onMemoryResult: (cb: (data: unknown) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data)
      ipcRenderer.on('memory:organize-result', listener)
      return () => ipcRenderer.removeListener('memory:organize-result', listener as any)
    }
  },

  connection: {
    onStatus: (cb: (data: { status: string; message?: string }) => void) => {
      const listener = (_: unknown, data: unknown) => cb(data as any)
      ipcRenderer.on('connection:status', listener)
      return () => ipcRenderer.removeListener('connection:status', listener as any)
    }
  },

  window: {
    minimize: () => ipcRenderer.send('window:minimize'),
    maximize: () => ipcRenderer.send('window:maximize'),
    close: () => ipcRenderer.send('window:close')
  }
}

contextBridge.exposeInMainWorld('electronAPI', api)
