/**
 * IpcBridge - 薄层 IPC 桥接
 * 只负责转发，零业务逻辑
 */

export class IpcBridge {
  constructor() {
    this.listeners = new Map();
    this._setupListeners();
  }

  _setupListeners() {
    // Live2D action listener
    const unsubscribeAction = window.electronAPI?.live2d?.onAction?.((data) => {
      this._emit('live2d:action', data);
    });

    // Audio stream listener (lip sync)
    const unsubscribeAudioStream = window.electronAPI?.live2d?.onAudioStream?.((data) => {
      this._emit('audio:stream', data);
    });

    // Audio with expression listener (TTS playback)
    const unsubscribeAudioWithExpr = window.electronAPI?.live2d?.onAudioWithExpression?.((data) => {
      this._emit('audio:with-expression', data);
    });

    // Store unsubscribers for cleanup
    this._unsubscribers = [
      unsubscribeAction,
      unsubscribeAudioStream,
      unsubscribeAudioWithExpr
    ].filter(Boolean);
  }

  on(channel, callback) {
    if (!this.listeners.has(channel)) {
      this.listeners.set(channel, new Set());
    }
    this.listeners.get(channel).add(callback);
    return () => this.off(channel, callback);
  }

  off(channel, callback) {
    this.listeners.get(channel)?.delete(callback);
  }

  _emit(channel, data) {
    this.listeners.get(channel)?.forEach(cb => {
      try { cb(data); } catch {}
    });
  }

  send(channel, data) {
    // Map channels to appropriate API calls
    if (channel === 'chat:sendMessage') {
      window.electronAPI?.chat?.sendMessage?.(data);
    }
  }

  invoke(channel, data) {
    // Map channels to appropriate API calls
    if (channel === 'live2d:loadModel') {
      return window.electronAPI?.live2d?.loadModel?.(data);
    }
    if (channel === 'app:getConfig') {
      return window.electronAPI?.getConfig?.(data);
    }
    return Promise.resolve(null);
  }

  destroy() {
    this._unsubscribers?.forEach(unsub => unsub?.());
    this.listeners.clear();
  }
}
