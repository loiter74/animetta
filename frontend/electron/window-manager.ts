import { BrowserWindow, shell } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'

export function createMainWindow(): BrowserWindow {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    show: false,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#1a1028',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  return mainWindow
}

export function createPopoutWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 600,
    height: 700,
    show: false,
    frame: false,
    backgroundColor: '#1a1028',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  // Load a special route for the popout Live2D view
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'] + '#/live2d-popout')
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'), {
      hash: '/live2d-popout'
    })
  }

  win.on('ready-to-show', () => {
    win.show()
  })

  return win
}
