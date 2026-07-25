class ChatApp {
    constructor() {
        this.ws = null;
        this.streamingContent = '';
        this.currentConversationId = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadConversations();
        
        if (initialConversationId) {
            this.selectConversation(initialConversationId);
        }
    }

    bindEvents() {
        document.getElementById('send-btn').addEventListener('click', () => this.sendMessage());
        
        document.getElementById('new-chat-btn').addEventListener('click', () => this.createConversation());
        
        const input = document.getElementById('chat-input');
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 200) + 'px';
        });
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
            <div class="conversation-item ${conv.id === this.currentConversationId ? 'active' : ''}" data-id="${conv.id}">
                <a href="/chat/${conv.id}" class="flex-1 truncate text-sm">${escapeHtml(conv.title)}</a>
                <div class="flex gap-1 opacity-0 hover:opacity-100">
                    <button class="rename-conv-btn text-gray-400 hover:text-blue-400 p-1" data-id="${conv.id}" data-title="${escapeHtml(conv.title)}">✎</button>
                    <button class="delete-conv-btn text-gray-400 hover:text-red-400 p-1" data-id="${conv.id}">×</button>
                </div>
            </div>
        `).join('');

        list.querySelectorAll('.conversation-item > a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const id = link.parentElement.dataset.id;
                window.location.href = `/chat/${id}`;
            });
        });

        list.querySelectorAll('.rename-conv-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.renameConversation(btn.dataset.id, btn.dataset.title);
            });
        });

        list.querySelectorAll('.delete-conv-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.deleteConversation(btn.dataset.id);
            });
        });
    }

    async renameConversation(conversationId, currentTitle) {
        const newTitle = prompt('请输入新的会话名称:', currentTitle);
        if (!newTitle || newTitle === currentTitle) return;
        
        try {
            await fetch(`${API_BASE}/api/chat/conversations/${conversationId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            this.loadConversations();
        } catch (error) {
            console.error('重命名失败:', error);
        }
    }

    selectConversation(conversationId) {
        this.currentConversationId = conversationId;
        
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', item.dataset.id === conversationId);
        });
        
        this.loadMessages(conversationId);
    }

    async createConversation() {
        try {
            const response = await fetch(`${API_BASE}/api/chat/conversations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: '新会话' })
            });
            const conversation = await response.json();
            
            window.location.href = `/chat/${conversation.id}`;
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
                window.location.href = '/chat';
            } else {
                this.loadConversations();
            }
        } catch (error) {
            console.error('删除会话失败:', error);
        }
    }

    async loadMessages(conversationId) {
        try {
            const response = await fetch(`${API_BASE}/api/chat/conversations/${conversationId}/messages`);
            const messages = await response.json();
            this.renderMessages(messages);
            this.connectWebSocket(conversationId);
        } catch (error) {
            console.error('加载消息失败:', error);
        }
    }

    renderMessages(messages) {
        const container = document.getElementById('chat-messages');
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 mt-20">开始新的对话</div>
            `;
            return;
        }

        container.innerHTML = messages.map(msg => `
            <div class="flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}">
                <div class="message-${msg.role} rounded-2xl px-4 py-3 max-w-[80%]">
                    <div class="message-content text-sm">${this.formatMessage(msg.content)}</div>
                </div>
            </div>
        `).join('');

        this.scrollToBottom();
    }

    formatMessage(content) {
        let html = escapeHtml(content);
        
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
        html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-600 px-1 rounded">$1</code>');
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }

    connectWebSocket(conversationId) {
        if (this.ws) {
            this.ws.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat/${conversationId}`);

        this.ws.onopen = () => {
            console.log('WebSocket连接已建立');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'chunk':
                    this.appendToLastMessage(data.content);
                    break;
                case 'done':
                    this.finishMessage();
                    break;
                case 'error':
                    this.showError(data.content);
                    break;
                case 'tool_call':
                    this.showToolCall(data.tool, data.arguments);
                    break;
                case 'tool_result':
                    this.showToolResult(data.tool, data.result);
                    break;
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket连接已关闭');
        };
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const content = input.value.trim();
        
        if (!content) return;

        if (!this.currentConversationId) {
            alert('请先创建或选择一个会话');
            return;
        }

        input.value = '';
        input.style.height = 'auto';

        this.appendMessage('user', content);
        this.startStreamingMessage();

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ content }));
        } else {
            console.log('WebSocket未连接');
            this.showError('连接已断开，请刷新页面重试');
        }
    }

    showToolCall(tool, args) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'flex justify-start';
        div.innerHTML = `
            <div class="message-assistant rounded-2xl px-4 py-3 max-w-[80%] bg-purple-900 bg-opacity-30 border border-purple-700">
                <div class="text-xs text-purple-400 mb-1">🔧 调用工具: ${tool}</div>
                <pre class="text-xs text-gray-400 overflow-x-auto">${escapeHtml(JSON.stringify(args, null, 2))}</pre>
            </div>
        `;
        container.appendChild(div);
        this.scrollToBottom();
    }

    showToolResult(tool, result) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'flex justify-start';
        div.innerHTML = `
            <div class="message-assistant rounded-2xl px-4 py-3 max-w-[80%] ${result.success ? 'bg-green-900 bg-opacity-30 border border-green-700' : 'bg-red-900 bg-opacity-30 border border-red-700'}">
                <div class="text-xs ${result.success ? 'text-green-400' : 'text-red-400'} mb-1">${result.success ? '✓' : '✗'} ${tool} 执行结果</div>
                <div class="text-sm text-gray-300">${escapeHtml(result.result?.message || result.error || '完成')}</div>
            </div>
        `;
        container.appendChild(div);
        this.scrollToBottom();
    }

    showError(message) {
        const streamingMsg = document.getElementById('streaming-message');
        if (streamingMsg) {
            streamingMsg.remove();
        }
        alert(message);
    }

    appendMessage(role, content) {
        const container = document.getElementById('chat-messages');
        
        const emptyMsg = container.querySelector('.text-center.text-gray-500');
        if (emptyMsg) emptyMsg.remove();

        const div = document.createElement('div');
        div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'}`;
        div.innerHTML = `
            <div class="message-${role} rounded-2xl px-4 py-3 max-w-[80%]">
                <div class="message-content text-sm">${this.formatMessage(content)}</div>
            </div>
        `;
        container.appendChild(div);
        this.scrollToBottom();
    }

    startStreamingMessage() {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'flex justify-start';
        div.id = 'streaming-message';
        div.innerHTML = `
            <div class="message-assistant rounded-2xl px-4 py-3 max-w-[80%]">
                <div class="message-content text-sm">
                    <span class="animate-pulse">思考中...</span>
                </div>
            </div>
        `;
        container.appendChild(div);
        this.streamingContent = '';
        this.scrollToBottom();
    }

    appendToLastMessage(chunk) {
        const streamingMsg = document.getElementById('streaming-message');
        if (!streamingMsg) return;

        this.streamingContent += chunk;
        const contentDiv = streamingMsg.querySelector('.message-content');
        contentDiv.innerHTML = this.formatMessage(this.streamingContent);
        this.scrollToBottom();
    }

    finishMessage() {
        const streamingMsg = document.getElementById('streaming-message');
        if (streamingMsg) {
            streamingMsg.removeAttribute('id');
        }
        this.streamingContent = '';
        this.loadConversations();
    }

    scrollToBottom() {
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    }
}

const chatApp = new ChatApp();
