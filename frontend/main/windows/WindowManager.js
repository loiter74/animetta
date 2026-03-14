const { app, BrowserWindow, globalShortcut } = require('electron');
const path = require('path');
const Live2DWindow = require('./Live2DWindow');
const ChatWindow = require('./ChatWindow');

/**
 * Window Manager - Manages all application windows
 */
class WindowManager {
  constructor() {
    this.windows = {
      live2d: null,
      chat: null
    };
  }

  /**
   * Create Live2D window
   * @returns {BrowserWindow} The Live2D window instance
   */
  createLive2DWindow() {
    if (this.windows.live2d && !this.windows.live2d.isDestroyed()) {
      this.windows.live2d.focus();
      return this.windows.live2d;
    }

    const live2dWindow = new Live2DWindow();
    this.windows.live2d = live2dWindow.createWindow();

    // Load Live2D page
    const htmlPath = path.join(__dirname, '../../renderer/live2d/live2d.html');
    this.windows.live2d.loadFile(htmlPath);

    // Window cleanup
    this.windows.live2d.on('closed', () => {
      this.windows.live2d = null;
      console.log('[WindowManager] Live2D window closed');
    });

    // DevTools - use detach mode for transparent window
    // 开发模式默认开启，生产模式需要 --dev 参数
    const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev') || !app.isPackaged;
    console.log('[WindowManager] isDev:', isDev, 'argv:', process.argv);
    if (isDev) {
      this.windows.live2d.webContents.on('did-finish-load', () => {
        this.windows.live2d.webContents.openDevTools({ mode: 'detach' });
        console.log('[WindowManager] Live2D DevTools opened');
      });
    }

    // Add keyboard shortcut to toggle DevTools (F12)
    this.windows.live2d.webContents.on('before-input-event', (event, input) => {
      if (input.key === 'F12') {
        if (this.windows.live2d.webContents.isDevToolsOpened()) {
          this.windows.live2d.webContents.closeDevTools();
        } else {
          this.windows.live2d.webContents.openDevTools({ mode: 'detach' });
        }
      }
    });

    console.log('[WindowManager] Live2D window created');
    return this.windows.live2d;
  }

  /**
   * Create Chat window
   * @returns {BrowserWindow} The chat window instance
   */
  createChatWindow() {
    if (this.windows.chat && !this.windows.chat.isDestroyed()) {
      this.windows.chat.focus();
      return this.windows.chat;
    }

    const chatWindow = new ChatWindow();
    this.windows.chat = chatWindow.createWindow();

    // Load chat page
    const htmlPath = path.join(__dirname, '../../renderer/chat/chat.html');
    this.windows.chat.loadFile(htmlPath);

    // Window cleanup
    this.windows.chat.on('closed', () => {
      this.windows.chat = null;
      console.log('[WindowManager] Chat window closed');
    });

    // DevTools - 开发模式默认开启
    const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev') || !app.isPackaged;
    console.log('[WindowManager] Chat isDev:', isDev);
    if (isDev) {
      this.windows.chat.webContents.on('did-finish-load', () => {
        this.windows.chat.webContents.openDevTools({ mode: 'detach' });
        console.log('[WindowManager] Chat DevTools opened');
      });
    }

    // Add keyboard shortcut to toggle DevTools (F12)
    this.windows.chat.webContents.on('before-input-event', (event, input) => {
      if (input.key === 'F12') {
        if (this.windows.chat.webContents.isDevToolsOpened()) {
          this.windows.chat.webContents.closeDevTools();
        } else {
          this.windows.chat.webContents.openDevTools({ mode: 'detach' });
        }
      }
    });

    console.log('[WindowManager] Chat window created');
    return this.windows.chat;
  }

  /**
   * Get window by type
   * @param {string} type - Window type ('live2d' or 'chat')
   * @returns {BrowserWindow|null} The window instance
   */
  getWindow(type) {
    return this.windows[type] || null;
  }

  /**
   * Close all windows
   */
  closeAllWindows() {
    Object.keys(this.windows).forEach(key => {
      if (this.windows[key] && !this.windows[key].isDestroyed()) {
        this.windows[key].close();
      }
    });
  }

  /**
   * Broadcast message to all windows
   * @param {string} channel - IPC channel
   * @param {*} data - Data to send
   */
  broadcastToAll(channel, data) {
    Object.keys(this.windows).forEach(key => {
      if (this.windows[key] && !this.windows[key].isDestroyed()) {
        this.windows[key].webContents.send(channel, data);
      }
    });
  }
}

module.exports = WindowManager;
