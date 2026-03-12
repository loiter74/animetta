/**
 * Anima 配置面板
 * 与后端 Socket.IO 服务通信
 */

// Socket.IO 客户端
let socket = null;

// 当前状态
const state = {
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

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    initNavigation();
    initForms();
    initButtons();
    loadSettings();
    startUptimeCounter();
});

// Socket.IO 连接
function initSocket() {
    const backendUrl = localStorage.getItem('backendUrl') || 'http://localhost:12394';

    // 动态加载 Socket.IO
    loadScript('https://cdn.socket.io/4.5.4/socket.io.min.js', () => {
        socket = io(backendUrl);

        socket.on('connect', () => {
            console.log('[Config] 已连接到后端');
            state.connected = true;
            updateConnectionStatus(true);
            requestStats();
        });

        socket.on('disconnect', () => {
            console.log('[Config] 与后端断开连接');
            state.connected = false;
            updateConnectionStatus(false);
        });

        socket.on('connection-established', (data) => {
            console.log('[Config] 连接确认:', data);
        });

        socket.on('history-list', (data) => {
            renderHistoryList(data.histories);
        });

        socket.on('history-cleared', () => {
            showNotification('历史已清空', 'success');
            requestHistory();
        });

        socket.on('log_level_changed', (data) => {
            showNotification(data.message, data.success ? 'success' : 'error');
        });

        socket.on('control', (data) => {
            if (data.text === 'start-mic') {
                console.log('[Config] 后端准备就绪');
            }
        });
    });
}

// 导入脚本
function loadScript(src, callback) {
    const script = document.createElement('script');
    script.src = src;
    script.onload = callback;
    document.head.appendChild(script);
}

// 导航
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const pages = document.querySelectorAll('.page');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const pageName = item.dataset.page;

            // 更新导航状态
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // 更新页面显示
            pages.forEach(page => page.classList.remove('active'));
            document.getElementById(`page-${pageName}`).classList.add('active');

            state.currentPage = pageName;

            // 加载页面数据
            loadPageData(pageName);
        });
    });
}

// 表单初始化
function initForms() {
    // Live2D 缩放滑块
    const scaleSlider = document.getElementById('live2dScale');
    const scaleValue = scaleSlider?.nextElementSibling;
    scaleSlider?.addEventListener('input', (e) => {
        if (scaleValue) scaleValue.textContent = parseFloat(e.target.value).toFixed(1);
    });

    // 口型同步灵敏度
    const sensitivitySlider = document.getElementById('lipSyncSensitivity');
    const sensitivityValue = sensitivitySlider?.nextElementSibling;
    sensitivitySlider?.addEventListener('input', (e) => {
        if (sensitivityValue) sensitivityValue.textContent = parseFloat(e.target.value).toFixed(1);
    });

    // 预设项选择
    document.querySelectorAll('.preset-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.preset-item').forEach(p => p.classList.remove('selected'));
            item.classList.add('selected');
            state.selectedPreset = item.dataset.preset;
        });
    });
}

// 按钮初始化
function initButtons() {
    // 保存 Live2D 配置
    document.getElementById('btnSaveLive2D')?.addEventListener('click', () => {
        const config = {
            model: document.getElementById('live2dModelSelect').value,
            scale: parseFloat(document.getElementById('live2dScale').value),
            transparent: document.getElementById('live2dTransparent').checked,
            alwaysOnTop: document.getElementById('live2dAlwaysOnTop').checked,
            lipSync: {
                enabled: document.getElementById('lipSyncEnabled').checked,
                mode: document.getElementById('lipSyncMode').value,
                sensitivity: parseFloat(document.getElementById('lipSyncSensitivity').value)
            }
        };
        saveLive2DConfig(config);
    });

    // 测试预设
    document.getElementById('btnTestPreset')?.addEventListener('click', () => {
        if (state.selectedPreset) {
            testPreset(state.selectedPreset);
        } else {
            showNotification('请先选择一个预设', 'warning');
        }
    });

    // 刷新历史
    document.getElementById('btnRefreshHistory')?.addEventListener('click', requestHistory);

    // 导出历史
    document.getElementById('btnExportHistory')?.addEventListener('click', exportHistory);

    // 清空历史
    document.getElementById('btnClearHistory')?.addEventListener('click', () => {
        if (confirm('确定要清空对话历史吗？')) {
            socket?.emit('clear_history', {});
        }
    });

    // 清空日志
    document.getElementById('btnClearLogs')?.addEventListener('click', () => {
        state.logs = [];
        renderLogs();
    });

    // 刷新日志
    document.getElementById('btnRefreshLogs')?.addEventListener('click', () => {
        showNotification('日志刷新功能待实现', 'info');
    });

    // 保存设置
    document.getElementById('btnSaveSettings')?.addEventListener('click', saveSettings);

    // 启动后端
    document.getElementById('btnStartBackend')?.addEventListener('click', () => {
        showNotification('请使用命令行启动后端: python -m anima.socketio_server', 'info');
    });

    // 启动桌面应用
    document.getElementById('btnStartDesktop')?.addEventListener('click', () => {
        showNotification('请使用命令行启动: cd frontend && npm run dev', 'info');
    });
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    if (connected) {
        statusEl.classList.add('connected');
        statusEl.querySelector('.text').textContent = '已连接';
    } else {
        statusEl.classList.remove('connected');
        statusEl.querySelector('.text').textContent = '未连接';
    }
}

// 加载页面数据
function loadPageData(pageName) {
    switch (pageName) {
        case 'presets':
            loadPresets();
            break;
        case 'history':
            requestHistory();
            break;
        case 'logs':
            renderLogs();
            break;
    }
}

