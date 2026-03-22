const { ipcMain } = require('electron');
const { io } = require('socket.io-client');
const { registerLive2dHandlers } = require('./handlers/live2d');
const { registerChatHandlers } = require('./handlers/chat');
const { registerDisplayHandlers } = require('./handlers/display');

/**
 * IPC Bridge - Bridges renderer processes and backend services via Socket.IO
 */
class IpcBridge {
  constructor(windowManager) {
    this.windowManager = windowManager;
    this.socket = null;
    this.socketConnected = false;
    this.messageQueue = [];

    this._registerHandlers();
    this._connectSocket();
  }

  /** @private */
  _registerHandlers() {
    registerLive2dHandlers(this);
    registerChatHandlers(this);
    registerDisplayHandlers();

    ipcMain.handle('app:getConfig', async (event, key) => {
      const appConfig = require('../config/appConfig');
      return appConfig.get(key);
    });

    ipcMain.handle('app:getVersion', async () => {
      const appConfig = require('../config/appConfig');
      return appConfig.get('application.version');
    });

    console.log('[IpcBridge] IPC handlers registered');
  }

  /** @private */
  _connectSocket() {
    const appConfig = require('../config/appConfig');
    const wsUrl = appConfig.getWsUrl().replace('ws://', 'http://').replace('wss://', 'https://');

    console.log('[IpcBridge] Connecting to backend:', wsUrl);

    this.socket = io(wsUrl, {
      path: '/socket.io/',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 3000,
      reconnectionAttempts: Infinity,
      pingTimeout: 120000,
      pingInterval: 30000
    });

    this.socket.on('connect', () => {
      console.log('[IpcBridge] Socket.IO connected');
      this.socketConnected = true;

      this.socket.emit('desktop_register', { client_type: 'desktop' });

      while (this.messageQueue.length > 0) {
        const message = this.messageQueue.shift();
        this.socket.emit(message.event, message.data);
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('[IpcBridge] Socket.IO connection error:', error.message);
    });

    this.socket.on('disconnect', (reason) => {
      console.log('[IpcBridge] Socket.IO disconnected:', reason);
      this.socketConnected = false;
    });

    this.socket.on('connection-established', (data) => {
      console.log('[IpcBridge] Connection confirmed by backend:', data);
    });

    this.socket.on('llm.chunk', (data) => {
      this.sendToWindow('chat', 'llm:chunk', data);
    });

    this.socket.on('live2d.action', (data) => {
      this.sendToWindow('live2d', 'live2d:action', data);
    });

    this.socket.on('audio.stream', (data) => {
      this.sendToWindow('live2d', 'audio:stream', data);
    });

    this.socket.on('audio_with_expression', (data) => {
      this.sendToWindow('live2d', 'audio:with-expression', data);
    });

    this.socket.on('chat.message', (data) => {
      this.sendToWindow('chat', 'chat:message', data);
    });

    this.socket.on('sentence', (data) => {
      const chunkData = {
        text: data.text || '',
        seq: data.seq || 0,
        is_complete: data.text === '' || data.is_complete
      };
      console.log('[IpcBridge] sentence -> llm:chunk:', chunkData.text?.substring(0, 20) || '(empty)');
      this.sendToWindow('chat', 'llm:chunk', chunkData);
    });

    this.socket.on('control', (data) => {
      console.log('[IpcBridge] control event:', data);
      if (data.signal === 'conversation-end') {
        this.sendToWindow('chat', 'chat:message', { type: 'complete' });
      }
    });

    this.socket.on('transcript', (data) => {
      console.log('[IpcBridge] transcript event:', data.text?.substring(0, 30));
      this.sendToWindow('chat', 'chat:transcript', data);
    });

    this.socket.on('stop_audio', (data) => {
      console.log('[IpcBridge] stop_audio event');
      this.sendToWindow('live2d', 'audio:stop', data);
    });
  }

  /**
   * Send message to specific window
   * @param {string} windowType - Window type ('live2d' or 'chat')
   * @param {string} channel - IPC channel
   * @param {*} data - Data to send
   */
  sendToWindow(windowType, channel, data) {
    const window = this.windowManager.getWindow(windowType);
    if (window && !window.isDestroyed()) {
      window.webContents.send(channel, data);
    }
  }

  /**
   * Send message to backend
   * @param {string} event - Event name
   * @param {Object} data - Event data
   */
  sendToBackend(event, data) {
    if (this.socketConnected && this.socket.connected) {
      this.socket.emit(event, data);
    } else {
      this.messageQueue.push({ event, data });
      console.log('[IpcBridge] Message queued (Socket.IO not connected):', event);
    }
  }

  /**
   * Legacy method for backward compatibility
   * @param {Object} message - Message with event and data
   */
  send(message) {
    this.sendToBackend(message.event, message.data);
  }

  /**
   * Get window by type
   * @param {string} type - Window type
   * @returns {BrowserWindow|null} Window instance
   */
  getWindow(type) {
    return this.windowManager.getWindow(type);
  }

  /** Disconnect and cleanup */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}

module.exports = IpcBridge;
