/**
 * LipSync - Mouth animation synchronized with audio
 * Uses PIXI ticker instead of separate rAF loop
 */

// Common mouth parameter names used by different Live2D models
const MOUTH_PARAM_CANDIDATES = [
  'ParamMouthOpenY',
  'ParamMouthOpen',
  'PARAM_MOUTH_OPEN',
];

export class LipSync {
  constructor(ticker) {
    this.ticker = ticker;
    this.model = null;

    // Lip sync state
    this.mouthOpenValue = 0;
    this.targetMouthOpen = 0;

    // Detected parameter name (cached after first detection)
    this._mouthParamName = null;
    this._mouthFormParamName = null;

    // Bind update method
    this._update = this._update.bind(this);

    // Register with PIXI ticker (not rAF!)
    ticker.add(this._update);
  }

  /**
   * Set the model to control
   * @param {PIXI.live2d.Live2DModel} model
   */
  setModel(model) {
    this.model = model;
    // Reset cached param names for new model
    this._mouthParamName = null;
    this._mouthFormParamName = null;
  }

  /**
   * Set target mouth openness
   * @param {number} value - Target value (0-1)
   */
  setTarget(value) {
    this.targetMouthOpen = Math.max(0, Math.min(1, value));
  }

  /**
   * Update loop (called by PIXI ticker)
   */
  _update() {
    if (!this.model) return;

    // Smooth interpolation
    const smoothing = 0.3;
    this.mouthOpenValue += (this.targetMouthOpen - this.mouthOpenValue) * smoothing;

    // Detect and cache mouth param name
    const mouthParam = this._detectMouthParam();
    if (mouthParam) {
      this._setParam(mouthParam, this.mouthOpenValue);
    }

    // Also try mouth form for shape
    const formParam = this._detectMouthFormParam();
    if (formParam) {
      this._setParam(formParam, this.mouthOpenValue * 0.5);
    }
  }

  /**
   * Detect mouth open parameter name (cached)
   * @returns {string|null}
   */
  _detectMouthParam() {
    if (this._mouthParamName !== null) {
      return this._mouthParamName;
    }

    for (const name of MOUTH_PARAM_CANDIDATES) {
      if (this._hasParam(name)) {
        this._mouthParamName = name;
        console.log('[LipSync] Detected mouth param:', name);
        return name;
      }
    }

    // No param found, cache null to avoid repeated checks
    this._mouthParamName = null;
    return null;
  }

  /**
   * Detect mouth form parameter name (cached)
   * @returns {string|null}
   */
  _detectMouthFormParam() {
    if (this._mouthFormParamName !== null) {
      return this._mouthFormParamName;
    }

    if (this._hasParam('ParamMouthForm')) {
      this._mouthFormParamName = 'ParamMouthForm';
      return this._mouthFormParamName;
    }

    return null;
  }

  /**
   * Check if model has parameter
   * @param {string} paramName
   * @returns {boolean}
   */
  _hasParam(paramName) {
    if (!this.model?.internalModel?.coreModel) return false;
    const index = this.model.internalModel.coreModel.getParameterIndex(paramName);
    return index >= 0;
  }

  /**
   * Set parameter value
   * @param {string} paramName
   * @param {number} value
   */
  _setParam(paramName, value) {
    if (!this.model?.internalModel?.coreModel) return;

    const index = this.model.internalModel.coreModel.getParameterIndex(paramName);
    if (index >= 0) {
      this.model.internalModel.coreModel.setParameterValueByIndex(index, value);
    }
  }

  /**
   * Cleanup (remove from ticker)
   */
  destroy() {
    this.ticker.remove(this._update);
  }
}
