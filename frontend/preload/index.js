/**
 * Preload Script - Exposes secure APIs to renderer processes
 * This runs in the renderer context but has access to Node.js APIs
 */
const { contextBridge, ipcRenderer } = require('electron');

/**
 * Expose protected methods that allow the renderer process to use
 * IPC without exposing the entire ipcRenderer API
 */
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  getConfig: (key) => ipcRenderer.invoke('app:getConfig', key),

  // Live2D controls
  live2d: {
    loadModel: (modelPath) => ipcRenderer.invoke('live2d:loadModel', modelPath),
    setExpression: (expressionName) =>
      ipcRenderer.invoke('live2d:setExpression', expressionName),
    playMotion: (group, index) => ipcRenderer.invoke('live2d:playMotion', group, index),
    setParam: (paramName, value) => ipcRenderer.invoke('live2d:setParam', paramName, value),
    setMouthOpen: (value) => ipcRenderer.invoke('live2d:setMouthOpen', value),
    executeAction: (action) => ipcRenderer.invoke('live2d:executeAction', action),
    getModelInfo: () => ipcRenderer.invoke('live2d:getModelInfo'),

    // Listen for actions from backend
    onAction: (callback) => {
      const listener = (_event, data) => callback(data);
      ipcRenderer.on('live2d:action', listener);
      return () => ipcRenderer.removeListener('live2d:action', listener);
    },

    // Listen for audio stream (lip sync)
    onAudioStream: (callback) => {
      const listener = (_event, data) => callback(data);
      ipcRenderer.on('audio:stream', listener);
      return () => ipcRenderer.removeListener('audio:stream', listener);
    }
  },

  // Chat controls
  chat: {
    sendMessage: (message) => ipcRenderer.invoke('chat:sendMessage', message),
    sendAudio: (audioData) => ipcRenderer.invoke('chat:sendAudio', audioData),
    startVoiceInput: () => ipcRenderer.invoke('chat:startVoiceInput'),
    stopVoiceInput: () => ipcRenderer.invoke('chat:stopVoiceInput'),
    getHistory: (limit) => ipcRenderer.invoke('chat:getHistory', limit),
    clearHistory: () => ipcRenderer.invoke('chat:clearHistory'),
    setSpeaking: (isSpeaking) => ipcRenderer.invoke('chat:setSpeaking', isSpeaking),
    setTyping: (isTyping) => ipcRenderer.invoke('chat:setTyping', isTyping),

    // Listen for LLM chunks (streaming response)
    onLlmChunk: (callback) => {
      const listener = (_event, data) => callback(data);
      ipcRenderer.on('llm:chunk', listener);
      return () => ipcRenderer.removeListener('llm:chunk', listener);
    },

    // Listen for chat messages
    onMessage: (callback) => {
      const listener = (_event, data) => callback(data);
      ipcRenderer.on('chat:message', listener);
      return () => ipcRenderer.removeListener('chat:message', listener);
    },

    // Listen for speaking state changes
    onSpeaking: (callback) => {
      const listener = (_event, data) => callback(data.isSpeaking);
      ipcRenderer.on('chat:speaking', listener);
      return () => ipcRenderer.removeListener('chat:speaking', listener);
    },

    // Style transfer control
    setStyleTransfer: (enabled) => ipcRenderer.invoke('chat:setStyleTransfer', enabled),
    onStyleTransfer: (callback) => {
      const listener = (_event, enabled) => callback(enabled);
      ipcRenderer.on('chat:styleTransfer', listener);
      return () => ipcRenderer.removeListener('chat:styleTransfer', listener);
    }
  },

  // Window controls
  window: {
    minimize: () => ipcRenderer.send('window:minimize'),
    maximize: () => ipcRenderer.send('window:maximize'),
    close: () => ipcRenderer.send('window:close')
  }
});

/**
 * Also expose a simplified API for direct use
 */
contextBridge.exposeInMainWorld('anima', {
  // Live2D shortcuts
  live2d: {
    load: (path) => window.electronAPI.live2d.loadModel(path),
    expression: (name) => window.electronAPI.live2d.setExpression(name),
    motion: (group, index) => window.electronAPI.live2d.playMotion(group, index),
    mouth: (value) => window.electronAPI.live2d.setMouthOpen(value)
  },

  // Chat shortcuts
  chat: {
    send: (text) =>
      window.electronAPI.chat.sendMessage({
        text,
        timestamp: Date.now()
      }),
    voice: {
      start: () => window.electronAPI.chat.startVoiceInput(),
      stop: () => window.electronAPI.chat.stopVoiceInput()
    }
  }
});

console.log('[Preload] Electron APIs exposed');
