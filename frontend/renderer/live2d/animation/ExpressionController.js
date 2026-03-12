/**
 * ExpressionController - Expression and motion control
 */

export class ExpressionController {
  constructor() {
    this.model = null;
  }

  /**
   * Set the model to control
   * @param {PIXI.live2d.Live2DModel} model
   */
  setModel(model) {
    this.model = model;
  }

  /**
   * Set expression by name
   * @param {string} expressionName
   */
  setExpression(expressionName) {
    if (!this.model) {
      console.warn('[ExpressionController] No model loaded, cannot set expression');
      return;
    }

    // Defensive check for model internals
    const internalModel = this.model.internalModel;
    if (!internalModel?.motionManager?.expressionNames) {
      console.warn('[ExpressionController] Model does not support expressions');
      return;
    }

    const expressionIndex = internalModel.motionManager.expressionNames.indexOf(
      expressionName
    );

    if (expressionIndex >= 0) {
      this.model.expression(expressionIndex);
      console.log('[ExpressionController] Expression:', expressionName);
    } else {
      console.warn('[ExpressionController] Expression not found:', expressionName);
    }
  }

  /**
   * Play motion
   * @param {string} group - Motion group name
   * @param {number} index - Motion index within group
   */
  playMotion(group, index) {
    if (!this.model) return;

    this.model.motion(group, index);
    console.log('[ExpressionController] Motion:', group, index);
  }

  /**
   * Set model parameter directly
   * @param {string} paramName - Parameter name
   * @param {number} value - Parameter value
   */
  setParam(paramName, value) {
    if (!this.model?.internalModel?.coreModel) return;

    const index = this.model.internalModel.coreModel.getParameterIndex(paramName);
    if (index >= 0) {
      this.model.internalModel.coreModel.setParameterValueByIndex(index, value);
    }
  }

  /**
   * Enable tap interaction
   */
  enableTapInteraction(callback) {
    if (!this.model) return;

    this.model.interactive = true;
    this.model.on('pointertap', () => {
      console.log('[ExpressionController] Model tapped');
      if (callback) {
        callback();
      } else {
        this.playMotion('Tap', 0);
      }
    });
  }
}
