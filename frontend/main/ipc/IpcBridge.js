const { ipcMain } = require('electron');
const { io } = require('socket.io-client');
const { registerLive2dHandlers } = require('./handlers/live2d');
const { registerChatHandlers } = require('./handlers/chat');
const { registerDisplayHandlers } = require('./handlers/display');

/**
 * IPC Bridge - Handles inter-process communication
 * Bridges messages between renderer processes and backend services
 */
class IpcBridge {
  constructor(windowManager) {
    this.windowManager = windowManager;
    this.socket = null;
    this.socketConnected = false;
    this.messageQueue = [];

    // Initialize IPC handlers
    this._registerHandlers();

    // Initialize Socket.IO connection to backend
    this._connectSocket();
  }

  /**
   * Register all IPC handlers
   * @private
   */
  _registerHandlers() {
    // Register Live2D handlers
    registerLive2dHandlers(this);

    // Register Chat handlers
    registerChatHandlers(this);

    // Register Display handlers (新增)
    registerDisplayHandlers();

    // System handlers
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

  /**
   * Connect to backend Socket.IO server
   * @private
   */
  _connectSocket() {
    const appConfig = require('../config/appConfig');
    const wsUrl = appConfig.getWsUrl().replace('ws://', 'http://').replace('wss://', 'https://');

    console.log('[IpcBridge] Connecting to backend:', wsUrl);

    this.socket = io(wsUrl, {
      path: '/socket.io/',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 3000,
      reconnectionAttempts: Infinity
    });

    this.socket.on('connect', () => {
      console.log('[IpcBridge] Socket.IO connected');
      this.socketConnected = true;

      // Register as desktop client
      this.socket.emit('desktop_register', { client_type: 'desktop' });

      // Send queued messages
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

    // LLM streaming response
    this.socket.on('llm.chunk', (data) => {
      this.sendToWindow('chat', 'llm:chunk', data);
    });

    // Live2D action
    this.socket.on('live2d.action', (data) => {
      this.sendToWindow('live2d', 'live2d:action', data);
    });

    // Audio stream for lip sync
    this.socket.on('audio.stream', (data) => {
      this.sendToWindow('live2d', 'audio:stream', data);
    });

    // Audio with expression (TTS audio playback)
    this.socket.on('audio_with_expression', (data) => {
      this.sendToWindow('live2d', 'audio:with-expression', data);
    });

    // Chat message
    this.socket.on('chat.message', (data) => {
      this.sendToWindow('chat', 'chat:message', data);
    });

    // Sentence (text response) -> convert to llm:chunk for frontend
    this.socket.on('sentence', (data) => {
      // Convert sentence event to llm:chunk format expected by frontend
      const chunkData = {
        text: data.text || '',
        seq: data.seq || 0,
        is_complete: data.text === '' || data.is_complete
      };
      console.log('[IpcBridge] sentence -> llm:chunk:', chunkData.text?.substring(0, 20) || '(empty)');
      this.sendToWindow('chat', 'llm:chunk', chunkData);
    });

    // Control events (conversation-end to hide typing indicator)
    this.socket.on('control', (data) => {
      console.log('[IpcBridge] control event:', data);
      if (data.signal === 'conversation-end') {
        this.sendToWindow('chat', 'chat:message', { type: 'complete' });
      }
    });

    // User transcript (ASR result - display user's voice input in chat)
    this.socket.on('transcript', (data) => {
      console.log('[IpcBridge] transcript event:', data.text?.substring(0, 30));
      this.sendToWindow('chat', 'chat:transcript', data);
    });
  }

  /**
   * Handle message from backend (legacy method, now handled by socket event listeners)
   * @param {Object} message - Backend message
   * @private
   */
  _handleBackendMessage(message) {
    const { event, data } = message;

    switch (event) {
      case 'llm.chunk':
        this.sendToWindow('chat', 'llm:chunk', data);
        break;

      case 'live2d.action':
        this.sendToWindow('live2d', 'live2d:action', data);
        break;

      case 'audio.stream':
        this.sendToWindow('live2d', 'audio:stream', data);
        break;

      case 'chat.message':
        this.sendToWindow('chat', 'chat:message', data);
        break;

      // sentence is now handled by socket.on('sentence') listener above
      // Do NOT add case 'sentence' here to avoid duplicate processing

      default:
        console.log('[IpcBridge] Unknown event:', event);
    }
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
      // Queue message for later
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

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}

module.exports = IpcBridge;
