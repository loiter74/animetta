const { BrowserWindow, screen } = require('electron');
const path = require('path');

/**
 * Live2D Window - Transparent, always-on-top Live2D display
 */
class Live2DWindow {
  constructor(config = {}) {
    this.defaultConfig = {
      width: 400,
      height: 600,
      transparent: true,
      frame: false,
      alwaysOnTop: true,
      resizable: true,
      skipTaskbar: false,
      title: 'Anima Live2D',
      backgroundColor: '#00000000'
    };
    this.config = { ...this.defaultConfig, ...config };
  }

  /**
   * Create the Live2D browser window
   * @returns {BrowserWindow} The created window
   */
  createWindow() {
    // Get screen dimensions for positioning
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    const window = new BrowserWindow({
      width: this.config.width,
      height: this.config.height,
      x: width - this.config.width - 50, // Position on right side
      y: (height - this.config.height) / 2, // Center vertically
      transparent: this.config.transparent,
      frame: this.config.frame,
      alwaysOnTop: this.config.alwaysOnTop,
      resizable: this.config.resizable,
      skipTaskbar: this.config.skipTaskbar,
      title: this.config.title,
      backgroundColor: this.config.backgroundColor,
      webPreferences: {
        preload: path.join(__dirname, '../../preload/index.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false,
        webSecurity: true
      }
    });

    // Make window click-through when not clicking on the model
    window.setIgnoreMouseEvents(true, { forward: true });

    // Handle window movement
    window.on('move', () => {
      const [x, y] = window.getPosition();
      console.log(`[Live2DWindow] Moved to ${x}, ${y}`);
    });

    return window;
  }
}

module.exports = Live2DWindow;
