class ChatWidget {
    constructor() {
        this.isOpen = false;
        this.lastMessageTimestamp = null;
        this.pollInterval = null;
        this.onlineUsersInterval = null;
        this.currentUser = null;
        this.unreadCount = 0;
        this.lastUnreadUpdate = null;
        this.isAndroid = /Android/i.test(navigator.userAgent);
        this.isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        this.isMobile = this.isAndroid || this.isIOS;
        this.keyboardVisible = false;
        this.originalViewportHeight = window.innerHeight;
        
        this.init();
    }
    
    init() {
        this.createChatWidget();
        this.bindEvents();
        this.startPolling();
        this.loadInitialMessages();
        this.updateOnlineUsers();
        this.updateUnreadCount();
        
        // Setup mobile keyboard detection for both Android and iOS
        if (this.isMobile) {
            this.setupMobileKeyboardDetection();
        }
    }
    
    setupMobileKeyboardDetection() {
        // Method 1: Visual Viewport API (modern browsers)
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', () => {
                this.handleViewportChange();
            });
        }
        
        // Method 2: Window resize fallback
        window.addEventListener('resize', () => {
            this.handleWindowResize();
        });
        
        // Method 3: Input focus/blur events for both Android and iOS
        document.addEventListener('focusin', (e) => {
            if (e.target.matches('.chat-input-field')) {
                setTimeout(() => this.handleKeyboardShow(), this.isIOS ? 600 : 300);
            }
        });
        
        document.addEventListener('focusout', (e) => {
            if (e.target.matches('.chat-input-field')) {
                setTimeout(() => this.handleKeyboardHide(), 300);
            }
        });
        
        // iOS-specific: orientation change handling
        if (this.isIOS) {
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    this.originalViewportHeight = window.innerHeight;
                    if (this.keyboardVisible) {
                        this.handleKeyboardShow();
                    }
                }, 500);
            });
        }
    }
    
    handleViewportChange() {
        if (!this.isOpen || !this.isMobile) return;
        
        const currentHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
        const heightDiff = this.originalViewportHeight - currentHeight;
        
        if (heightDiff > 150) { // Keyboard is likely open
            this.handleKeyboardShow();
        } else {
            this.handleKeyboardHide();
        }
    }
    
    handleWindowResize() {
        if (!this.isOpen || !this.isMobile) return;
        
        const currentHeight = window.innerHeight;
        const heightDiff = this.originalViewportHeight - currentHeight;
        
        if (heightDiff > 150) { // Keyboard is likely open
            this.handleKeyboardShow();
        } else {
            this.handleKeyboardHide();
        }
    }
    
    handleKeyboardShow() {
        if (!this.isOpen || !this.isMobile || this.keyboardVisible) return;
        
        this.keyboardVisible = true;
        const chatWidget = document.getElementById('chatWidget');
        const chatMessages = document.getElementById('chatMessages');
        const chatInput = document.querySelector('.chat-input');
        
        if (chatWidget && chatMessages && chatInput) {
            // Add mobile keyboard class for specific styling
            if (this.isAndroid) {
                chatWidget.classList.add('android-keyboard-open');
            } else if (this.isIOS) {
                chatWidget.classList.add('ios-keyboard-open');
            }
            
            // Scroll to bottom to ensure input is visible
            setTimeout(() => {
                this.scrollToBottom();
                const inputField = document.getElementById('chatInputField');
                if (inputField) {
                    if (this.isIOS) {
                        // iOS needs a different approach
                        inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                        // Double-ensure on iOS
                        setTimeout(() => {
                            inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                        }, 300);
                    } else {
                        inputField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }, this.isIOS ? 200 : 100);
        }
    }
    
    handleKeyboardHide() {
        if (!this.isMobile || !this.keyboardVisible) return;
        
        this.keyboardVisible = false;
        const chatWidget = document.getElementById('chatWidget');
        
        if (chatWidget) {
            chatWidget.classList.remove('android-keyboard-open', 'ios-keyboard-open');
        }
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
                        <div class="online-users-list" id="onlineUsersList">
                            <span class="online-user">
                                <span class="online-user-dot"></span>
                                Caricamento...
                            </span>
                        </div>
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
            inputField.style.height = Math.min(inputField.scrollHeight, 100) + 'px';
        });
        
        // Mobile-specific input handling
        if (this.isMobile) {
            inputField.addEventListener('focus', () => {
                // Ensure input stays visible when keyboard opens
                setTimeout(() => {
                    if (this.keyboardVisible) {
                        if (this.isIOS) {
                            inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                        } else {
                            inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                        }
                    }
                }, this.isIOS ? 700 : 400);
            });
            
            inputField.addEventListener('input', () => {
                // Keep input visible while typing on mobile
                if (this.keyboardVisible) {
                    setTimeout(() => {
                        inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                    }, this.isIOS ? 100 : 50);
                }
            });
            
            // iOS-specific: handle touch events to improve responsiveness
            if (this.isIOS) {
                inputField.addEventListener('touchstart', () => {
                    // Pre-emptively prepare for keyboard opening
                    setTimeout(() => {
                        if (document.activeElement === inputField) {
                            inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                        }
                    }, 100);
                });
            }
        }
        
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
        
        // Update original viewport height when opening chat
        if (this.isMobile) {
            this.originalViewportHeight = window.innerHeight;
        }
        
        // Focus input field with mobile-specific handling
        setTimeout(() => {
            const inputField = document.getElementById('chatInputField');
            if (inputField) {
                inputField.focus();
                
                // For mobile devices, ensure proper scrolling after focus
                if (this.isMobile) {
                    setTimeout(() => {
                        inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                        
                        // iOS sometimes needs an extra push
                        if (this.isIOS) {
                            setTimeout(() => {
                                inputField.scrollIntoView({ behavior: 'smooth', block: 'end' });
                            }, 400);
                        }
                    }, this.isIOS ? 400 : 300);
                }
            }
        }, 300);
        
        // Mark messages as read and update unread count immediately
        setTimeout(() => {
            this.markMessagesAsRead();
        }, 500);
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
            
            // Handle authentication errors
            if (response.status === 401) {
                console.warn('Authentication expired, stopping polling');
                this.stopPolling();
                return;
            }
            
            const data = await response.json();
            
            if (data.success && data.messages.length > 0) {
                this.displayMessages(data.messages);
                this.lastMessageTimestamp = data.messages[data.messages.length - 1].timestamp;
                
                // Update read status for existing messages in real-time
                this.updateExistingMessagesReadStatus(data.messages);
                
                // Update unread count only if chat is closed
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
    
    updateExistingMessagesReadStatus(newMessages) {
        // Update read status for messages that might have been read by others
        newMessages.forEach(message => {
            const existingMessageElement = document.querySelector(`[data-message-id="${message.id}"]`);
            if (existingMessageElement && message.user_id === this.getCurrentUserId()) {
                // This is our own message, update the read status
                const timeElement = existingMessageElement.querySelector('.message-time');
                if (timeElement) {
                    const readStatusElement = timeElement.querySelector('.message-read-status');
                    if (message.is_read && (!readStatusElement || !readStatusElement.classList.contains('fa-check-double'))) {
                        // Message was read, update to double check
                        if (readStatusElement) {
                            readStatusElement.className = 'fas fa-check-double message-read-status';
                            readStatusElement.style.color = '#4fc3f7';
                            readStatusElement.title = 'Letto';
                        }
                    }
                }
            }
        });
    }
    
    async updateOnlineUsers() {
        try {
            const response = await fetch('/chat/api/users/online');
            
            if (response.status === 401) {
                console.warn('Authentication expired for online users');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.displayOnlineUsers(data.users, data.total_online);
            }
        } catch (error) {
            console.error('Error updating online users:', error);
        }
    }
    
    displayOnlineUsers(users, totalOnline) {
        const onlineUsersList = document.getElementById('onlineUsersList');
        if (!onlineUsersList) return;
        
        if (users.length === 0) {
            onlineUsersList.innerHTML = `
                <span class="online-user">
                    <span class="online-user-dot"></span>
                    Nessuno online
                </span>
            `;
            return;
        }
        
        // Show max 3 users in the header, then show count
        const displayUsers = users.slice(0, 3);
        const remainingCount = Math.max(0, totalOnline - 3);
        
        let html = '';
        displayUsers.forEach(user => {
            const displayName = user.is_current ? 'Tu' : user.username;
            html += `
                <span class="online-user">
                    <span class="online-user-dot"></span>
                    ${this.escapeHtml(displayName)}
                </span>
            `;
        });
        
        if (remainingCount > 0) {
            html += `
                <span class="online-user">
                    <span class="online-user-dot"></span>
                    +${remainingCount}
                </span>
            `;
        }
        
        onlineUsersList.innerHTML = html;
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
        messageDiv.dataset.messageId = message.id;
        
        // Only show read status on OWN messages, and only if they are actually read
        // For own messages: show read indicator only if is_read is true
        const readStatus = isOwn && message.is_read ? 
            '<i class="fas fa-check-double message-read-status" title="Letto"></i>' : 
            (isOwn ? '<i class="fas fa-check message-read-status" style="color: #999;" title="Inviato"></i>' : '');
        
        messageDiv.innerHTML = `
            <div class="message-bubble">
                ${!isOwn ? `<div class="message-header">${this.escapeHtml(message.username)}</div>` : ''}
                <div class="message-text">${this.escapeHtml(message.message)}</div>
                <div class="message-time">
                    ${message.formatted_time}
                    ${readStatus}
                </div>
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
            
            if (response.status === 401) {
                console.warn('Authentication expired for unread count');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.unreadCount = data.unread_count;
                this.updateUnreadBadge();
                this.lastUnreadUpdate = Date.now();
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
        if (!this.isOpen) return;
        
        try {
            const response = await fetch('/chat/api/messages/mark-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.status === 401) {
                console.warn('Authentication expired for mark as read');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Reset unread count immediately
                this.unreadCount = 0;
                this.updateUnreadBadge();
                
                // Update read status of own messages in the UI
                this.updateOwnMessagesReadStatus();
            }
        } catch (error) {
            console.error('Error marking messages as read:', error);
        }
    }
    
    updateOwnMessagesReadStatus() {
        // Update all own messages to show as read (double check)
        const ownMessages = document.querySelectorAll('.message.own');
        ownMessages.forEach(messageElement => {
            const timeElement = messageElement.querySelector('.message-time');
            if (timeElement) {
                const readStatusElement = timeElement.querySelector('.message-read-status');
                if (readStatusElement && readStatusElement.classList.contains('fa-check')) {
                    // Update single check to double check
                    readStatusElement.className = 'fas fa-check-double message-read-status';
                    readStatusElement.style.color = '#4fc3f7';
                    readStatusElement.title = 'Letto';
                }
            }
        });
    }
    
    startPolling() {
        // Poll for new messages every 3 seconds
        this.pollInterval = setInterval(() => {
            this.pollForNewMessages();
        }, 3000);
        
        // Update online users every 10 seconds
        this.onlineUsersInterval = setInterval(() => {
            this.updateOnlineUsers();
        }, 10000);
        
        // Update unread count every 15 seconds, but only if chat is closed
        // and we haven't updated recently to avoid badge flicker
        setInterval(() => {
            if (!this.isOpen) {
                const now = Date.now();
                if (!this.lastUnreadUpdate || (now - this.lastUnreadUpdate) > 10000) {
                    this.updateUnreadCount();
                }
            }
        }, 15000);
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        
        if (this.onlineUsersInterval) {
            clearInterval(this.onlineUsersInterval);
            this.onlineUsersInterval = null;
        }
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    isScrolledToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return true;
        
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