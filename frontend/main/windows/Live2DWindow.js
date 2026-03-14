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
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  const window = new BrowserWindow({
    width: this.config.width,
    height: this.config.height,
    x: width - this.config.width - 50,
    y: (height - this.config.height) / 2,
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
      webSecurity: true,
      devTools: true,          // 明确开启
      autoplayPolicy: 'no-user-gesture-required', 
    }
  });

  // 加载页面
  const filePath = path.join(__dirname, '../../renderer/live2d/live2d.html');
  console.log('[Live2DWindow] 加载路径:', filePath);
  console.log('[Live2DWindow] 文件存在:', require('fs').existsSync(filePath));
  window.loadFile(filePath);

  // 等页面加载完再开 DevTools，调试期间先不穿透
  if (process.env.NODE_ENV === 'development' || process.argv.includes('--dev')) {
    window.webContents.on('did-finish-load', () => {
      console.log('[Live2DWindow] 页面加载完成，开启 DevTools');
      window.webContents.openDevTools({ mode: 'detach' });
      // 调试期间暂时关掉穿透，能正常点击 DevTools
      // window.setIgnoreMouseEvents(true, { forward: true });
    });
  } else {
    // 生产环境才开穿透
    window.setIgnoreMouseEvents(true, { forward: true });
  }

  window.on('move', () => {
    const [x, y] = window.getPosition();
    console.log(`[Live2DWindow] Moved to ${x}, ${y}`);
  });

  return window;
}
}

module.exports = Live2DWindow;