// 加载预设
function loadPresets() {
    const presets = {
        emotes: [
            { name: 'happy', desc: '开心' },
            { name: 'sad', desc: '伤心' },
            { name: 'shy', desc: '害羞' },
            { name: 'cry', desc: '哭泣' }
        ],
        gestures: [
            { name: 'greet', desc: '问候' },
            { name: 'think', desc: '思考' },
            { name: 'apologize', desc: '道歉' }
        ],
        reacts: [
            { name: 'success', desc: '成功' },
            { name: 'error', desc: '错误' },
            { name: 'waiting', desc: '等待' }
        ]
    };

    renderPresetList('emotePresets', presets.emotes);
    renderPresetList('gesturePresets', presets.gestures);
    renderPresetList('reactPresets', presets.reacts);
}

// 渲染预设列表
function renderPresetList(containerId, presets) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = presets.map(preset => `
        <div class="preset-item" data-preset="${preset.name}">
            <div class="preset-name">${preset.name}</div>
            <div class="preset-desc">${preset.desc}</div>
        </div>
    `).join('');

    // 添加点击事件
    container.querySelectorAll('.preset-item').forEach(item => {
        item.addEventListener('click', () => {
            container.querySelectorAll('.preset-item').forEach(p => p.classList.remove('selected'));
            item.classList.add('selected');
            state.selectedPreset = item.dataset.preset;
        });
    });
}

// 测试预设
function testPreset(presetName) {
    if (!state.connected) {
        showNotification('未连接到后端', 'error');
        return;
    }

    socket?.emit('live2d.action', {
        action: {
            type: 'emote',
            name: presetName
        }
    });

    showNotification(`执行预设: ${presetName}`, 'info');
}

// 请求历史
function requestHistory() {
    if (!state.connected) {
        renderHistoryList([]);
        return;
    }
    socket?.emit('fetch_history_list', {});
}

// 渲染历史列表
function renderHistoryList(histories) {
    const container = document.getElementById('historyList');
    if (!container) return;

    if (!histories || histories.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无对话历史</div>';
        return;
    }

    container.innerHTML = histories.map(h => `
        <div class="history-item">
            <div class="history-preview">${h.preview || '空对话'}</div>
            <div class="history-meta">${h.uid}</div>
        </div>
    `).join('');
}

// 导出历史
function exportHistory() {
    showNotification('导出功能待实现', 'info');
}

// 渲染日志
function renderLogs() {
    const container = document.getElementById('logContainer');
    if (!container) return;

    if (state.logs.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无日志</div>';
        return;
    }

    const levelFilter = document.getElementById('logLevelFilter')?.value || 'all';

    container.innerHTML = state.logs
        .filter(log => levelFilter === 'all' || log.level === levelFilter)
        .map(log => `
            <div class="log-entry">
                <span class="log-time">${log.time}</span>
                <span class="log-level ${log.level}">${log.level}</span>
                <span class="log-message">${log.message}</span>
            </div>
        `).join('');
}

// 添加日志
function addLog(level, message) {
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    state.logs.push({ level, message, time });

    // 限制日志数量
    if (state.logs.length > 1000) {
        state.logs.shift();
    }

    if (state.currentPage === 'logs') {
        renderLogs();
    }
}

// 请求统计数据
function requestStats() {
    // 模拟数据
    state.stats.sessions = 1;
    state.stats.messages = Math.floor(Math.random() * 100);
    updateStats();
}

// 更新统计显示
function updateStats() {
    document.getElementById('stat-sessions').textContent = state.stats.sessions;
    document.getElementById('stat-messages').textContent = state.stats.messages;
    document.getElementById('stat-live2d').textContent = state.connected ? '运行中' : '-';
}

// 运行时间计数器
function startUptimeCounter() {
    let seconds = 0;
    setInterval(() => {
        seconds++;
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        let text;
        if (hours > 0) {
            text = `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            text = `${minutes}m`;
        } else {
            text = `${seconds}s`;
        }

        document.getElementById('stat-uptime').textContent = text;
    }, 1000);
}

// 保存 Live2D 配置
function saveLive2DConfig(config) {
    localStorage.setItem('live2dConfig', JSON.stringify(config));
    showNotification('Live2D 配置已保存', 'success');
}

// 保存设置
function saveSettings() {
    const settings = {
        backendUrl: document.getElementById('backendUrl').value,
        logLevel: document.getElementById('logLevel').value
    };

    localStorage.setItem('backendUrl', settings.backendUrl);

    if (state.connected) {
        socket?.emit('set_log_level', { level: settings.logLevel });
    }

    showNotification('设置已保存', 'success');
}

// 加载设置
function loadSettings() {
    const savedBackendUrl = localStorage.getItem('backendUrl');
    if (savedBackendUrl) {
        document.getElementById('backendUrl').value = savedBackendUrl;
    }

    const savedLive2DConfig = localStorage.getItem('live2dConfig');
    if (savedLive2DConfig) {
        const config = JSON.parse(savedLive2DConfig);
        document.getElementById('live2dModelSelect').value = config.model || '';
        document.getElementById('live2dScale').value = config.scale || 1;
        document.getElementById('live2dTransparent').checked = config.transparent !== false;
        document.getElementById('live2dAlwaysOnTop').checked = config.alwaysOnTop !== false;
        if (config.lipSync) {
            document.getElementById('lipSyncEnabled').checked = config.lipSync.enabled !== false;
            document.getElementById('lipSyncMode').value = config.lipSync.mode || 'viseme';
            document.getElementById('lipSyncSensitivity').value = config.lipSync.sensitivity || 2.5;
        }
    }
}

// 通知
function showNotification(message, type = 'info') {
    const colors = {
        info: '#3b82f6',
        success: '#22c55e',
        warning: '#f59e0b',
        error: '#ef4444'
    };

    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${colors[type]};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
