# Anima Desktop - Electron Live2D + Chat Application

Desktop application for Anima with decoupled Live2D display and chat interface.

## Project Structure

```
apps/electron-live2d/
├── main/                      # Electron main process
│   ├── index.js              # Application entry point
│   ├── windows/              # Window management
│   │   ├── Live2DWindow.js   # Live2D window class
│   │   ├── ChatWindow.js     # Chat window class
│   │   └── WindowManager.js  # Window manager
│   ├── ipc/                  # Inter-process communication
│   │   ├── IpcBridge.js      # IPC bridge
│   │   └── handlers/         # IPC handlers
│   │       ├── live2d.js     # Live2D handlers
│   │       └── chat.js       # Chat handlers
│   └── config/
│       └── appConfig.js      # Application configuration
│
├── renderer/                 # Renderer processes
│   ├── live2d/              # Live2D window
│   │   ├── live2d.html
│   │   ├── live2d.css
│   │   └── live2d.js
│   ├── chat/                # Chat window
│   │   ├── chat.html
│   │   ├── chat.css
│   │   └── chat.js
│   └── shared/              # Shared utilities
│       └── constants.js
│
├── preload/
│   └── index.js             # Preload script (context bridge)
│
├── package.json
├── tsconfig.json
└── README.md
```

## Features

### Live2D Window
- Transparent, always-on-top display
- PIXI.js + pixi-live2d-display rendering
- Model loading and management
- Expression and motion control
- Lip sync support
- Draggable positioning

### Chat Window
- Message history display
- Streaming response rendering
- Voice input support
- Modern dark theme UI
- Custom title bar

### IPC Bridge
- Secure context isolation
- Window-to-window communication
- Backend WebSocket relay
- Live2D action queue integration

## Installation

```bash
cd apps/electron-live2d
npm install
```

## Development

```bash
# Start with dev tools
npm run dev

# Start normally
npm start
```

## Building

```bash
# Build for current platform
npm run build

# Build for specific platforms
npm run build:win
npm run build:mac
npm run build:linux
```

## Configuration

Configuration is loaded from `config/desktop.yaml` in the project root:

```yaml
application:
  name: "Anima Desktop"
  version: "1.0.0"

windows:
  live2d:
    width: 400
    height: 600
    transparent: true
    frame: false
    alwaysOnTop: true

  chat:
    width: 380
    height: 500

backend:
  wsUrl: "ws://localhost:12394"
```

## Backend Integration

The Electron app connects to the Anima backend via WebSocket:

- **Chat messages**: Forwarded to LLM service
- **Live2D actions**: Sent through action queue
- **Audio streams**: Processed for lip sync
- **State sync**: Speaking, typing indicators

## TODO (Phase 2+)

- [ ] Implement Viseme-based lip sync
- [ ] Integrate action queue from backend
- [ ] Add YAML preset configuration
- [ ] Implement voice input recording
- [ ] Add model selection UI
- [ ] Add settings/configuration UI
- [ ] Implement crash reporting
- [ ] Add auto-update mechanism

## License

MIT
