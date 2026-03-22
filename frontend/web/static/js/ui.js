/**
 * UI 渲染模块
 */

import { state, addLog } from './state.js';

export function renderLogs() {
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

export function renderHistoryList(histories) {
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

export function renderPresetList(containerId, presets) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = presets.map(preset => `
        <div class="preset-item" data-preset="${preset.name}">
            <div class="preset-name">${preset.name}</div>
            <div class="preset-desc">${preset.desc}</div>
        </div>
    `).join('');

    container.querySelectorAll('.preset-item').forEach(item => {
        item.addEventListener('click', () => {
            container.querySelectorAll('.preset-item').forEach(p => p.classList.remove('selected'));
            item.classList.add('selected');
            state.selectedPreset = item.dataset.preset;
        });
    });
}

export function showNotification(message, type = 'info') {
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
