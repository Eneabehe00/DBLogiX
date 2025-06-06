/**
 * Sistema Campanella Notifiche - JavaScript
 * Gestisce l'apertura del modale, il caricamento delle notifiche e le interazioni
 */

class NotificationBell {
    constructor() {
        this.modal = null;
        this.isLoading = false;
        this.currentNotifications = [];
        this.pollInterval = null;
        this.pollFrequency = 10000; // 10 secondi per aggiornamenti più veloci dei task completati
        
        this.init();
    }
    
    init() {
        // Inizializza elementi DOM
        this.modal = document.getElementById('notificationsModal');
        this.loadingElement = document.getElementById('notificationsLoading');
        this.containerElement = document.getElementById('notificationsContainer');
        this.emptyElement = document.getElementById('notificationsEmpty');
        
        // Inizializza event listeners
        this.initEventListeners();
        
        // Carica il conteggio iniziale
        this.updateNotificationCount();
        
        // Inizia il polling automatico
        this.startPolling();
        
        console.log('NotificationBell initialized');
    }
    
    initEventListeners() {
        // Campanelle (mobile e desktop)
        const bellButtons = document.querySelectorAll('#mobile-notification-bell, #sidebar-notification-bell');
        bellButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openModal();
            });
        });
        
        // Pulsante segna tutto come letto
        const markAllBtn = document.getElementById('markAllAsReadBtn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
        
        // Evento quando il modale viene nascosto
        if (this.modal) {
            this.modal.addEventListener('hidden.bs.modal', () => {
                this.onModalHidden();
            });
        }
    }
    
    async openModal() {
        if (this.modal) {
            // Mostra il modale
            const modalInstance = new bootstrap.Modal(this.modal);
            modalInstance.show();
            
            // Carica le notifiche
            await this.loadNotifications();
        }
    }
    
    async loadNotifications() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const response = await fetch('/tasks/api/notifications/unread', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.currentNotifications = data.notifications;
                this.renderNotifications(data.notifications);
                this.updateNotificationCount(data.unread_count);
            } else {
                throw new Error(data.error || 'Errore nel caricamento delle notifiche');
            }
            
        } catch (error) {
            console.error('Errore nel caricamento delle notifiche:', error);
            this.showError('Errore nel caricamento delle notifiche. Riprova.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }
    
    renderNotifications(notifications) {
        if (!this.containerElement) return;
        
        if (notifications.length === 0) {
            this.showEmpty();
            return;
        }
        
        this.hideEmpty();
        this.hideLoading();
        
        const html = notifications.map(notification => {
            return this.createNotificationHTML(notification);
        }).join('');
        
        this.containerElement.innerHTML = html;
        this.containerElement.style.display = 'block';
        
        // Aggiungi event listeners per le azioni
        this.attachNotificationEventListeners();
    }
    
    createNotificationHTML(notification) {
        const iconClass = this.getNotificationIcon(notification.type);
        const typeClass = notification.type.replace('_', '-');
        
        return `
            <div class="notification-item-modal ${!notification.is_read ? 'unread' : ''}" 
                 data-notification-id="${notification.id}" 
                 data-task-id="${notification.task_id}">
                <div class="notification-icon ${typeClass}">
                    <i class="${iconClass}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${this.escapeHtml(notification.title)}</div>
                    <div class="notification-message">${this.escapeHtml(notification.message)}</div>
                    <div class="notification-meta">
                        <span class="notification-time">${notification.created_at_relative}</span>
                        <div class="notification-actions">
                            ${!notification.is_read ? `
                                <button class="notification-action-btn mark-read" 
                                        onclick="notificationBell.markAsRead(${notification.id}); event.stopPropagation();">
                                    <i class="fas fa-check"></i> Letto
                                </button>
                            ` : ''}
                            <button class="notification-action-btn view-task" 
                                    onclick="notificationBell.viewTask(${notification.task_id}); event.stopPropagation();">
                                <i class="fas fa-eye"></i> Vedi Task
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    getNotificationIcon(type) {
        switch (type) {
            case 'task_assigned':
                return 'fas fa-user-plus';
            case 'task_completed':
                return 'fas fa-check-circle';
            case 'task_reassigned':
                return 'fas fa-exchange-alt';
            default:
                return 'fas fa-info-circle';
        }
    }
    
    attachNotificationEventListeners() {
        // Click su notifica per andare al task
        const notificationItems = document.querySelectorAll('.notification-item-modal');
        notificationItems.forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('notification-action-btn')) {
                    return; // Non gestire se si clicca sui pulsanti
                }
                
                const taskId = item.dataset.taskId;
                if (taskId) {
                    this.viewTask(parseInt(taskId));
                }
            });
        });
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/tasks/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    csrf_token: this.getCSRFToken()
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Rimuovi la notifica dalla vista
                const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
                if (notificationElement) {
                    notificationElement.style.opacity = '0.5';
                    notificationElement.classList.remove('unread');
                    
                    // Rimuovi pulsante "Letto"
                    const markReadBtn = notificationElement.querySelector('.mark-read');
                    if (markReadBtn) {
                        markReadBtn.remove();
                    }
                }
                
                // Aggiorna il conteggio
                this.updateNotificationCount();
                
                // Mostra feedback
                this.showNotificationFeedback('Notifica segnata come letta', 'success');
                
            } else {
                throw new Error(data.message || 'Errore nel segnare la notifica come letta');
            }
            
        } catch (error) {
            console.error('Errore nel segnare notifica come letta:', error);
            this.showNotificationFeedback('Errore nel segnare la notifica come letta', 'error');
        }
    }
    
    async markAllAsRead() {
        if (this.currentNotifications.filter(n => !n.is_read).length === 0) {
            this.showNotificationFeedback('Non ci sono notifiche non lette', 'info');
            return;
        }
        
        try {
            const response = await fetch('/tasks/notifications/mark-all-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    csrf_token: this.getCSRFToken()
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Ricarica le notifiche
                await this.loadNotifications();
                
                this.showNotificationFeedback(`${data.marked_count || 0} notifiche segnate come lette`, 'success');
                
            } else {
                throw new Error(data.error || 'Errore nel segnare le notifiche come lette');
            }
            
        } catch (error) {
            console.error('Errore nel segnare tutte le notifiche come lette:', error);
            this.showNotificationFeedback('Errore nel segnare le notifiche come lette', 'error');
        }
    }
    
    viewTask(taskId) {
        // Chiudi il modale
        const modalInstance = bootstrap.Modal.getInstance(this.modal);
        if (modalInstance) {
            modalInstance.hide();
        }
        
        // Vai alla pagina del task
        window.location.href = `/tasks/task/${taskId}`;
    }
    
    async updateNotificationCount(count = null) {
        if (count === null) {
            try {
                const response = await fetch('/tasks/api/notifications/unread');
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        count = data.unread_count;
                    }
                }
            } catch (error) {
                console.error('Errore nel recuperare il conteggio notifiche:', error);
                return;
            }
        }
        
        // Aggiorna i badge
        const badges = document.querySelectorAll('#mobile-notification-badge, #sidebar-notification-badge');
        badges.forEach(badge => {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count.toString();
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        });
        
        // Aggiorna anche il contatore dei task completati per gli admin
        this.updateTaskCompletedCount();
    }
    
    async updateTaskCompletedCount() {
        try {
            const response = await fetch('/tasks/api/notifications/completed-count');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    const completedCount = data.completed_count;
                    
                    // Trova il badge nel link dei task nella sidebar
                    const taskLink = document.querySelector('a[href*="tasks.index"]');
                    if (taskLink) {
                        let badge = taskLink.querySelector('.badge.bg-success');
                        
                        if (completedCount > 0) {
                            if (!badge) {
                                // Crea il badge se non esiste
                                badge = document.createElement('span');
                                badge.className = 'badge bg-success position-absolute';
                                badge.style.cssText = 'top: 8px; right: 15px; font-size: 0.7rem; padding: 3px 6px; border-radius: 10px; min-width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;';
                                taskLink.appendChild(badge);
                            }
                            badge.textContent = completedCount > 99 ? '99+' : completedCount.toString();
                            badge.style.display = 'flex';
                        } else if (badge) {
                            badge.style.display = 'none';
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Errore nel recuperare il conteggio task completati:', error);
        }
    }
    
    showLoading() {
        if (this.loadingElement) {
            this.loadingElement.style.display = 'flex';
        }
        if (this.containerElement) {
            this.containerElement.style.display = 'none';
        }
        if (this.emptyElement) {
            this.emptyElement.style.display = 'none';
        }
    }
    
    hideLoading() {
        if (this.loadingElement) {
            this.loadingElement.style.display = 'none';
        }
    }
    
    showEmpty() {
        if (this.emptyElement) {
            this.emptyElement.style.display = 'flex';
        }
        if (this.containerElement) {
            this.containerElement.style.display = 'none';
        }
    }
    
    hideEmpty() {
        if (this.emptyElement) {
            this.emptyElement.style.display = 'none';
        }
    }
    
    showError(message) {
        if (this.containerElement) {
            this.containerElement.innerHTML = `
                <div class="notification-error-state">
                    <div class="error-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <h6>Errore</h6>
                    <p>${message}</p>
                    <button class="btn btn-primary btn-sm" onclick="notificationBell.loadNotifications()">
                        <i class="fas fa-retry"></i> Riprova
                    </button>
                </div>
            `;
            this.containerElement.style.display = 'block';
        }
    }
    
    showNotificationFeedback(message, type = 'info') {
        // Utilizza il sistema di notifiche esistente se disponibile
        if (window.NotificationSystem && window.NotificationSystem.show) {
            window.NotificationSystem.show(message, type);
        } else {
            // Fallback con alert
            alert(message);
        }
    }
    
    onModalHidden() {
        // Aggiorna il conteggio quando il modale viene chiuso
        setTimeout(() => {
            this.updateNotificationCount();
        }, 500);
    }
    
    startPolling() {
        this.pollInterval = setInterval(() => {
            this.updateNotificationCount();
        }, this.pollFrequency);
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inizializza quando il DOM è pronto
document.addEventListener('DOMContentLoaded', function() {
    // Verifica che l'utente sia autenticato
    if (document.querySelector('meta[name="current-user-id"]')) {
        window.notificationBell = new NotificationBell();
    }
});

// Pulisci quando la pagina viene scaricata
window.addEventListener('beforeunload', function() {
    if (window.notificationBell) {
        window.notificationBell.stopPolling();
    }
}); 