class MemoryApp {
    constructor() {
        this.bindEvents();
        this.loadMemories();
    }

    formatTime(dateStr) {
        const date = new Date(dateStr + 'Z');
        return date.toLocaleString('zh-CN');
    }

    bindEvents() {
        document.getElementById('add-memory-btn').addEventListener('click', () => this.showAddModal());
    }

    async loadMemories() {
        try {
            const response = await fetch(`${API_BASE}/api/memory/`);
            const memories = await response.json();
            this.renderMemories(memories);
        } catch (error) {
            console.error('加载记忆失败:', error);
        }
    }

    renderMemories(memories) {
        const container = document.getElementById('memory-list');
        
        if (memories.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-12">
                    暂无记忆，点击"添加记忆"创建一个
                </div>
            `;
            return;
        }

        const grouped = {};
        memories.forEach(m => {
            if (!grouped[m.category]) grouped[m.category] = [];
            grouped[m.category].push(m);
        });

        container.innerHTML = Object.entries(grouped).map(([category, items]) => `
            <div class="mb-6">
                <h3 class="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wider">${escapeHtml(category)}</h3>
                <div class="space-y-2">
                    ${items.map(m => `
                        <div class="memory-item" data-id="${m.id}">
                            <div class="flex justify-between items-start">
                                <div class="flex-1">
                                    <div class="font-medium text-blue-400">${escapeHtml(m.key)}</div>
                                    <div class="text-gray-300 mt-1 text-sm">${escapeHtml(m.value)}</div>
                                    <div class="text-gray-500 text-xs mt-2">更新于 ${this.formatTime(m.updated_at)}</div>
                                </div>
                                <div class="flex gap-1 ml-4">
                                    <button onclick="memoryApp.editMemory(${m.id})" 
                                            class="text-gray-400 hover:text-blue-400 p-1">编辑</button>
                                    <button onclick="memoryApp.deleteMemory(${m.id})" 
                                            class="text-gray-400 hover:text-red-400 p-1">删除</button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    showAddModal() {
        showModal(`
            <div class="p-6">
                <h3 class="text-xl font-bold mb-4">添加记忆</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">键名</label>
                        <input id="memory-key" type="text" class="w-full bg-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                               placeholder="例如: user_name, home_ip, nas_path">
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">值</label>
                        <textarea id="memory-value" class="w-full bg-gray-200 rounded-lg px-4 py-2 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500" 
                                  placeholder="记忆的内容"></textarea>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400 mb-1">分类</label>
                        <input id="memory-category" type="text" class="w-full bg-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                               placeholder="例如: personal, network, hardware" value="general">
                    </div>
                </div>
                <div class="flex justify-end gap-2 mt-6">
                    <button onclick="hideModal()" class="btn-secondary text-white px-4 py-2 rounded">取消</button>
                    <button onclick="memoryApp.saveMemory()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">保存</button>
                </div>
            </div>
        `);
    }

    async editMemory(memoryId) {
        try {
            const response = await fetch(`${API_BASE}/api/memory/`);
            const memories = await response.json();
            const mem = memories.find(m => m.id === memoryId);
            if (!mem) return;

            showModal(`
                <div class="p-6">
                    <h3 class="text-xl font-bold mb-4">编辑记忆</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">键名</label>
                            <div class="text-gray-300">${escapeHtml(mem.key)}</div>
                        </div>
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">值</label>
                            <textarea id="memory-value" class="w-full bg-gray-200 rounded-lg px-4 py-2 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500">${escapeHtml(mem.value)}</textarea>
                        </div>
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">分类</label>
                            <input id="memory-category" type="text" class="w-full bg-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" 
                                   value="${escapeHtml(mem.category)}">
                        </div>
                    </div>
                    <div class="flex justify-end gap-2 mt-6">
                        <button onclick="hideModal()" class="btn-secondary text-white px-4 py-2 rounded">取消</button>
                        <button onclick="memoryApp.updateMemory(${memoryId})" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">更新</button>
                    </div>
                </div>
            `);
        } catch (error) {
            console.error('获取记忆详情失败:', error);
        }
    }

    async saveMemory() {
        const data = {
            key: document.getElementById('memory-key').value.trim(),
            value: document.getElementById('memory-value').value.trim(),
            category: document.getElementById('memory-category').value.trim() || 'general'
        };

        if (!data.key || !data.value) {
            alert('请填写键名和值');
            return;
        }

        try {
            await fetch(`${API_BASE}/api/memory/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            hideModal();
            this.loadMemories();
        } catch (error) {
            console.error('保存记忆失败:', error);
            alert('保存失败，可能键名已存在');
        }
    }

    async updateMemory(memoryId) {
        const data = {
            value: document.getElementById('memory-value').value.trim(),
            category: document.getElementById('memory-category').value.trim()
        };

        if (!data.value) {
            alert('请填写值');
            return;
        }

        try {
            await fetch(`${API_BASE}/api/memory/${memoryId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            hideModal();
            this.loadMemories();
        } catch (error) {
            console.error('更新记忆失败:', error);
        }
    }

    async deleteMemory(memoryId) {
        if (!confirm('确定删除这条记忆吗？')) return;
        
        try {
            await fetch(`${API_BASE}/api/memory/${memoryId}`, {
                method: 'DELETE'
            });
            this.loadMemories();
        } catch (error) {
            console.error('删除记忆失败:', error);
        }
    }
}

const memoryApp = new MemoryApp();
