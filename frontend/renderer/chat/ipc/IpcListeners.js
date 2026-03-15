/**
 * IpcListeners - IPC event listener registration and cleanup
 */

export class IpcListeners {
  constructor(handlers) {
    this.handlers = handlers;
    this._cleanupFns = [];
  }

  /**
   * Setup all IPC listeners
   */
  setup() {
    if (!window.electronAPI || !window.electronAPI.chat) {
      console.warn('[IpcListeners] Electron API not available');
      return;
    }

    // Clean up any existing listeners first
    this.cleanup();

    // Listen for LLM chunks (streaming response)
    const cleanupChunk = window.electronAPI.chat.onLlmChunk((data) => {
      this.handlers.onLlmChunk(data);
    });
    if (cleanupChunk) this._cleanupFns.push(cleanupChunk);

    // Listen for messages
    const cleanupMessage = window.electronAPI.chat.onMessage((data) => {
      this.handlers.onMessage(data);
    });
    if (cleanupMessage) this._cleanupFns.push(cleanupMessage);

    // Listen for speaking state
    const cleanupSpeaking = window.electronAPI.chat.onSpeaking((isSpeaking) => {
      this.handlers.onSpeaking(isSpeaking);
    });
    if (cleanupSpeaking) this._cleanupFns.push(cleanupSpeaking);

    // Listen for style transfer state from backend
    if (window.electronAPI.chat.onStyleTransfer) {
      const cleanupStyle = window.electronAPI.chat.onStyleTransfer((enabled) => {
        this.handlers.onStyleTransfer(enabled);
      });
      if (cleanupStyle) this._cleanupFns.push(cleanupStyle);
    }

    // Listen for user transcript (ASR result from voice input)
    if (window.electronAPI.chat.onTranscript) {
      const cleanupTranscript = window.electronAPI.chat.onTranscript((data) => {
        this.handlers.onTranscript(data);
      });
      if (cleanupTranscript) this._cleanupFns.push(cleanupTranscript);
    }

    // console.log('[IpcListeners] Setup complete');
  }

  /**
   * Cleanup all IPC listeners
   */
  cleanup() {
    this._cleanupFns.forEach((cleanup) => {
      try {
        if (typeof cleanup === 'function') {
          cleanup();
        }
      } catch (e) {
        console.warn('[IpcListeners] Error cleaning up listener:', e);
      }
    });
    this._cleanupFns = [];
    console.log('[IpcListeners] Cleanup complete');
  }
}
