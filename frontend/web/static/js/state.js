/**
 * 状态管理模块
 */

export const state = {
    connected: false,
    currentPage: 'dashboard',
    selectedPreset: null,
    logs: [],
    stats: {
        sessions: 0,
        messages: 0,
        uptime: 0
    }
};

export function updateConnectionStatus(connected) {
    state.connected = connected;
    const statusEl = document.getElementById('connectionStatus');
    if (statusEl) {
        statusEl.classList.toggle('connected', connected);
        const textEl = statusEl.querySelector('.text');
        if (textEl) textEl.textContent = connected ? '已连接' : '未连接';
    }
}

export function addLog(level, message) {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    state.logs.push({ level, message, time });

    if (state.logs.length > 1000) {
        state.logs.shift();
    }
}

export function updateStats(newStats) {
    Object.assign(state.stats, newStats);

    document.getElementById('stat-sessions').textContent = state.stats.sessions;
    document.getElementById('stat-messages').textContent = state.stats.messages;
    document.getElementById('stat-live2d').textContent = state.connected ? '运行中' : '-';
}
