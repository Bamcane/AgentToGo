const API_BASE = '';

class App {
    constructor() {
        this.currentConversationId = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadConversations();
        notifications.loadUnreadCount();
    }

    bindEvents() {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        document.getElementById('notification-btn').addEventListener('click', () => {
            notifications.togglePanel();
        });
    }

    switchTab(tabName) {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');

        if (tabName === 'tasks') tasks.loadTasks();
        if (tabName === 'memory') memory.loadMemories();
    }

    async loadConversations() {
        try {
            const response = await fetch(`${API_BASE}/api/chat/conversations`);
            const conversations = await response.json();
            this.renderConversations(conversations);
        } catch (error) {
            console.error('加载会话失败:', error);
        }
    }

    renderConversations(conversations) {
        const list = document.getElementById('conversation-list');
        list.innerHTML = conversations.map(conv => `
            <div class="conversation-item ${conv.id === this.currentConversationId ? 'active' : ''}" 
                 data-id="${conv.id}">
                <span class="truncate text-sm">${this.escapeHtml(conv.title)}</span>
                <button class="delete-conv-btn opacity-0 hover:opacity-100 text-gray-400 hover:text-red-400 p-1" 
                        data-id="${conv.id}">×</button>
            </div>
        `).join('');

        list.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('delete-conv-btn')) {
                    this.selectConversation(item.dataset.id);
                }
            });
        });

        list.querySelectorAll('.delete-conv-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteConversation(btn.dataset.id);
            });
        });
    }

    async selectConversation(conversationId) {
        this.currentConversationId = conversationId;
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', item.dataset.id === conversationId);
        });
        await chat.loadMessages(conversationId);
    }

    async createConversation() {
        try {
            const response = await fetch(`${API_BASE}/api/chat/conversations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: '新会话' })
            });
            const conversation = await response.json();
            await this.loadConversations();
            this.selectConversation(conversation.id);
        } catch (error) {
            console.error('创建会话失败:', error);
        }
    }

    async deleteConversation(conversationId) {
        if (!confirm('确定删除这个会话吗？')) return;
        
        try {
            await fetch(`${API_BASE}/api/chat/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            if (this.currentConversationId === conversationId) {
                this.currentConversationId = null;
                document.getElementById('chat-messages').innerHTML = `
                    <div class="text-center text-gray-500 mt-20">选择或创建一个会话开始聊天</div>
                `;
            }
            await this.loadConversations();
        } catch (error) {
            console.error('删除会话失败:', error);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showModal(content) {
        const overlay = document.getElementById('modal-overlay');
        const modalContent = document.getElementById('modal-content');
        modalContent.innerHTML = content;
        overlay.classList.remove('hidden');
        
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) this.hideModal();
        });
    }

    hideModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }
}

const app = new App();

document.getElementById('new-chat-btn').addEventListener('click', () => app.createConversation());
