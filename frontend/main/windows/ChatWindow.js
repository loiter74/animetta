const { BrowserWindow, screen } = require('electron');
const path = require('path');

/**
 * Chat Window - Main chat interface
 */
class ChatWindow {
  constructor(config = {}) {
    this.defaultConfig = {
      width: 380,
      height: 500,
      resizable: true,
      title: 'Anima Chat',
      minWidth: 300,
      minHeight: 400
    };
    this.config = { ...this.defaultConfig, ...config };
  }

  /**
   * Create the chat browser window
   * @returns {BrowserWindow} The created window
   */
  createWindow() {
    // Get screen dimensions for positioning
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    const window = new BrowserWindow({
      width: this.config.width,
      height: this.config.height,
      x: 50, // Position on left side
      y: (height - this.config.height) / 2, // Center vertically
      resizable: this.config.resizable,
      minWidth: this.config.minWidth,
      minHeight: this.config.minHeight,
      title: this.config.title,
      titleBarStyle: 'hiddenInset', // Custom title bar style
      webPreferences: {
        preload: path.join(__dirname, '../../preload/index.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false,
        webSecurity: true
      }
    });

    // Handle window movement
    window.on('move', () => {
      const [x, y] = window.getPosition();
      console.log(`[ChatWindow] Moved to ${x}, ${y}`);
    });

    return window;
  }
}

module.exports = ChatWindow;
