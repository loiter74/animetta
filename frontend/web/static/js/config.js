/**
 * Anima 配置面板
 * 主入口文件 - 模块化重构
 */

import { initSocket, emit } from './socket.js';
import { state, updateConnectionStatus, addLog, updateStats } from './state.js';
import { renderLogs, renderHistoryList, renderPresetList, showNotification } from './ui.js';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initSocket({
        onConnect: () => {
            updateConnectionStatus(true);
            requestStats();
        },
        onDisconnect: () => updateConnectionStatus(false),
        onHistoryList: (histories) => renderHistoryList(histories),
        onHistoryCleared: () => {
            showNotification('历史已清空', 'success');
            requestHistory();
        },
        onLogLevelChanged: (data) => {
            showNotification(data.message, data.success ? 'success' : 'error');
        },
        onControl: (data) => {
            if (data.text === 'start-mic') {
                console.log('[Config] 后端准备就绪');
            }
        }
    });

    initNavigation();
    initForms();
    initButtons();
    loadSettings();
    startUptimeCounter();
});

// 导航
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const pages = document.querySelectorAll('.page');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const pageName = item.dataset.page;

            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            pages.forEach(page => page.classList.remove('active'));
            document.getElementById(`page-${pageName}`).classList.add('active');

            state.currentPage = pageName;
            loadPageData(pageName);
        });
    });
}

// 表单初始化
function initForms() {
    const scaleSlider = document.getElementById('live2dScale');
    const scaleValue = scaleSlider?.nextElementSibling;
    scaleSlider?.addEventListener('input', (e) => {
        if (scaleValue) scaleValue.textContent = parseFloat(e.target.value).toFixed(1);
    });

    const sensitivitySlider = document.getElementById('lipSyncSensitivity');
    const sensitivityValue = sensitivitySlider?.nextElementSibling;
    sensitivitySlider?.addEventListener('input', (e) => {
        if (sensitivityValue) sensitivityValue.textContent = parseFloat(e.target.value).toFixed(1);
    });

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

    document.getElementById('btnTestPreset')?.addEventListener('click', () => {
        if (state.selectedPreset) {
            testPreset(state.selectedPreset);
        } else {
            showNotification('请先选择一个预设', 'warning');
        }
    });

    document.getElementById('btnRefreshHistory')?.addEventListener('click', requestHistory);
    document.getElementById('btnExportHistory')?.addEventListener('click', () => showNotification('导出功能待实现', 'info'));
    document.getElementById('btnClearHistory')?.addEventListener('click', () => {
        if (confirm('确定要清空对话历史吗？')) {
            emit('clear_history', {});
        }
    });
    document.getElementById('btnClearLogs')?.addEventListener('click', () => {
        state.logs = [];
        renderLogs();
    });
    document.getElementById('btnRefreshLogs')?.addEventListener('click', () => showNotification('日志刷新功能待实现', 'info'));
    document.getElementById('btnSaveSettings')?.addEventListener('click', saveSettings);
    document.getElementById('btnStartBackend')?.addEventListener('click', () => {
        showNotification('请使用命令行启动后端: python -m anima.socketio_server', 'info');
    });
    document.getElementById('btnStartDesktop')?.addEventListener('click', () => {
        showNotification('请使用命令行启动: cd frontend && npm run dev', 'info');
    });
}

// 页面数据加载
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

// 测试预设
function testPreset(presetName) {
    if (!state.connected) {
        showNotification('未连接到后端', 'error');
        return;
    }

    emit('live2d.action', {
        action: { type: 'emote', name: presetName }
    });

    showNotification(`执行预设: ${presetName}`, 'info');
}

// 请求历史
function requestHistory() {
    if (!state.connected) {
        renderHistoryList([]);
        return;
    }
    emit('fetch_history_list', {});
}

// 请求统计数据
function requestStats() {
    state.stats.sessions = 1;
    state.stats.messages = Math.floor(Math.random() * 100);
    updateStats({});
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
        emit('set_log_level', { level: settings.logLevel });
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
