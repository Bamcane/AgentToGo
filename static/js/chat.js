class Chat {
    constructor() {
        this.ws = null;
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('send-btn').addEventListener('click', () => this.sendMessage());
        
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
        let html = app.escapeHtml(content);
        
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

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'chunk') {
                this.appendToLastMessage(data.content);
            } else if (data.type === 'done') {
                this.finishMessage();
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const content = input.value.trim();
        
        if (!content || !app.currentConversationId) return;

        input.value = '';
        input.style.height = 'auto';

        this.appendMessage('user', content);

        try {
            await fetch(`${API_BASE}/api/chat/conversations/${app.currentConversationId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            this.startStreamingMessage();

            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ content }));
            }
        } catch (error) {
            console.error('发送消息失败:', error);
        }
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
        app.loadConversations();
    }

    scrollToBottom() {
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    }
}

const chat = new Chat();
