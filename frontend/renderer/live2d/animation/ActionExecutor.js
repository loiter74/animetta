/**
 * ActionExecutor - Execute Live2D actions and sequences
 * Fixed delay calculation bug
 */

export class ActionExecutor {
  constructor(expressionController) {
    this.controller = expressionController;
  }

  /**
   * Execute a single action
   * @param {Object} action - Action object
   */
  execute(action) {
    console.log('[ActionExecutor] Executing action:', action);

    switch (action.type) {
      case 'expression':
        if (action.name) {
          this.controller.setExpression(action.name);
        }
        break;

      case 'motion':
        if (action.group !== undefined && action.index !== undefined) {
          this.controller.playMotion(action.group, action.index);
        }
        break;

      case 'param':
        if (action.name !== undefined && action.value !== undefined) {
          this.controller.setParam(action.name, action.value);
        }
        break;

      case 'sequence':
        if (Array.isArray(action.actions)) {
          this._executeSequence(action.actions);
        }
        break;

      case 'wait':
        // Wait is handled in sequence, standalone wait does nothing
        break;

      default:
        console.warn('[ActionExecutor] Unknown action type:', action.type);
    }
  }

  /**
   * Execute sequence of actions with proper timing
   * @param {Array} actions - Array of action objects
   */
  _executeSequence(actions) {
    let delay = 0;

    for (const action of actions) {
      if (action.type === 'wait') {
        // Wait action adds to delay
        delay += action.ms || 0;
      } else {
        // Schedule action at current delay
        const capturedAction = action;
        setTimeout(() => {
          this.execute(capturedAction);
        }, delay);
        // Note: Removed automatic 250ms delay - caller should use 'wait' action
        // to control timing between actions explicitly
      }
    }
  }
}
