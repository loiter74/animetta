/**
 * LipSyncController - Drive lip sync from volume envelope data
 *
 * Backend sends volumes array sampled at 50Hz (every 20ms)
 */

export class LipSyncController {
  constructor() {
    this._timer = null;
    this._animationFrame = null;
    this._currentIndex = 0;
    this._volumes = [];
    this._startTime = 0;
    this._sampleRate = 50; // Hz
    this._isRunning = false;
  }

  /**
   * Start lip sync animation
   * @param {number[]} volumes - Volume envelope array (0-1)
   * @param {Function} onVolume - Callback for each volume sample (volume: number) => void
   * @param {number} sampleRate - Sample rate in Hz (default 50)
   */
  start(volumes, onVolume, sampleRate = 50) {
    this.stop();

    if (!volumes || volumes.length === 0) {
      console.warn('[LipSyncController] No volume data');
      return;
    }

    this._volumes = volumes;
    this._sampleRate = sampleRate;
    this._currentIndex = 0;
    this._startTime = performance.now();
    this._isRunning = true;

    const intervalMs = 1000 / sampleRate;

    // Use requestAnimationFrame for smoother animation
    const tick = () => {
      if (!this._isRunning) return;

      const elapsed = performance.now() - this._startTime;
      const expectedIndex = Math.floor((elapsed / 1000) * sampleRate);

      // Catch up to expected index (in case of frame drops)
      while (this._currentIndex <= expectedIndex && this._currentIndex < this._volumes.length) {
        const volume = this._volumes[this._currentIndex];
        if (typeof onVolume === 'function') {
          onVolume(volume);
        }
        this._currentIndex++;
      }

      // Check if finished
      if (this._currentIndex >= this._volumes.length) {
        this.stop();
        // Set mouth to closed at end
        if (typeof onVolume === 'function') {
          onVolume(0);
        }
        return;
      }

      this._animationFrame = requestAnimationFrame(tick);
    };

    this._animationFrame = requestAnimationFrame(tick);
    // console.log('[LipSyncController] Started with', volumes.length, 'samples');
  }

  /**
   * Stop lip sync animation
   */
  stop() {
    this._isRunning = false;

    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }

    if (this._animationFrame) {
      cancelAnimationFrame(this._animationFrame);
      this._animationFrame = null;
    }

    this._volumes = [];
    this._currentIndex = 0;
  }

  /**
   * Check if currently running
   */
  get isRunning() {
    return this._isRunning;
  }
}
