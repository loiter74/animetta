/**
 * Live2DIpcListeners - IPC event listener registration and cleanup
 */

export class Live2DIpcListeners {
  constructor(handlers) {
    this.handlers = handlers;
    this._cleanupFns = [];
  }

  /**
   * Setup all IPC listeners
   */
  setup() {
    if (!window.electronAPI || !window.electronAPI.live2d) {
      console.warn('[Live2DIpcListeners] Electron API not available');
      return;
    }

    // Clean up any existing listeners first
    this.cleanup();

    // Listen for actions from backend
    const cleanupAction = window.electronAPI.live2d.onAction((action) => {
      this.handlers.onAction(action);
    });
    if (cleanupAction) this._cleanupFns.push(cleanupAction);

    // Listen for audio stream (lip sync)
    const cleanupAudio = window.electronAPI.live2d.onAudioStream((data) => {
      this.handlers.onAudioStream(data);
    });
    if (cleanupAudio) this._cleanupFns.push(cleanupAudio);

    console.log('[Live2DIpcListeners] Setup complete');
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
        console.warn('[Live2DIpcListeners] Error cleaning up listener:', e);
      }
    });
    this._cleanupFns = [];
    console.log('[Live2DIpcListeners] Cleanup complete');
  }
}
