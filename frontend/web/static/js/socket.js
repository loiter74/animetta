/**
 * Socket.IO 通信模块
 */

let socket = null;
let reconnectTimer = null;

export function initSocket(callbacks) {
    const backendUrl = localStorage.getItem('backendUrl') || 'http://localhost:12394';

    loadScript('https://cdn.socket.io/4.5.4/socket.io.min.js', () => {
        socket = io(backendUrl);

        socket.on('connect', () => {
            console.log('[SocketIO] 已连接到后端');
            callbacks.onConnect?.();
        });

        socket.on('disconnect', () => {
            console.log('[SocketIO] 与后端断开连接');
            callbacks.onDisconnect?.();
        });

        socket.on('connection-established', (data) => {
            console.log('[SocketIO] 连接确认:', data);
        });

        socket.on('history-list', (data) => callbacks.onHistoryList?.(data.histories));
        socket.on('history-cleared', () => callbacks.onHistoryCleared?.());
        socket.on('log_level_changed', (data) => callbacks.onLogLevelChanged?.(data));
        socket.on('control', (data) => callbacks.onControl?.(data));
    });
}

export function emit(event, data) {
    if (socket?.connected) {
        socket.emit(event, data);
    }
}

export function isConnected() {
    return socket?.connected || false;
}

function loadScript(src, callback) {
    const script = document.createElement('script');
    script.src = src;
    script.onload = callback;
    document.head.appendChild(script);
}
