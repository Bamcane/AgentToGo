class Tasks {
    constructor() {
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('generate-task-btn').addEventListener('click', () => this.showGenerateModal());
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
                    暂无循环任务，点击"AI生成任务"创建一个
                </div>
            `;
            return;
        }

        container.innerHTML = tasks.map(task => `
            <div class="task-card ${!task.enabled ? 'disabled' : ''}" data-id="${task.id}">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="font-bold text-lg">${app.escapeHtml(task.name)}</h3>
                        <p class="text-gray-400 text-sm mt-1">${app.escapeHtml(task.description || '')}</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs px-2 py-1 rounded ${task.enabled ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'}">
                            ${task.enabled ? '运行中' : '已停止'}
                        </span>
                    </div>
                </div>
                
                <div class="flex items-center gap-4 text-sm text-gray-400 mb-3">
                    <span>间隔: ${this.formatInterval(task.interval_seconds)}</span>
                    <span>超时: ${task.timeout_seconds}秒</span>
                    <span>上次运行: ${task.last_run ? new Date(task.last_run).toLocaleString() : '从未'}</span>
                </div>
                
                ${task.last_result ? `
                    <div class="bg-gray-900 rounded-lg p-3 mb-3 text-sm">
                        <div class="text-gray-500 mb-1">上次结果:</div>
                        <div class="text-gray-300">${app.escapeHtml(task.last_result).substring(0, 200)}${task.last_result.length > 200 ? '...' : ''}</div>
                    </div>
                ` : ''}
                
                <div class="flex gap-2">
                    <button onclick="tasks.toggleTask('${task.id}', ${!task.enabled})" 
                            class="${task.enabled ? 'btn-secondary' : 'bg-green-600 hover:bg-green-700'} text-white px-3 py-1 rounded text-sm">
                        ${task.enabled ? '停止' : '启动'}
                    </button>
                    <button onclick="tasks.editTask('${task.id}')" 
                            class="btn-secondary text-white px-3 py-1 rounded text-sm">编辑</button>
                    <button onclick="tasks.deleteTask('${task.id}')" 
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

    showGenerateModal() {
        app.showModal(`
            <div class="p-6">
                <h3 class="text-xl font-bold mb-4">AI生成循环任务</h3>
                <textarea id="task-description" class="w-full bg-gray-700 rounded-lg px-4 py-3 mb-4 h-32 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500" 
                          placeholder="描述你想让AI监测的任务，例如：&#10;- 每5分钟检查NAS存储空间，低于20%时通知我&#10;- 监控某个API的响应时间，超过3秒时告警"></textarea>
                <div class="flex justify-end gap-2">
                    <button onclick="app.hideModal()" class="btn-secondary text-white px-4 py-2 rounded">取消</button>
                    <button onclick="tasks.generateTask()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">生成</button>
                </div>
            </div>
        `);
    }

    async generateTask() {
        const description = document.getElementById('task-description').value.trim();
        if (!description) return;

        try {
            const response = await fetch(`${API_BASE}/api/tasks/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description })
            });
            const taskData = await response.json();
            this.showEditModal(null, taskData);
        } catch (error) {
            console.error('生成任务失败:', error);
            alert('生成任务失败，请重试');
        }
    }

    async editTask(taskId) {
        try {
            const response = await fetch(`${API_BASE}/api/tasks/`);
            const tasks = await response.json();
            const task = tasks.find(t => t.id === taskId);
            if (task) {
                this.showEditModal(taskId, task);
            }
        } catch (error) {
            console.error('获取任务详情失败:', error);
        }
    }

    showEditModal(taskId, taskData) {
        const isEdit = !!taskId;
        app.showModal(`
            <div class="p-6">
                <h3 class="text-xl font-bold mb-4">${isEdit ? '编辑任务' : '创建新任务'}</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">任务名称</label>
                        <input id="task-name" type="text" class="w-full bg-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                               value="${app.escapeHtml(taskData.name || '')}">
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">任务说明</label>
                        <input id="task-desc" type="text" class="w-full bg-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                               value="${app.escapeHtml(taskData.description || '')}">
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">执行间隔（秒）</label>
                            <input id="task-interval" type="number" class="w-full bg-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                                   value="${taskData.interval_seconds || 60}">
                        </div>
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">超时时间（秒）</label>
                            <input id="task-timeout" type="number" class="w-full bg-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                                   value="${taskData.timeout_seconds || 30}">
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">Python脚本</label>
                        <pre class="bg-gray-900 rounded-lg p-3 mb-2 text-xs text-gray-500">脚本必须包含 async def check(context: dict) -> dict 函数</pre>
                        <textarea id="task-script" class="w-full bg-gray-900 rounded-lg px-4 py-3 font-mono text-sm h-64 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500">${app.escapeHtml(taskData.script || '')}</textarea>
                    </div>
                </div>
                <div class="flex justify-end gap-2 mt-6">
                    <button onclick="app.hideModal()" class="btn-secondary text-white px-4 py-2 rounded">取消</button>
                    <button onclick="tasks.saveTask('${taskId || ''}')" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">保存</button>
                </div>
            </div>
        `);
    }

    async saveTask(taskId) {
        const data = {
            name: document.getElementById('task-name').value.trim(),
            description: document.getElementById('task-desc').value.trim(),
            script: document.getElementById('task-script').value,
            interval_seconds: parseInt(document.getElementById('task-interval').value) || 60,
            timeout_seconds: parseInt(document.getElementById('task-timeout').value) || 30
        };

        if (!data.name || !data.script) {
            alert('请填写任务名称和脚本');
            return;
        }

        try {
            const url = taskId ? `${API_BASE}/api/tasks/${taskId}` : `${API_BASE}/api/tasks/`;
            const method = taskId ? 'PUT' : 'POST';
            
            await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            app.hideModal();
            this.loadTasks();
        } catch (error) {
            console.error('保存任务失败:', error);
            alert('保存任务失败');
        }
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

const tasks = new Tasks();
