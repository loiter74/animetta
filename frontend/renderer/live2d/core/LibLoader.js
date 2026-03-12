/**
 * LibLoader - Wait for PIXI and pixi-live2d-display libraries
 */

/**
 * Wait for required libraries to load
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<void>}
 */
export function waitForLibs(timeout = 10000) {
  return new Promise((resolve, reject) => {
    let timer = null;
    let resolved = false;

    const cleanup = () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    };

    const check = () => {
      if (resolved) return;

      if (typeof PIXI !== 'undefined' && PIXI.live2d?.Live2DModel) {
        resolved = true;
        cleanup();
        resolve();
      } else {
        setTimeout(check, 100);
      }
    };

    timer = setTimeout(() => {
      if (resolved) return;
      cleanup();

      if (typeof PIXI === 'undefined') {
        reject(new Error('PIXI.js failed to load'));
      } else if (!PIXI.live2d) {
        reject(new Error('pixi-live2d-display failed to load'));
      } else {
        reject(new Error('Unknown library loading error'));
      }
    }, timeout);

    check();
  });
}
