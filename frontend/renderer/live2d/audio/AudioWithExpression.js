/**
 * AudioWithExpression - Coordinator for audio playback with lip sync and expressions
 *
 * Handles complete audio_with_expression events from backend
 */

import { AudioPlayer } from './AudioPlayer.js';
import { LipSyncController } from './LipSyncController.js';
import { ExpressionScheduler } from './ExpressionScheduler.js';

export class AudioWithExpression {
  constructor(options = {}) {
    // Callbacks
    this.setMouthOpen = options.setMouthOpen || (() => {});
    this.setExpression = options.setExpression || (() => {});
    this.onPlaybackStart = options.onPlaybackStart;
    this.onPlaybackEnd = options.onPlaybackEnd;
    this.onError = options.onError;

    // Components
    this.player = new AudioPlayer();
    this.lipSync = new LipSyncController();
    this.scheduler = new ExpressionScheduler();

    // State
    this._isPlaying = false;
    this._queue = [];
    this._isProcessingQueue = false;
  }

  /**
   * Play audio with expression data
   * @param {Object} data - Event data from backend
   * @param {string} data.audio_data - Base64 encoded audio
   * @param {string} data.format - Audio format
   * @param {number[]} data.volumes - Volume envelope for lip sync
   * @param {Object} data.expressions - Expression timeline
   */
  async play(data) {
    // Debug: log received data structure
    console.log('[AudioWithExpression] Received data:', {
      keys: Object.keys(data || {}),
      has_audio_data: !!data?.audio_data,
      audio_data_length: data?.audio_data?.length,
      format: data?.format,
      volumes_length: data?.volumes?.length,
      seq: data?.seq,
    });

    const { audio_data, format, volumes, expressions, seq } = data;

    if (!audio_data) {
      console.warn('[AudioWithExpression] No audio data in payload:', data);
      return;
    }

    // Stop current playback
    this.stop();

    this._isPlaying = true;

    try {
      // Notify start
      if (this.onPlaybackStart) {
        this.onPlaybackStart(seq);
      }

      // Start lip sync controller
      if (volumes && volumes.length > 0) {
        this.lipSync.start(volumes, (v) => {
          this.setMouthOpen(v);
        });
      }

      // Start expression scheduler
      if (expressions && expressions.segments) {
        this.scheduler.start(expressions.segments, (emotion, intensity) => {
          this.setExpression(emotion);
        });
      }

      // Play audio (waits for completion)
      await this.player.play(audio_data, format || 'mp3');

    } catch (error) {
      console.error('[AudioWithExpression] Playback error:', error);
      if (this.onError) {
        this.onError(error);
      }
    } finally {
      // Cleanup
      this.lipSync.stop();
      this.scheduler.stop();

      // Reset mouth to closed
      this.setMouthOpen(0);

      this._isPlaying = false;

      // Notify end
      if (this.onPlaybackEnd) {
        this.onPlaybackEnd();
      }

      // Process queue
      this._processQueue();
    }
  }

  /**
   * Queue audio for sequential playback
   */
  queue(data) {
    this._queue.push(data);
    this._processQueue();
  }

  /**
   * Process queued audio
   */
  async _processQueue() {
    if (this._isProcessingQueue || this._isPlaying) return;
    if (this._queue.length === 0) return;

    this._isProcessingQueue = true;

    while (this._queue.length > 0) {
      const data = this._queue.shift();
      await this.play(data);
    }

    this._isProcessingQueue = false;
  }

  /**
   * Stop current playback and clear queue
   */
  stop() {
    this.player.stop();
    this.lipSync.stop();
    this.scheduler.stop();
    this._isPlaying = false;

    // Reset mouth
    this.setMouthOpen(0);
  }

  /**
   * Clear queued audio
   */
  clearQueue() {
    this._queue = [];
  }

  /**
   * Check if currently playing
   */
  get isPlaying() {
    return this._isPlaying;
  }

  /**
   * Cleanup resources
   */
  destroy() {
    this.stop();
    this.clearQueue();
    this.player.destroy();
  }
}
