const { app, BrowserWindow, screen } = require('electron')
const path = require('path')

// Disable GPU acceleration for compatibility
app.disableHardwareAcceleration()

let mainWindow = null

function createWindow() {
  const { width } = screen.getPrimaryDisplay().workAreaSize

  // Default window size (9:16 aspect ratio, half size for screen fit)
  const windowWidth = 540
  const windowHeight = 960

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: width - windowWidth - 50,
    y: 50,
    transparent: false,
    frame: true,
    alwaysOnTop: false,
    resizable: true,
    minimizable: true,
    maximizable: true,
    backgroundColor: '#0a0a0f',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    title: 'Animetta Live Stream',
    icon: path.join(__dirname, '../public/favicon.svg'),
  })

  // Always load from Vite dev server in development
  // The concurrent script ensures Vite is running first
  mainWindow.loadURL('http://localhost:3000/live.html')

  // Open DevTools for debugging
  mainWindow.webContents.openDevTools({ mode: 'detach' })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // Log when page loads
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('[Electron] Page loaded successfully')
  })

  // Log errors
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('[Electron] Failed to load:', errorCode, errorDescription)
  })
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
