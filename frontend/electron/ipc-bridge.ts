import { BrowserWindow, ipcMain } from 'electron'
import { io, Socket } from 'socket.io-client'

/**
 * IpcBridge - Connects Electron main process to the Python backend via Socket.IO
 * Relays events between backend and renderer processes via IPC.
 */
export class IpcBridge {
  private mainWindow: BrowserWindow
  private socket: Socket | null = null
  private socketConnected = false
  private messageQueue: Array<{ event: string; data: unknown }> = []

  constructor(mainWindow: BrowserWindow) {
    this.mainWindow = mainWindow
    this.registerIpcHandlers()
    this.connectSocket()
  }

  private registerIpcHandlers(): void {
    // Window controls
    ipcMain.on('window:minimize', () => this.mainWindow.minimize())
    ipcMain.on('window:maximize', () => {
      this.mainWindow.isMaximized() ? this.mainWindow.unmaximize() : this.mainWindow.maximize()
    })
    ipcMain.on('window:close', () => this.mainWindow.close())

    // Chat → Backend
    ipcMain.handle('chat:sendMessage', async (_event, message: { text: string; timestamp: number }) => {
      this.sendToBackend('text_input', message)
      return { ok: true }
    })

    ipcMain.handle('chat:startVoiceInput', async () => {
      this.sendToBackend('voice_start', {})
      return { ok: true }
    })

    ipcMain.handle('chat:stopVoiceInput', async () => {
      this.sendToBackend('mic_audio_end', {})
      return { ok: true }
    })

    ipcMain.on('chat:sendAudioChunk', (_event, audioData: number[]) => {
      this.sendToBackend('raw_audio_data', { audio: audioData })
    })

    ipcMain.handle('chat:setSpeaking', async (_event, isSpeaking: boolean) => {
      this.sendToBackend('chat_speaking', { isSpeaking })
      return { ok: true }
    })

    ipcMain.handle('chat:setStyleTransfer', async (_event, enabled: boolean) => {
      this.sendToBackend('style_transfer_toggle', { enabled })
      return { ok: true }
    })

    ipcMain.handle('chat:organizeMemory', async () => {
      this.sendToBackend('memory_organize', {})
      return { ok: true }
    })

    // Live2D → Backend
    ipcMain.handle('live2d:setExpression', async (_event, name: string) => {
      // Expression changes are local to renderer, no backend event needed
      return { ok: true }
    })

    // App
    ipcMain.handle('app:getVersion', async () => {
      return '2.0.0'
    })

    ipcMain.handle('app:getConfig', async (_event, key: string) => {
      // TODO: implement config store
      return null
    })

    console.log('[IpcBridge] IPC handlers registered')
  }

  private connectSocket(): void {
    const wsUrl = 'http://localhost:12394'

    console.log('[IpcBridge] Connecting to backend:', wsUrl)

    this.socket = io(wsUrl, {
      path: '/socket.io/',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 3000,
      reconnectionAttempts: Infinity,
      pingTimeout: 120000,
      pingInterval: 30000
    })

    this.socket.on('connect', () => {
      console.log('[IpcBridge] Socket.IO connected')
      this.socketConnected = true
      this.sendToRenderer('connection:status', { status: 'connected' })
      this.socket!.emit('desktop_register', { client_type: 'desktop' })

      // Flush message queue
      while (this.messageQueue.length > 0) {
        const msg = this.messageQueue.shift()!
        this.socket!.emit(msg.event, msg.data)
      }
    })

    this.socket.on('disconnect', () => {
      console.log('[IpcBridge] Socket.IO disconnected')
      this.socketConnected = false
      this.sendToRenderer('connection:status', { status: 'disconnected' })
    })

    this.socket.on('connect_error', (err) => {
      console.error('[IpcBridge] Connection error:', err.message)
      this.sendToRenderer('connection:status', { status: 'error', message: err.message })
    })

    // Backend events → Renderer
    this.socket.on('sentence', (data) => {
      this.sendToRenderer('llm:chunk', {
        text: data.text || '',
        seq: data.seq || 0,
        is_complete: data.text === '' || data.is_complete
      })
    })

    this.socket.on('control', (data) => {
      if (data.signal === 'conversation-end') {
        this.sendToRenderer('chat:complete', {})
      }
    })

    this.socket.on('transcript', (data) => {
      this.sendToRenderer('chat:transcript', data)
    })

    this.socket.on('live2d.action', (data) => {
      this.sendToRenderer('live2d:action', data)
    })

    this.socket.on('audio_with_expression', (data) => {
      this.sendToRenderer('audio:with-expression', data)
    })

    this.socket.on('audio.stream', (data) => {
      this.sendToRenderer('audio:stream', data)
    })

    this.socket.on('stop_audio', () => {
      this.sendToRenderer('audio:stop', {})
    })

    this.socket.on('memory.organize.progress', (data) => {
      this.sendToRenderer('memory:organize-progress', data)
    })

    this.socket.on('memory.organize.result', (data) => {
      this.sendToRenderer('memory:organize-result', data)
    })
  }

  private sendToRenderer(channel: string, data: unknown): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, data)
    }
  }

  private sendToBackend(event: string, data: unknown): void {
    if (this.socketConnected && this.socket?.connected) {
      this.socket.emit(event, data)
    } else {
      this.messageQueue.push({ event, data })
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
    }
  }
}
