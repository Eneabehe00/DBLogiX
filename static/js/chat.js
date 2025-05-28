class ChatWidget {
    constructor() {
        this.isOpen = false;
        this.lastMessageTimestamp = null;
        this.pollInterval = null;
        this.currentUser = null;
        this.unreadCount = 0;
        
        this.init();
    }
    
    init() {
        this.createChatWidget();
        this.bindEvents();
        this.startPolling();
        this.loadInitialMessages();
        this.updateUnreadCount();
    }
    
    createChatWidget() {
        // Create chat toggle button
        const toggleButton = document.createElement('button');
        toggleButton.className = 'chat-toggle';
        toggleButton.innerHTML = '<i class="fas fa-comments"></i>';
        toggleButton.id = 'chatToggle';
        
        // Create unread badge
        const unreadBadge = document.createElement('span');
        unreadBadge.className = 'unread-badge';
        unreadBadge.id = 'chatUnreadBadge';
        unreadBadge.style.display = 'none';
        toggleButton.appendChild(unreadBadge);
        
        // Create chat widget
        const chatWidget = document.createElement('div');
        chatWidget.className = 'chat-widget';
        chatWidget.id = 'chatWidget';
        chatWidget.innerHTML = `
            <div class="chat-header">
                <div>
                    <h5>Chat Globale</h5>
                    <div class="online-users">
                        <span class="online-dot"></span>
                        <span class="online-count" id="onlineCount">Caricamento...</span>
                    </div>
                </div>
                <button class="chat-close" id="chatClose">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="chat-loading">
                    <div class="spinner"></div>
                </div>
            </div>
            <div class="typing-indicator" id="typingIndicator">
                Qualcuno sta scrivendo...
            </div>
            <div class="chat-input">
                <textarea 
                    class="chat-input-field" 
                    id="chatInputField" 
                    placeholder="Scrivi un messaggio..."
                    rows="1"
                ></textarea>
                <button class="chat-send" id="chatSend">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(toggleButton);
        document.body.appendChild(chatWidget);
    }
    
    bindEvents() {
        const toggleButton = document.getElementById('chatToggle');
        const closeButton = document.getElementById('chatClose');
        const sendButton = document.getElementById('chatSend');
        const inputField = document.getElementById('chatInputField');
        
        toggleButton.addEventListener('click', () => this.toggleChat());
        closeButton.addEventListener('click', () => this.closeChat());
        sendButton.addEventListener('click', () => this.sendMessage());
        
        // Handle Enter key in input field
        inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        inputField.addEventListener('input', () => {
            inputField.style.height = 'auto';
            inputField.style.height = Math.min(inputField.scrollHeight, 80) + 'px';
        });
        
        // Mark messages as read when chat is opened
        document.getElementById('chatWidget').addEventListener('transitionend', () => {
            if (this.isOpen) {
                this.markMessagesAsRead();
            }
        });
    }
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }
    
    openChat() {
        const widget = document.getElementById('chatWidget');
        const toggle = document.getElementById('chatToggle');
        
        widget.classList.add('open');
        toggle.classList.add('hidden');
        this.isOpen = true;
        
        // Focus input field
        setTimeout(() => {
            document.getElementById('chatInputField').focus();
        }, 300);
        
        // Mark messages as read
        this.markMessagesAsRead();
        this.updateUnreadCount();
    }
    
    closeChat() {
        const widget = document.getElementById('chatWidget');
        const toggle = document.getElementById('chatToggle');
        
        widget.classList.remove('open');
        toggle.classList.remove('hidden');
        this.isOpen = false;
    }
    
    async loadInitialMessages() {
        try {
            const response = await fetch('/chat/api/messages/latest');
            const data = await response.json();
            
            if (data.success) {
                this.displayMessages(data.messages, true);
                if (data.messages.length > 0) {
                    this.lastMessageTimestamp = data.messages[data.messages.length - 1].timestamp;
                }
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('Errore nel caricamento dei messaggi');
        }
    }
    
    async sendMessage() {
        const inputField = document.getElementById('chatInputField');
        const sendButton = document.getElementById('chatSend');
        const message = inputField.value.trim();
        
        if (!message) return;
        
        // Disable input while sending
        inputField.disabled = true;
        sendButton.disabled = true;
        
        try {
            const response = await fetch('/chat/api/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            if (data.success) {
                inputField.value = '';
                inputField.style.height = 'auto';
                this.displayMessages([data.message]);
                this.lastMessageTimestamp = data.message.timestamp;
                this.scrollToBottom();
            } else {
                this.showError(data.error || 'Errore nell\'invio del messaggio');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Errore nell\'invio del messaggio');
        } finally {
            inputField.disabled = false;
            sendButton.disabled = false;
            inputField.focus();
        }
    }
    
    async pollForNewMessages() {
        if (!this.lastMessageTimestamp) return;
        
        try {
            const response = await fetch(`/chat/api/messages/latest?since=${this.lastMessageTimestamp}`);
            const data = await response.json();
            
            if (data.success && data.messages.length > 0) {
                this.displayMessages(data.messages);
                this.lastMessageTimestamp = data.messages[data.messages.length - 1].timestamp;
                
                // Update unread count if chat is closed
                if (!this.isOpen) {
                    this.updateUnreadCount();
                }
                
                // Auto-scroll if user is at bottom
                if (this.isOpen && this.isScrolledToBottom()) {
                    this.scrollToBottom();
                }
            }
        } catch (error) {
            console.error('Error polling for messages:', error);
        }
    }
    
    displayMessages(messages, replace = false) {
        const messagesContainer = document.getElementById('chatMessages');
        
        if (replace) {
            messagesContainer.innerHTML = '';
        }
        
        messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            messagesContainer.appendChild(messageElement);
        });
        
        if (replace || this.isScrolledToBottom()) {
            this.scrollToBottom();
        }
    }
    
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        const isOwn = message.user_id === this.getCurrentUserId();
        
        messageDiv.className = `message ${isOwn ? 'own' : 'other'} new`;
        
        messageDiv.innerHTML = `
            <div class="message-bubble">
                ${!isOwn ? `<div class="message-header">${this.escapeHtml(message.username)}</div>` : ''}
                <div class="message-text">${this.escapeHtml(message.message)}</div>
                <div class="message-time">${message.formatted_time}</div>
            </div>
        `;
        
        // Remove animation class after animation completes
        setTimeout(() => {
            messageDiv.classList.remove('new');
        }, 300);
        
        return messageDiv;
    }
    
    async updateUnreadCount() {
        try {
            const response = await fetch('/chat/api/unread-count');
            const data = await response.json();
            
            if (data.success) {
                this.unreadCount = data.unread_count;
                this.updateUnreadBadge();
            }
        } catch (error) {
            console.error('Error updating unread count:', error);
        }
    }
    
    updateUnreadBadge() {
        const badge = document.getElementById('chatUnreadBadge');
        
        if (this.unreadCount > 0 && !this.isOpen) {
            badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
    
    async markMessagesAsRead() {
        // For simplicity, we'll just reset the unread count
        // In a real implementation, you'd mark specific messages as read
        this.unreadCount = 0;
        this.updateUnreadBadge();
    }
    
    startPolling() {
        // Poll for new messages every 3 seconds
        this.pollInterval = setInterval(() => {
            this.pollForNewMessages();
        }, 3000);
        
        // Update unread count every 10 seconds
        setInterval(() => {
            if (!this.isOpen) {
                this.updateUnreadCount();
            }
        }, 10000);
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    isScrolledToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        const threshold = 50; // pixels from bottom
        return messagesContainer.scrollHeight - messagesContainer.clientHeight <= messagesContainer.scrollTop + threshold;
    }
    
    getCurrentUserId() {
        // Get current user ID from a meta tag or global variable
        const metaTag = document.querySelector('meta[name="current-user-id"]');
        return metaTag ? parseInt(metaTag.content) : null;
    }
    
    getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.content : '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showError(message) {
        // Create a temporary error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.style.position = 'fixed';
        errorDiv.style.top = '20px';
        errorDiv.style.right = '20px';
        errorDiv.style.zIndex = '9999';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
    
    destroy() {
        this.stopPolling();
        
        // Remove elements
        const toggle = document.getElementById('chatToggle');
        const widget = document.getElementById('chatWidget');
        
        if (toggle) toggle.remove();
        if (widget) widget.remove();
    }
}

// Initialize chat widget when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if user is authenticated
    const userMeta = document.querySelector('meta[name="current-user-id"]');
    if (userMeta) {
        window.chatWidget = new ChatWidget();
    }
});

// Clean up when page is unloaded
window.addEventListener('beforeunload', function() {
    if (window.chatWidget) {
        window.chatWidget.destroy();
    }
}); 