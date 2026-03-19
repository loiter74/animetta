/**
 * ExpressionTimelinePlayer - 表情时间轴播放器
 *
 * 根据时间轴播放 Live2D 参数变化
 */

export class ExpressionTimelinePlayer {
  constructor(expressionController) {
    this.expressionController = expressionController;

    // 播放状态
    this.isPlaying = false;
    this.currentFrameIndex = 0;
    this.startTime = 0;
    this.animationFrameId = null;

    // 时间轴数据
    this.frames = [];
    this.totalDuration = 0;

    // 当前参数状态
    this.currentParameters = new Map(); // param_name -> { value, targetValue, startTime, duration }
  }

  /**
   * 加载时间轴数据
   * @param {Object} data - { frames: [...], total_duration: number }
   */
  loadTimeline(data) {
    this.frames = data.frames || [];
    this.totalDuration = data.total_duration || 0;

    console.log('[ExpressionTimelinePlayer] 加载时间轴:', {
      frames: this.frames.length,
      duration: this.totalDuration
    });

    // 重置状态
    this.stop();
  }

  /**
   * 播放时间轴
   * @param {number} startTime - 开始时间偏移（秒）
   */
  play(startTime = 0) {
    if (this.frames.length === 0) {
      console.warn('[ExpressionTimelinePlayer] 没有时间轴数据');
      return;
    }

    this.isPlaying = true;
    this.startTime = performance.now() / 1000 - startTime;
    this.currentFrameIndex = 0;

    console.log('[ExpressionTimelinePlayer] 开始播放');

    this._tick();
  }

  /**
   * 停止播放
   */
  stop() {
    this.isPlaying = false;

    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }

    console.log('[ExpressionTimelinePlayer] 停止播放');
  }

  /**
   * 重置状态
   */
  reset() {
    this.stop();
    this.currentFrameIndex = 0;
    this.currentParameters.clear();
  }

  /**
   * 主循环
   */
  _tick() {
    if (!this.isPlaying) return;

    const currentTime = performance.now() / 1000 - this.startTime;

    // 检查是否播放完成
    if (currentTime >= this.totalDuration) {
      console.log('[ExpressionTimelinePlayer] 播放完成');
      this.stop();
      return;
    }

    // 更新参数
    this._updateParameters(currentTime);

    // 应用到模型
    this._applyParameters();

    // 继续下一帧
    this.animationFrameId = requestAnimationFrame(() => this._tick());
  }

  /**
   * 更新参数值
   * @param {number} currentTime - 当前时间（秒）
   */
  _updateParameters(currentTime) {
    // 找到当前应该激活的帧
    while (
      this.currentFrameIndex < this.frames.length &&
      this.frames[this.currentFrameIndex].timestamp <= currentTime
    ) {
      const frame = this.frames[this.currentFrameIndex];

      // 更新参数目标值
      for (const param of frame.parameters) {
        this.currentParameters.set(param.name, {
          targetValue: param.value,
          startTime: currentTime,
          duration: param.duration,
          startValue: this.currentParameters.get(param.name)?.currentValue || param.value
        });
      }

      this.currentFrameIndex++;
    }

    // 计算当前参数值（平滑过渡）
    for (const [name, state] of this.currentParameters) {
      const elapsed = currentTime - state.startTime;
      const progress = Math.min(elapsed / state.duration, 1.0);

      // 使用缓动函数
      const eased = this._easeInOutCubic(progress);

      state.currentValue = state.startValue + (state.targetValue - state.startValue) * eased;

      // 移除过期的参数
      if (progress >= 1.0) {
        this.currentParameters.delete(name);
      }
    }
  }

  /**
   * 应用参数到模型
   */
  _applyParameters() {
    for (const [name, state] of this.currentParameters) {
      this.expressionController.setParam(name, state.currentValue);
    }
  }

  /**
   * 缓动函数 - easeInOutCubic
   * @param {number} t - 进度 (0-1)
   * @returns {number} 缓动后的值
   */
  _easeInOutCubic(t) {
    return t < 0.5
      ? 4 * t * t * t
      : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  /**
   * 获取播放状态
   */
  getStatus() {
    return {
      isPlaying: this.isPlaying,
      currentTime: this.isPlaying ? (performance.now() / 1000 - this.startTime) : 0,
      totalDuration: this.totalDuration,
      progress: this.isPlaying
        ? ((performance.now() / 1000 - this.startTime) / this.totalDuration)
        : 0
    };
  }

  /**
   * 销毁
   */
  destroy() {
    this.stop();
    this.frames = [];
    this.currentParameters.clear();
  }
}
