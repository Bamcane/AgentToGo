class TasksApp {
    constructor() {
        this.loadTasks();
    }

    async loadTasks() {
        try {
            const response = await fetch(`${API_BASE}/api/tasks/`);
            const tasks = await response.json();
            this.renderTasks(tasks);
        } catch (error) {
            console.error('加载任务失败:', error);
        }
    }

    renderTasks(tasks) {
        const container = document.getElementById('task-list');
        
        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-12">
                    暂无循环任务<br>
                    <span class="text-sm">在聊天中告诉AI："每5分钟检查...提醒我"</span>
                </div>
            `;
            return;
        }

        container.innerHTML = tasks.map(task => `
            <div class="task-card ${!task.enabled ? 'disabled' : ''}" data-id="${task.id}">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="font-bold text-lg">${escapeHtml(task.name)}</h3>
                        ${task.user_requirement ? `<p class="text-blue-400 text-sm mt-1">要求: ${escapeHtml(task.user_requirement)}</p>` : ''}
                        ${task.description ? `<p class="text-gray-400 text-sm mt-1">${escapeHtml(task.description)}</p>` : ''}
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs px-2 py-1 rounded ${task.enabled ? 'bg-green-900 text-green-300' : 'bg-gray-300 text-gray-400'}">
                            ${task.enabled ? '运行中' : '已停止'}
                        </span>
                    </div>
                </div>
                
                <div class="flex items-center gap-4 text-sm text-gray-400 mb-3">
                    <span>间隔: ${this.formatInterval(task.interval_seconds)}</span>
                    <span>超时: ${task.timeout_seconds}秒</span>
                    <span>上次运行: ${task.last_run ? this.formatTime(task.last_run) : '从未'}</span>
                </div>
                
                ${task.last_result ? `
                    <div class="bg-gray-900 rounded-lg p-3 mb-3 text-sm">
                        <div class="text-gray-500 mb-1">上次结果:</div>
                        <div class="text-gray-300">${escapeHtml(task.last_result).substring(0, 200)}${task.last_result.length > 200 ? '...' : ''}</div>
                    </div>
                ` : ''}
                
                <div class="flex gap-2">
                    <button onclick="tasksApp.toggleTask('${task.id}', ${!task.enabled})" 
                            class="${task.enabled ? 'btn-secondary' : 'bg-green-600 hover:bg-green-700'} text-white px-3 py-1 rounded text-sm">
                        ${task.enabled ? '停止' : '启动'}
                    </button>
                    <button onclick="tasksApp.deleteTask('${task.id}')" 
                            class="btn-danger text-white px-3 py-1 rounded text-sm">删除</button>
                </div>
            </div>
        `).join('');
    }

    formatInterval(seconds) {
        if (seconds < 60) return `${seconds}秒`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
        return `${Math.floor(seconds / 3600)}小时`;
    }

    formatTime(dateStr) {
        const date = new Date(dateStr + 'Z');
        return date.toLocaleString('zh-CN');
    }

    async toggleTask(taskId, enabled) {
        try {
            await fetch(`${API_BASE}/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            this.loadTasks();
        } catch (error) {
            console.error('更新任务失败:', error);
        }
    }

    async deleteTask(taskId) {
        if (!confirm('确定删除这个任务吗？')) return;
        
        try {
            await fetch(`${API_BASE}/api/tasks/${taskId}`, {
                method: 'DELETE'
            });
            this.loadTasks();
        } catch (error) {
            console.error('删除任务失败:', error);
        }
    }
}

const tasksApp = new TasksApp();
