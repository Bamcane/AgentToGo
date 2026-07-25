class Notifications {
    constructor() {
        this.panelOpen = false;
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('mark-all-read').addEventListener('click', () => this.markAllAsRead());
    }

    async loadUnreadCount() {
        try {
            const response = await fetch(`${API_BASE}/api/notifications/unread-count`);
            const data = await response.json();
            this.updateBadge(data.count);
        } catch (error) {
            console.error('加载未读数量失败:', error);
        }
    }

    updateBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    togglePanel() {
        this.panelOpen = !this.panelOpen;
        const panel = document.getElementById('notification-panel');
        
        if (this.panelOpen) {
            panel.classList.remove('hidden');
            this.loadNotifications();
        } else {
            panel.classList.add('hidden');
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch(`${API_BASE}/api/notifications/`);
            const notifications = await response.json();
            this.renderNotifications(notifications);
        } catch (error) {
            console.error('加载通知失败:', error);
        }
    }

    renderNotifications(notifications) {
        const container = document.getElementById('notification-list');
        
        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-8">暂无通知</div>
            `;
            return;
        }

        container.innerHTML = notifications.map(n => `
            <div class="notification-item ${!n.read ? 'unread' : ''}" data-id="${n.id}">
                <div class="flex justify-between items-start mb-2">
                    <span class="font-medium text-sm">${app.escapeHtml(n.task_name || '系统通知')}</span>
                    <span class="text-xs text-gray-500">${this.formatTime(n.created_at)}</span>
                </div>
                <div class="text-sm text-gray-300 mb-2">${app.escapeHtml(n.message)}</div>
                <div class="flex justify-between items-center">
                    <span class="text-xs px-2 py-1 rounded bg-gray-700 text-gray-400">${this.getActionLabel(n.action)}</span>
                    ${!n.read ? `<button onclick="notifications.markAsRead(${n.id})" class="text-xs text-blue-400 hover:text-blue-300">标为已读</button>` : ''}
                </div>
            </div>
        `).join('');
    }

    getActionLabel(action) {
        const labels = {
            'notify_continue': '通知并继续',
            'notify_stop': '通知并停止',
            'llm_analysis': 'AI分析',
            'ignore': '忽略'
        };
        return labels[action] || action;
    }

    formatTime(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
        return date.toLocaleDateString();
    }

    async markAsRead(notificationId) {
        try {
            await fetch(`${API_BASE}/api/notifications/${notificationId}/read`, {
                method: 'PUT'
            });
            this.loadNotifications();
            this.loadUnreadCount();
        } catch (error) {
            console.error('标记已读失败:', error);
        }
    }

    async markAllAsRead() {
        try {
            await fetch(`${API_BASE}/api/notifications/read-all`, {
                method: 'PUT'
            });
            this.loadNotifications();
            this.updateBadge(0);
        } catch (error) {
            console.error('全部标记已读失败:', error);
        }
    }
}

const notifications = new Notifications();
