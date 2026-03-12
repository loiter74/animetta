const { ipcMain } = require('electron');

/**
 * Register Live2D IPC handlers
 * @param {IpcBridge} ipcBridge - IPC bridge instance
 */
function registerLive2dHandlers(ipcBridge) {
  /**
   * Load Live2D model
   */
  ipcMain.handle('live2d:loadModel', async (event, modelPath) => {
    try {
      const live2dWindow = ipcBridge.getWindow('live2d');
      if (!live2dWindow || live2dWindow.isDestroyed()) {
        return { ok: false, error: 'Live2D window not available' };
      }

      await live2dWindow.webContents.executeJavaScript(`
        if (window.live2dRenderer) {
          window.live2dRenderer.loadModel('${modelPath}');
        }
      `);

      console.log('[Live2DHandler] Model loaded:', modelPath);
      return { ok: true };
    } catch (error) {
      console.error('[Live2DHandler] Failed to load model:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Set Live2D expression
   */
  ipcMain.handle('live2d:setExpression', async (event, expressionName) => {
    try {
      const live2dWindow = ipcBridge.getWindow('live2d');
      if (!live2dWindow || live2dWindow.isDestroyed()) {
        return { ok: false, error: 'Live2D window not available' };
      }

      await live2dWindow.webContents.executeJavaScript(`
        if (window.live2dRenderer) {
          window.live2dRenderer.setExpression('${expressionName}');
        }
      `);

      console.log('[Live2DHandler] Expression set:', expressionName);
      return { ok: true };
    } catch (error) {
      console.error('[Live2DHandler] Failed to set expression:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Play Live2D motion
   */
  ipcMain.handle('live2d:playMotion', async (event, group, index) => {
    try {
      const live2dWindow = ipcBridge.getWindow('live2d');
      if (!live2dWindow || live2dWindow.isDestroyed()) {
        return { ok: false, error: 'Live2D window not available' };
      }

      await live2dWindow.webContents.executeJavaScript(`
        if (window.live2dRenderer) {
          window.live2dRenderer.playMotion('${group}', ${index});
        }
      `);

      console.log('[Live2DHandler] Motion played:', group, index);
      return { ok: true };
    } catch (error) {
      console.error('[Live2DHandler] Failed to play motion:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Set Live2D parameter directly
   */
  ipcMain.handle('live2d:setParam', async (event, paramName, value) => {
    try {
      const live2dWindow = ipcBridge.getWindow('live2d');
      if (!live2dWindow || live2dWindow.isDestroyed()) {
        return { ok: false, error: 'Live2D window not available' };
      }

      await live2dWindow.webContents.executeJavaScript(`
        if (window.live2dRenderer) {
          window.live2dRenderer.setParam('${paramName}', ${value});
        }
      `);

      return { ok: true };
    } catch (error) {
      console.error('[Live2DHandler] Failed to set param:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Set mouth openness for lip sync
   */
  ipcMain.handle('live2d:setMouthOpen', async (event, value) => {
    try {
      const live2dWindow = ipcBridge.getWindow('live2d');
      if (!live2dWindow || live2dWindow.isDestroyed()) {
        return { ok: false, error: 'Live2D window not available' };
      }

      await live2dWindow.webContents.executeJavaScript(`
        if (window.live2dRenderer) {
          window.live2dRenderer.setMouthOpen(${value});
        }
      `);

      return { ok: true };
    } catch (error) {
      console.error('[Live2DHandler] Failed to set mouth open:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Execute Live2D action (from preset)
   */
  ipcMain.handle('live2d:executeAction', async (event, action) => {
    try {
      const live2dWindow = ipcBridge.getWindow('live2d');
      if (!live2dWindow || live2dWindow.isDestroyed()) {
        return { ok: false, error: 'Live2D window not available' };
      }

      // Forward to renderer
      live2dWindow.webContents.send('live2d:action', action);

      console.log('[Live2DHandler] Action executed:', action.type);
      return { ok: true };
    } catch (error) {
      console.error('[Live2DHandler] Failed to execute action:', error);
      return { ok: false, error: error.message };
    }
  });

  /**
   * Get Live2D model info
   */
  ipcMain.handle('live2d:getModelInfo', async (event) => {
    try {
      const live2dWindow = ipcBridge.getWindow('live2d');
      if (!live2dWindow || live2dWindow.isDestroyed()) {
        return { ok: false, error: 'Live2D window not available' };
      }

      const info = await live2dWindow.webContents.executeJavaScript(`
        if (window.live2dRenderer && window.live2dRenderer.model) {
          return {
            loaded: true,
            modelPath: window.live2dRenderer.modelPath,
            bounds: window.live2dRenderer.getBounds()
          };
        }
        return { loaded: false };
      `);

      return { ok: true, data: info };
    } catch (error) {
      console.error('[Live2DHandler] Failed to get model info:', error);
      return { ok: false, error: error.message };
    }
  });

  console.log('[Live2DHandler] Handlers registered');
}

module.exports = { registerLive2dHandlers };
