/**
 * ExpressionController - 合并表情、动作、口型控制
 * 包含: LipSync + ExpressionController + ActionExecutor
 */

// 口型参数候选
const MOUTH_PARAMS = ['ParamMouthOpenY', 'ParamMouthOpen', 'PARAM_MOUTH_OPEN'];

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

    // 绑定更新
    this._update = this._update.bind(this);
    ticker.add(this._update);
  }

  // ====== LipSync ======
  setMouthTarget(value) {
    this.targetMouth = Math.max(0, Math.min(1, value));
  }

  _update() {
    const model = this.modelLoader?.model;
    if (!model) return;

    // 平滑插值
    this.mouthValue += (this.targetMouth - this.mouthValue) * 0.3;

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
  }

  setExpression(name) {
    const model = this.model || this.modelLoader?.model;
    if (!model?.internalModel?.motionManager?.expressionNames) return;

    const idx = model.internalModel.motionManager.expressionNames.indexOf(name);
    if (idx >= 0) {
      model.expression(idx);
      console.log('[ExpressionController] Expression:', name);
    }
  }

  playMotion(group, index) {
    const model = this.model || this.modelLoader?.model;
    if (!model) return;
    model.motion(group, index);
    console.log('[ExpressionController] Motion:', group, index);
  }

  setParam(name, value) {
    const model = this.model || this.modelLoader?.model;
    if (!model?.internalModel?.coreModel) return;

    const idx = model.internalModel.coreModel.getParameterIndex(name);
    if (idx >= 0) model.internalModel.coreModel.setParameterValueByIndex(idx, value);
  }

  enableTap(callback) {
    const model = this.model || this.modelLoader?.model;
    if (!model) return;

    model.interactive = true;
    model.on('pointertap', () => {
      callback ? callback() : this.playMotion('Tap', 0);
    });
  }

  // ====== ActionExecutor ======
  execute(action) {
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
    this.ticker.remove(this._update);
  }
}
