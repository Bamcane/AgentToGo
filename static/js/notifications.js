class NotificationsApp {
    constructor() {
        this.panelOpen = false;
        this.bindEvents();
        this.loadUnreadCount();
    }

    bindEvents() {
        const markAllBtn = document.getElementById('mark-all-read');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => this.markAllAsRead());
        }
        
        const notificationBtn = document.getElementById('notification-btn');
        if (notificationBtn) {
            notificationBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.togglePanel();
            });
        }
        
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('notification-panel');
            const btn = document.getElementById('notification-btn');
            if (this.panelOpen && panel && !panel.contains(e.target) && btn && !btn.contains(e.target)) {
                this.closePanel();
            }
        });
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
        if (!badge) return;
        
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    togglePanel() {
        if (this.panelOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    }

    openPanel() {
        this.panelOpen = true;
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.remove('hidden');
            this.loadNotifications();
        }
    }

    closePanel() {
        this.panelOpen = false;
        const panel = document.getElementById('notification-panel');
        if (panel) {
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
        if (!container) return;
        
        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-8">暂无通知</div>
            `;
            return;
        }

        container.innerHTML = notifications.map(n => `
            <div class="notification-item ${!n.read ? 'unread' : ''}" data-id="${n.id}">
                <div class="flex justify-between items-start mb-2">
                    <span class="font-medium text-sm">${escapeHtml(n.task_name || '系统通知')}</span>
                    <span class="text-xs text-gray-500">${this.formatTime(n.created_at)}</span>
                </div>
                <div class="text-sm text-gray-300 mb-2">${escapeHtml(n.message)}</div>
                <div class="flex justify-between items-center">
                    <span class="text-xs px-2 py-1 rounded bg-gray-300 text-gray-400">${this.getActionLabel(n.action)}</span>
                    ${!n.read ? `<button onclick="notificationsApp.markAsRead(${n.id})" class="text-xs text-blue-400 hover:text-blue-300">标为已读</button>` : ''}
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
        // 数据库存的是UTC时间，需要转换为本地时间
        const date = new Date(dateStr + 'Z');  // 添加Z表示UTC时间
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
        return date.toLocaleString('zh-CN');
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

const notificationsApp = new NotificationsApp();
