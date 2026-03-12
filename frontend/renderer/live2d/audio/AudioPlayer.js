/**
 * AudioPlayer - Base64 audio decoding and Web Audio API playback
 */

export class AudioPlayer {
  constructor() {
    this.audioContext = null;
    this.currentSource = null;
    this.isPlaying = false;
  }

  /**
   * Get or create AudioContext
   */
  _getAudioContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    // Resume if suspended (browser autoplay policy)
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
    return this.audioContext;
  }

  /**
   * Play base64 encoded audio
   * @param {string} base64Data - Base64 encoded audio data
   * @param {string} format - Audio format (mp3, wav, etc.)
   * @returns {Promise<void>} Resolves when playback ends
   */
  async play(base64Data, format = 'mp3') {
    // Stop any current playback
    this.stop();

    const ctx = this._getAudioContext();

    try {
      // Decode base64 to binary
      const binary = atob(base64Data);
      const buffer = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        buffer[i] = binary.charCodeAt(i);
      }

      // Create blob and array buffer for decoding
      const mimeType = this._getMimeType(format);
      const blob = new Blob([buffer], { type: mimeType });
      const arrayBuffer = await blob.arrayBuffer();

      // Decode audio data
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

      // Create and configure source
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      // Store reference for stopping
      this.currentSource = source;
      this.isPlaying = true;

      // Return promise that resolves when playback ends
      return new Promise((resolve) => {
        source.onended = () => {
          this.isPlaying = false;
          this.currentSource = null;
          resolve();
        };

        source.start(0);
      });
    } catch (error) {
      console.error('[AudioPlayer] Playback error:', error);
      this.isPlaying = false;
      throw error;
    }
  }

  /**
   * Stop current playback
   */
  stop() {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch (e) {
        // Already stopped
      }
      this.currentSource = null;
    }
    this.isPlaying = false;
  }

  /**
   * Get MIME type for audio format
   */
  _getMimeType(format) {
    const types = {
      mp3: 'audio/mpeg',
      mpeg: 'audio/mpeg',
      wav: 'audio/wav',
      wave: 'audio/wav',
      ogg: 'audio/ogg',
      webm: 'audio/webm',
    };
    return types[format.toLowerCase()] || 'audio/mpeg';
  }

  /**
   * Cleanup resources
   */
  destroy() {
    this.stop();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}
