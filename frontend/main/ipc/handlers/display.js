/**
 * Display IPC Handlers - 显示相关IPC处理
 *
 * 处理来自渲染进程的显示控制请求
 */

const { ipcMain, BrowserWindow } = require('electron');
const { getWindowStateStore } = require('../../config/WindowStateStore');

/**
 * 注册显示相关的IPC处理器
 * @param {BrowserWindow} mainWindow - 主窗口引用 (可选)
 */
function registerDisplayHandlers(mainWindow = null) {
  // 获取状态存储
  const stateStore = getWindowStateStore();

  // 获取当前活动窗口
  const getTargetWindow = (event) => {
    // 优先使用传入的窗口
    if (mainWindow && !mainWindow.isDestroyed()) {
      return mainWindow;
    }
    // 从事件中获取
    return BrowserWindow.fromWebContents(event.sender);
  };

  // ==================== 缩放控制 ====================

  /**
   * 设置缩放策略
   */
  ipcMain.handle('display:setScaleStrategy', async (event, strategy) => {
    const window = getTargetWindow(event);
    if (window) {
      // 发送到渲染进程执行
      window.webContents.send('display:setScaleStrategy', strategy);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 获取当前缩放策略
   */
  ipcMain.handle('display:getScaleStrategy', async (event) => {
    // 这个需要从渲染进程获取，返回一个默认值
    return 'contain';
  });

  /**
   * 获取可用缩放策略
   */
  ipcMain.handle('display:getAvailableStrategies', async () => {
    return [
      { value: 'fit', label: '适应', description: '完整显示模型，保持比例' },
      { value: 'contain', label: '包含', description: '填满高度，底部对齐，适合全身模型' },
      { value: 'cover', label: '覆盖', description: '填满容器，可能裁切' },
    ];
  });

  /**
   * 缩放 (增量)
   */
  ipcMain.handle('display:zoom', async (event, delta) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:zoom', delta);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 设置用户缩放
   */
  ipcMain.handle('display:setUserScale', async (event, scale) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:setUserScale', scale);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 重置缩放
   */
  ipcMain.handle('display:resetScale', async (event) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:resetScale');
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // ==================== 模型位置 ====================

  /**
   * 移动模型
   */
  ipcMain.handle('display:moveModel', async (event, dx, dy) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:moveModel', dx, dy);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 重置模型位置
   */
  ipcMain.handle('display:resetModelPosition', async (event) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:resetModelPosition');
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  // ==================== 背景控制 (Phase 2) ====================

  /**
   * 设置背景模式
   */
  ipcMain.handle('display:setBackgroundMode', async (event, mode, options = {}) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:setBackgroundMode', mode, options);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 获取当前背景模式
   */
  ipcMain.handle('display:getBackgroundMode', async () => {
    return 'transparent';
  });

  /**
   * 设置背景颜色
   */
  ipcMain.handle('display:setBackgroundColor', async (event, color) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:setBackgroundColor', color);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 设置背景透明度
   */
  ipcMain.handle('display:setBackgroundOpacity', async (event, opacity) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:setBackgroundOpacity', opacity);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 设置背景图片
   */
  ipcMain.handle('display:setBackgroundImage', async (event, path) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:setBackgroundImage', path);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 设置背景视频
   */
  ipcMain.handle('display:setBackgroundVideo', async (event, path) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:setBackgroundVideo', path);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 切换背景模式
   */
  ipcMain.handle('display:cycleBackgroundMode', async (event) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:cycleBackgroundMode');
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 获取可用背景模式
   */
  ipcMain.handle('display:getAvailableBackgroundModes', async () => {
    return [
      { value: 'transparent', label: '透明', description: '透明背景，适用于OBS捕获', icon: '🌀' },
      { value: 'color', label: '纯色', description: '纯色背景，可选绿幕色', icon: '🎨' },
      { value: 'image', label: '图片', description: '图片背景', icon: '🖼️' },
      { value: 'video', label: '视频', description: '视频背景（循环播放）', icon: '🎬' },
    ];
  });

  // ==================== 窗口控制 ====================

  /**
   * 设置窗口置顶
   */
  ipcMain.handle('display:setAlwaysOnTop', async (event, value) => {
    const window = getTargetWindow(event);
    if (window) {
      window.setAlwaysOnTop(value);
      // 保存状态
      stateStore.updateAlwaysOnTop(value);
      return { success: true, value };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 设置点击穿透
   */
  ipcMain.handle('display:setClickThrough', async (event, value) => {
    const window = getTargetWindow(event);
    if (window) {
      window.setIgnoreMouseEvents(value, { forward: true });
      // 保存状态
      stateStore.updateClickThrough(value);
      return { success: true, value };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 移动窗口
   */
  ipcMain.handle('display:moveWindow', async (event, x, y) => {
    const window = getTargetWindow(event);
    if (window) {
      window.setPosition(Math.round(x), Math.round(y));
      // 保存位置
      stateStore.updateWindowPosition(x, y);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 调整窗口大小
   */
  ipcMain.handle('display:resizeWindow', async (event, width, height) => {
    const window = getTargetWindow(event);
    if (window) {
      window.setSize(Math.round(width), Math.round(height));
      // 保存大小
      stateStore.updateWindowSize(width, height);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 获取窗口位置
   */
  ipcMain.handle('display:getWindowPosition', async (event) => {
    const window = getTargetWindow(event);
    if (window) {
      const [x, y] = window.getPosition();
      return { x, y };
    }
    return { x: 0, y: 0 };
  });

  /**
   * 保存窗口状态 (批量)
   */
  ipcMain.handle('display:saveWindowState', async (event, state) => {
    try {
      if (state.x !== undefined && state.y !== undefined) {
        stateStore.updateWindowPosition(state.x, state.y);
      }
      if (state.width !== undefined && state.height !== undefined) {
        stateStore.updateWindowSize(state.width, state.height);
      }
      if (state.alwaysOnTop !== undefined) {
        stateStore.updateAlwaysOnTop(state.alwaysOnTop);
      }
      if (state.clickThrough !== undefined) {
        stateStore.updateClickThrough(state.clickThrough);
      }
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // ==================== 配置持久化 ====================

  /**
   * 获取显示配置
   */
  ipcMain.handle('display:getConfig', async () => {
    try {
      const config = stateStore.getDisplayConfig();
      return config;
    } catch (error) {
      console.error('[DisplayHandlers] Failed to get config:', error);
      return null;
    }
  });

  /**
   * 保存显示配置
   */
  ipcMain.handle('display:saveConfig', async (event, config) => {
    try {
      stateStore.saveDisplayConfig(config);
      return { success: true };
    } catch (error) {
      console.error('[DisplayHandlers] Failed to save config:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * 获取 Live2D 窗口状态
   */
  ipcMain.handle('display:getWindowState', async () => {
    try {
      const state = stateStore.getLive2DWindowState();
      return state;
    } catch (error) {
      console.error('[DisplayHandlers] Failed to get window state:', error);
      return null;
    }
  });

  /**
   * 重置配置
   */
  ipcMain.handle('display:resetConfig', async () => {
    try {
      stateStore.reset();
      return { success: true };
    } catch (error) {
      console.error('[DisplayHandlers] Failed to reset config:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * 导出配置
   */
  ipcMain.handle('display:exportConfig', async () => {
    try {
      const json = stateStore.exportConfig();
      return { success: true, data: json };
    } catch (error) {
      console.error('[DisplayHandlers] Failed to export config:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * 导入配置
   */
  ipcMain.handle('display:importConfig', async (event, json) => {
    try {
      const result = stateStore.importConfig(json);
      return result;
    } catch (error) {
      console.error('[DisplayHandlers] Failed to import config:', error);
      return { success: false, error: error.message };
    }
  });

  // ==================== 状态查询 ====================

  /**
   * 获取显示状态
   */
  ipcMain.handle('display:getState', async () => {
    // 这个需要从渲染进程获取，返回默认值
    return null;
  });

  /**
   * 获取模型信息
   */
  ipcMain.handle('display:getModelInfo', async () => {
    // 这个需要从渲染进程获取，返回默认值
    return null;
  });

  // ==================== 快捷键管理 (Phase 3) ====================

  /**
   * 获取快捷键配置
   */
  ipcMain.handle('display:getHotkeys', async (event) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:getHotkeys');
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 重置快捷键为默认
   */
  ipcMain.handle('display:resetHotkeys', async (event) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:resetHotkeys');
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 设置快捷键启用状态
   */
  ipcMain.handle('display:setHotkeysEnabled', async (event, enabled) => {
    const window = getTargetWindow(event);
    if (window) {
      window.webContents.send('display:setHotkeysEnabled', enabled);
      return { success: true };
    }
    return { success: false, error: 'Window not found' };
  });

  /**
   * 获取快捷键列表
   */
  ipcMain.handle('display:getHotkeyList', async () => {
    // 返回默认快捷键列表
    return [
      { action: 'moveUp', key: 'ArrowUp', modifiers: [], description: '向上移动模型', display: '↑' },
      { action: 'moveDown', key: 'ArrowDown', modifiers: [], description: '向下移动模型', display: '↓' },
      { action: 'moveLeft', key: 'ArrowLeft', modifiers: [], description: '向左移动模型', display: '←' },
      { action: 'moveRight', key: 'ArrowRight', modifiers: [], description: '向右移动模型', display: '→' },
      { action: 'zoomIn', key: '=', modifiers: ['ctrl'], description: '放大模型', display: 'Ctrl + +' },
      { action: 'zoomOut', key: '-', modifiers: ['ctrl'], description: '缩小模型', display: 'Ctrl + -' },
      { action: 'reset', key: 'r', modifiers: ['ctrl'], description: '重置模型位置和缩放', display: 'Ctrl + R' },
      { action: 'nextBackground', key: 'b', modifiers: [], description: '切换背景模式', display: 'B' },
      { action: 'toggleAlwaysOnTop', key: 't', modifiers: ['ctrl'], description: '切换窗口置顶', display: 'Ctrl + T' },
      { action: 'toggleClickThrough', key: 'c', modifiers: ['ctrl', 'alt'], description: '切换点击穿透', display: 'Ctrl + Alt + C' },
    ];
  });

  console.log('[DisplayHandlers] Registered display IPC handlers');
}

module.exports = { registerDisplayHandlers };
