/**
 * ExpressionController - 合并表情、动作、口型控制
 * 包含: LipSync + ExpressionController + ActionExecutor + TimelinePlayer
 */

import { ExpressionTimelinePlayer } from './ExpressionTimelinePlayer.js';

// 口型参数候选
const MOUTH_PARAMS = ['ParamMouthOpenY', 'ParamMouthOpen', 'PARAM_MOUTH_OPEN'];

// 事件日志记录
const EVENT_LOG = true;
const logEvent = (category, action, ...args) => {
  if (EVENT_LOG) {
    const timestamp = Date.now();
    const timeStr = new Date(timestamp).toLocaleTimeString('zh-CN', { hour12: false }) + '.' + String(timestamp % 1000).padStart(3, '0');
    console.log(`[EC ${timeStr}] ${action}`, ...args);
  }
};

export class ExpressionController {
  constructor(ticker, modelLoader) {
    this.ticker = ticker;
    this.modelLoader = modelLoader;

    // === LipSync 状态 ===
    this.mouthValue = 0;
    this.targetMouth = 0;
    this._mouthParam = null;

    // === 表情状态 ===
    this.model = null;

    // === TimelinePlayer ===
    this.timelinePlayer = new ExpressionTimelinePlayer(this);

    // 绑定更新
    this._update = this._update.bind(this);
    ticker.add(this._update);

    logEvent('INIT', 'ExpressionController created');
  }

  // ====== LipSync ======
  setMouthTarget(value) {
    this.targetMouth = Math.max(0, Math.min(1, value));
    logEvent('LIPSYNC', 'setMouthTarget', value.toFixed(3), 'current:', this.mouthValue.toFixed(3));
  }

  _update() {
    const model = this.modelLoader?.model;
    if (!model) return;

    // 快速响应的平滑插值：基础系数 0.5，根据差距动态调整
    const delta = Math.abs(this.targetMouth - this.mouthValue);
    const factor = 0.5 + 0.4 * Math.min(delta / 0.3, 1.0);
    this.mouthValue += (this.targetMouth - this.mouthValue) * factor;

    // 检测口型参数
    if (!this._mouthParam) {
      for (const name of MOUTH_PARAMS) {
        const idx = model.internalModel?.coreModel?.getParameterIndex(name);
        if (idx >= 0) { this._mouthParam = name; break; }
      }
    }

    // 设置口型
    if (this._mouthParam) {
      const idx = model.internalModel.coreModel.getParameterIndex(this._mouthParam);
      if (idx >= 0) model.internalModel.coreModel.setParameterValueByIndex(idx, this.mouthValue);
    }
  }

  // ====== Expression ======
  setModel(model) {
    this.model = model;
    this._mouthParam = null; // 重置缓存
    logEvent('MODEL', 'Model loaded', model?._model??.name || 'unknown');
  }

  setExpression(name) {
    logEvent('EXPRESSION', 'setExpression', name);
    const model = this.model || this.modelLoader?.model;
    if (!model?.internalModel?.motionManager?.expressionNames) {
      logEvent('EXPRESSION', 'No expression names available');
      return;
    }

    const idx = model.internalModel.motionManager.expressionNames.indexOf(name);
    if (idx >= 0) {
      model.expression(idx);
      logEvent('EXPRESSION', 'Expression applied', name, 'idx:', idx);
    } else {
      logEvent('EXPRESSION', 'Expression not found', name, 'available:', model.internalModel.motionManager.expressionNames);
    }
  }

  playMotion(group, index) {
    logEvent('MOTION', 'playMotion', group, index);
    const model = this.model || this.modelLoader?.model;
    if (!model) return;
    model.motion(group, index);
  }

  /**
   * 设置单个参数
   * @param {string} name - 参数名
   * @param {number} value - 参数值
   */
  setParam(name, value) {
    logEvent('PARAM', 'setParam', name, '=', value.toFixed(3));
    const model = this.model || this.modelLoader?.model;
    if (!model?.internalModel?.coreModel) return;

    const idx = model.internalModel.coreModel.getParameterIndex(name);
    if (idx >= 0) {
      model.internalModel.coreModel.setParameterValueByIndex(idx, value);
    }
  }

  /**
   * 批量设置参数（用于表情帧）
   * @param {Array} parameters - [{ name, value }, ...]
   */
  setParameters(parameters) {
    logEvent('PARAM', 'setParameters', `${parameters.length} params`);
    for (const param of parameters) {
      this.setParam(param.name, param.value);
    }
  }

  enableTap(callback) {
    const model = this.model || this.modelLoader?.model;
    if (!model) return;

    model.interactive = true;
    model.on('pointertap', () => {
      callback ? callback() : this.playMotion('Tap', 0);
    });
  }

  // ====== TimelinePlayer ======
  /**
   * 加载并播放表情时间轴（参数映射模式）
   * @param {Object} data - { frames: [...], total_duration: number }
   * @param {number} startTime - 开始时间偏移
   */
  playParameterTimeline(data, startTime = 0) {
    logEvent('TIMELINE', 'playParameterTimeline', `frames: ${data.frames?.length || 0}, duration: ${data.total_duration}s`);
    this.timelinePlayer.loadTimeline(data);
    this.timelinePlayer.play(startTime);
  }

  /**
   * 停止时间轴播放
   */
  stopTimeline() {
    logEvent('TIMELINE', 'stopTimeline');
    this.timelinePlayer.stop();
  }

  /**
   * 获取时间轴播放状态
   */
  getTimelineStatus() {
    return this.timelinePlayer.getStatus();
  }

  // ====== ActionExecutor ======
  execute(action) {
    logEvent('ACTION', 'execute', action.type, action);
    switch (action.type) {
      case 'expression': this.setExpression(action.name); break;
      case 'motion': this.playMotion(action.group, action.index); break;
      case 'param': this.setParam(action.name, action.value); break;
      case 'sequence': this._runSequence(action.actions); break;
    }
  }

  _runSequence(actions) {
    let delay = 0;
    for (const action of actions) {
      if (action.type === 'wait') { delay += action.ms || 0; }
      else {
        const captured = action;
        setTimeout(() => this.execute(captured), delay);
      }
    }
  }

  destroy() {
    logEvent('DESTROY', 'ExpressionController destroying');
    this.ticker.remove(this._update);
    this.timelinePlayer.destroy();
  }
}
