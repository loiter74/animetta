/**
 * ExpressionScheduler - Schedule expression changes from timeline segments
 *
 * segments format: [{emotion, start_time, end_time, intensity}]
 */

export class ExpressionScheduler {
  constructor() {
    this._timers = [];
    this._isRunning = false;
  }

  /**
   * Start expression scheduling
   * @param {Array} segments - Expression timeline segments
   * @param {Function} onExpression - Callback (emotion: string, intensity: number) => void
   */
  start(segments, onExpression) {
    this.stop();

    if (!segments || segments.length === 0) {
      console.warn('[ExpressionScheduler] No segments');
      return;
    }

    this._isRunning = true;

    // Schedule each segment
    for (const seg of segments) {
      const startTimeMs = (seg.start_time || 0) * 1000;
      const emotion = seg.emotion || 'neutral';
      const intensity = seg.intensity || 1.0;

      const timer = setTimeout(() => {
        if (!this._isRunning) return;

        // console.log(`[ExpressionScheduler] ${emotion} at ${startTimeMs}ms (intensity: ${intensity})`);
        if (typeof onExpression === 'function') {
          onExpression(emotion, intensity);
        }
      }, startTimeMs);

      this._timers.push(timer);
    }

    // console.log('[ExpressionScheduler] Started with', segments.length, 'segments');
  }

  /**
   * Stop all scheduled expressions
   */
  stop() {
    this._isRunning = false;

    for (const timer of this._timers) {
      clearTimeout(timer);
    }
    this._timers = [];
  }

  /**
   * Check if currently running
   */
  get isRunning() {
    return this._isRunning;
  }
}
