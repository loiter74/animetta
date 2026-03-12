const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const WindowManager = require('./windows/WindowManager');
const IpcBridge = require('./ipc/IpcBridge');
const appConfig = require('./config/appConfig');

// Global references
let windowManager = null;
let ipcBridge = null;

/**
 * Application entry point
 */
app.whenReady().then(() => {
  console.log('[Anima Desktop] Initializing...');

  // Initialize window manager
  windowManager = new WindowManager();

  // Initialize IPC bridge
  ipcBridge = new IpcBridge(windowManager);

  // Create windows
  windowManager.createLive2DWindow();
  windowManager.createChatWindow();

  console.log('[Anima Desktop] Ready');

  // macOS: Recreate windows when dock icon is clicked
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      windowManager.createLive2DWindow();
      windowManager.createChatWindow();
    }
  });
});

/**
 * Quit when all windows are closed (except on macOS)
 */
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

/**
 * Before quit: cleanup resources
 */
app.on('before-quit', () => {
  console.log('[Anima Desktop] Shutting down...');
  if (ipcBridge) {
    ipcBridge.disconnect();
  }
});

/**
 * Handle uncaught exceptions
 */
process.on('uncaughtException', (error) => {
  console.error('[Anima Desktop] Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('[Anima Desktop] Unhandled rejection at:', promise, 'reason:', reason);
});
