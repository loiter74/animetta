import { app, BrowserWindow, shell } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { createMainWindow, createPopoutWindow } from './window-manager'
import { IpcBridge } from './ipc-bridge'

let mainWindow: BrowserWindow | null = null
let popoutWindow: BrowserWindow | null = null
let ipcBridge: IpcBridge | null = null

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.anima.desktop')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  mainWindow = createMainWindow()
  ipcBridge = new IpcBridge(mainWindow)

  // Open links in system browser
  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // HMR for dev
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow()
      ipcBridge = new IpcBridge(mainWindow)
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  if (ipcBridge) {
    ipcBridge.disconnect()
  }
})

// Export for IPC handlers to access windows
export function getMainWindow(): BrowserWindow | null {
  return mainWindow
}

export function getPopoutWindow(): BrowserWindow | null {
  return popoutWindow
}

export function setPopoutWindow(win: BrowserWindow | null): void {
  popoutWindow = win
}
