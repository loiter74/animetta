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
    },

    // Listen for audio with expression (TTS playback)
    onAudioWithExpression: (callback) => {
      const listener = (_event, data) => callback(data);
      ipcRenderer.on('audio:with-expression', listener);
      return () => ipcRenderer.removeListener('audio:with-expression', listener);
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

    // 🔧 新增: 发送音频数据块 (高频调用，用 send 不用 invoke)
    sendAudioChunk: (audioData) => ipcRenderer.send('chat:sendAudioChunk', audioData),

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
  },

  // Display controls (新增)
  display: {
    // 缩放控制
    setScaleStrategy: (strategy) => ipcRenderer.invoke('display:setScaleStrategy', strategy),
    getScaleStrategy: () => ipcRenderer.invoke('display:getScaleStrategy'),
    getAvailableStrategies: () => ipcRenderer.invoke('display:getAvailableStrategies'),
    zoom: (delta) => ipcRenderer.invoke('display:zoom', delta),
    setUserScale: (scale) => ipcRenderer.invoke('display:setUserScale', scale),
    resetScale: () => ipcRenderer.invoke('display:resetScale'),

    // 模型位置
    moveModel: (dx, dy) => ipcRenderer.invoke('display:moveModel', dx, dy),
    resetModelPosition: () => ipcRenderer.invoke('display:resetModelPosition'),

    // 背景控制 (Phase 2)
    setBackgroundMode: (mode, options) => ipcRenderer.invoke('display:setBackgroundMode', mode, options),
    getBackgroundMode: () => ipcRenderer.invoke('display:getBackgroundMode'),
    setBackgroundColor: (color) => ipcRenderer.invoke('display:setBackgroundColor', color),
    setBackgroundOpacity: (opacity) => ipcRenderer.invoke('display:setBackgroundOpacity', opacity),
    setBackgroundImage: (path) => ipcRenderer.invoke('display:setBackgroundImage', path),
    setBackgroundVideo: (path) => ipcRenderer.invoke('display:setBackgroundVideo', path),
    cycleBackgroundMode: () => ipcRenderer.invoke('display:cycleBackgroundMode'),
    getAvailableBackgroundModes: () => ipcRenderer.invoke('display:getAvailableBackgroundModes'),

    // 窗口控制
    setAlwaysOnTop: (value) => ipcRenderer.invoke('display:setAlwaysOnTop', value),
    setClickThrough: (value) => ipcRenderer.invoke('display:setClickThrough', value),
    moveWindow: (x, y) => ipcRenderer.invoke('display:moveWindow', x, y),
    resizeWindow: (width, height) => ipcRenderer.invoke('display:resizeWindow', width, height),
    getWindowPosition: () => ipcRenderer.invoke('display:getWindowPosition'),

    // 配置持久化
    getConfig: () => ipcRenderer.invoke('display:getConfig'),
    saveConfig: (config) => ipcRenderer.invoke('display:saveConfig', config),
    getWindowState: () => ipcRenderer.invoke('display:getWindowState'),
    saveWindowState: (state) => ipcRenderer.invoke('display:saveWindowState', state),
    resetConfig: () => ipcRenderer.invoke('display:resetConfig'),
    exportConfig: () => ipcRenderer.invoke('display:exportConfig'),
    importConfig: (json) => ipcRenderer.invoke('display:importConfig', json),

    // 状态
    getState: () => ipcRenderer.invoke('display:getState'),
    getModelInfo: () => ipcRenderer.invoke('display:getModelInfo'),

    // 快捷键控制 (Phase 3)
    setHotkey: (action, key, modifiers) => ipcRenderer.invoke('display:setHotkey', action, key, modifiers),
    getHotkeys: () => ipcRenderer.invoke('display:getHotkeys'),
    resetHotkeys: () => ipcRenderer.invoke('display:resetHotkeys'),
    setHotkeysEnabled: (enabled) => ipcRenderer.invoke('display:setHotkeysEnabled', enabled),
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
  },

  // Display shortcuts (新增)
  display: {
    // 缩放策略
    strategy: (name) => window.electronAPI.display.setScaleStrategy(name),
    zoomIn: () => window.electronAPI.display.zoom(1),
    zoomOut: () => window.electronAPI.display.zoom(-1),
    reset: () => {
      window.electronAPI.display.resetScale();
      window.electronAPI.display.resetModelPosition();
    },

    // 位置移动
    move: (dx, dy) => window.electronAPI.display.moveModel(dx, dy),
    up: () => window.electronAPI.display.moveModel(0, -10),
    down: () => window.electronAPI.display.moveModel(0, 10),
    left: () => window.electronAPI.display.moveModel(-10, 0),
    right: () => window.electronAPI.display.moveModel(10, 0),

    // 窗口
    alwaysOnTop: (value) => window.electronAPI.display.setAlwaysOnTop(value),
    clickThrough: (value) => window.electronAPI.display.setClickThrough(value),

    // 背景 (Phase 2)
    background: (mode) => window.electronAPI.display.setBackgroundMode(mode),
    backgroundTransparent: () => window.electronAPI.display.setBackgroundMode('transparent'),
    backgroundGreen: () => window.electronAPI.display.setBackgroundMode('color', { color: '#00ff00' }),
    backgroundWhite: () => window.electronAPI.display.setBackgroundMode('color', { color: '#ffffff' }),
    backgroundCycle: () => window.electronAPI.display.cycleBackgroundMode(),

    // 状态
    info: () => window.electronAPI.display.getModelInfo()
  }
});

console.log('[Preload] Electron APIs exposed');
