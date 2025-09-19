/**
 * Sistema Notifiche Eleganti Unificato
 * Gestisce tutte le notifiche del progetto con stile uniforme
 * Versione ottimizzata per ridurre il clutter
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.activeNotifications = [];
        this.maxNotifications = 3; // Massimo 3 notifiche simultanee
        this.recentMessages = new Map(); // Per evitare duplicati
        this.duplicateTimeout = 3000; // 3 secondi per considerare un messaggio duplicato
        this.ignoredMessages = new Set([
            // Messaggi informativi ridondanti da ignorare (solo quelli veramente spam)
            'Nessun codice EAN assegnato a questo prodotto.',
            'Nessuna Classe Assegnata Questo prodotto non ha una classe di tracciabilità assegnata.',
            'La tracciabilità sarà disponibile solo dopo aver assegnato una classe di tracciabilità a questo articolo.',
            'Tutti i ticket associati torneranno allo stato Enviado = 0 e saranno di nuovo disponibili per altri task.',
            'Conseguenze: Tutti i ticket associati torneranno allo stato Enviado = 0 (solo se non hanno DDT generato) Tutte le scansioni e i progressi saranno persi Tutte le notifiche saranno eliminate I ticket senza DDT saranno nuovamente disponibili per l\'assegnazione',
            // Messaggi dei modali (non dovrebbero apparire comunque)
            'Task completato! Tutti i prodotti sono stati verificati.',
            'Verrà generato un Documento di Trasporto con tutti i prodotti verificati del task.',
            'DDT già generato! Questo task ha già generato il DDT #5. I ticket associati resteranno processati (Enviado = 1) perché già inclusi nel DDT ufficiale.',
            'L\'utente riceverà una notifica dell\'assegnazione del task.',
            'Questa azione è irreversibile.',
            'Attenzione! Questa azione è irreversibile.',
            'Stai per eliminare il task:',
            'Tutti i ticket associati torneranno allo stato Enviado = 0 e saranno di nuovo disponibili per altri task.',
            // Notifiche amministrative ridondanti
            'Riavvia l\'applicazione per applicare le modifiche.',
            'Riavvia l\'app per applicare le modifiche.',
            'Impossibile aggiornare il timeout sessioni nel file config.py',
            'Logo esistente',
            'migrato automaticamente a LogoDDT.png',
            // Messaggi informativi generici troppo verbosi
            'Configurazione database salvata con successo!',
            'Configurazione azienda salvata con successo!',
            'Configurazione sessioni aggiornata nel file config.py.',
            'Tutte le configurazioni sistema sono state salvate con successo!',
            // Messaggi tecnici per sviluppatori
            'Error loading text fields:',
            'Error activating existing EAN scanner',
            'Article created but EAN scanner could not be saved',
            'Article created but balanza association could not be saved',
            'Article created but tienda association could not be saved',
            'Article updated but EAN scanner could not be saved'
        ]);
        this.init();
    }

    init() {
        // Crea il container per le notifiche se non esiste
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'elegant-notifications-container';
            this.container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                pointer-events: none;
                max-width: 400px;
                width: auto;
            `;
            document.body.appendChild(this.container);
        }
    }

    // Controlla se un messaggio dovrebbe essere ignorato per evitare duplicati
    shouldIgnoreMessage(message) {
        if (!message || typeof message !== 'string' || message.trim() === '') {
            return true;
        }
        
        // Controlla se il messaggio è nei messaggi da ignorare
        const cleanMessage = message.trim().toLowerCase();
        for (const ignoredMessage of this.ignoredMessages) {
            if (cleanMessage.includes(ignoredMessage.toLowerCase().trim())) {
                return true;
            }
        }
        
        // Controlla se abbiamo già mostrato questo messaggio di recente
        const now = Date.now();
        const messageKey = cleanMessage;
        
        // Se abbiamo già questo messaggio nei recenti, controlla se è ancora valido
        if (this.recentMessages.has(messageKey)) {
            const lastShown = this.recentMessages.get(messageKey);
            if (now - lastShown < this.duplicateTimeout) {
                console.log(`Messaggio duplicato ignorato: "${message}"`);
                return true; // Ignora duplicato
            }
        }
        
        // Salva il timestamp di questo messaggio
        this.recentMessages.set(messageKey, now);
        
        // Pulisci messaggi vecchi dalla cache per evitare memory leak
        this.recentMessages.forEach((timestamp, key) => {
            if (now - timestamp > this.duplicateTimeout * 2) {
                this.recentMessages.delete(key);
            }
        });
        
        return false;
    }

    // Gestisce il limite di notifiche simultanee
    manageNotificationLimit() {
        if (this.activeNotifications.length >= this.maxNotifications) {
            // Rimuovi la notifica più vecchia (solo se non è un errore)
            const oldestNonError = this.activeNotifications.find(n => 
                !n.dataset.type || !['error', 'danger'].includes(n.dataset.type)
            );
            
            if (oldestNonError) {
                this.dismiss(oldestNonError);
            }
        }
    }

    show(message, type = 'success', duration = 5000) {
        // Filtra messaggi ridondanti
        if (this.shouldIgnoreMessage(message)) {
            return null;
        }

        // Gestisci limite notifiche
        this.manageNotificationLimit();

        const notification = this.createNotification(message, type, duration);
        this.container.appendChild(notification);
        this.activeNotifications.push(notification);

        // Animazione di entrata
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
            notification.style.opacity = '1';
        }, 100);

        // Auto-dismiss (solo per successi e info, non per errori)
        if (duration > 0 && !['error', 'danger'].includes(type)) {
            setTimeout(() => {
                this.dismiss(notification);
            }, duration);
        } else if (['error', 'danger'].includes(type)) {
            // Gli errori rimangono più a lungo
            setTimeout(() => {
                this.dismiss(notification);
            }, duration * 1.5);
        }

        return notification;
    }

    createNotification(message, type, duration) {
        const notification = document.createElement('div');
        const config = this.getTypeConfig(type);
        
        notification.className = 'elegant-notification';
        notification.dataset.type = type;
        
        notification.style.cssText = `
            background: ${config.background};
            backdrop-filter: blur(10px);
            border: 1px solid ${config.border};
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
            color: ${config.color};
            margin-bottom: 16px;
            min-height: 60px;
            opacity: 0;
            padding: 16px 20px;
            pointer-events: auto;
            position: relative;
            transform: translateX(100%);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            max-width: 380px;
            word-wrap: break-word;
        `;

        notification.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="flex-shrink: 0; margin-top: 2px;">
                    <i class="fas ${config.icon}" style="color: ${config.accent}; font-size: 18px;"></i>
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-weight: 600; margin-bottom: 4px; line-height: 1.3;">
                        ${config.title}
                    </div>
                    <div style="font-size: 14px; line-height: 1.4; opacity: 0.9;">
                        ${message}
                    </div>
                </div>
                <div style="flex-shrink: 0;">
                    <button type="button" onclick="notificationSystem.dismiss(this.closest('.elegant-notification'))" 
                            style="background: none; border: none; color: ${config.color}; opacity: 0.7; cursor: pointer; padding: 4px; border-radius: 4px; transition: all 0.2s ease;">
                        <i class="fas fa-times" style="font-size: 14px;"></i>
                    </button>
                </div>
            </div>
        `;

        // Progress bar per notifiche temporizzate (solo per non-errori)
        if (duration > 0 && !['error', 'danger'].includes(type)) {
            const progressBar = document.createElement('div');
            progressBar.style.cssText = `
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: ${config.accent};
                opacity: 0.6;
                transition: width ${duration}ms linear;
                width: 100%;
            `;
            notification.appendChild(progressBar);

            setTimeout(() => {
                progressBar.style.width = '0%';
            }, 100);
        }

        return notification;
    }

    dismiss(notification) {
        if (!notification || !notification.parentNode) return;

        // Rimuovi dalla lista attiva
        const index = this.activeNotifications.indexOf(notification);
        if (index > -1) {
            this.activeNotifications.splice(index, 1);
        }

        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';

        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    getTypeConfig(type) {
        const configs = {
            success: {
                title: 'Operazione completata',
                icon: 'fa-check-circle',
                background: 'rgba(16, 185, 129, 0.95)',
                color: '#ffffff',
                border: '#10b981',
                accent: '#059669'
            },
            error: {
                title: 'Errore',
                icon: 'fa-exclamation-circle',
                background: 'rgba(239, 68, 68, 0.95)',
                color: '#ffffff',
                border: '#ef4444',
                accent: '#dc2626'
            },
            warning: {
                title: 'Attenzione',
                icon: 'fa-exclamation-triangle',
                background: 'rgba(245, 158, 11, 0.95)',
                color: '#ffffff',
                border: '#f59e0b',
                accent: '#d97706'
            },
            info: {
                title: 'Informazione',
                icon: 'fa-info-circle',
                background: 'rgba(59, 130, 246, 0.95)',
                color: '#ffffff',
                border: '#3b82f6',
                accent: '#2563eb'
            },
            danger: {
                title: 'Errore critico',
                icon: 'fa-times-circle',
                background: 'rgba(220, 38, 38, 0.95)',
                color: '#ffffff',
                border: '#dc2626',
                accent: '#991b1b'
            }
        };

        return configs[type] || configs.info;
    }

    // Metodi di convenienza con filtri aggiuntivi
    success(message, duration = 3000) { // Durata ridotta per successi
        return this.show(message, 'success', duration);
    }

    error(message, duration = 8000) { // Errori durano di più
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 5000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 4000) { // Info durata ridotta
        return this.show(message, 'info', duration);
    }

    danger(message, duration = 10000) { // Pericoli durano molto di più
        return this.show(message, 'danger', duration);
    }

    // Pulisce tutte le notifiche
    clear() {
        const notifications = this.container.querySelectorAll('.elegant-notification');
        notifications.forEach(notification => this.dismiss(notification));
        this.activeNotifications = [];
    }

    // Converte le flash messages esistenti (metodo pubblico) con filtri
    convertFlashMessages() {
        // Cerca TUTTE le flash messages nella pagina, non solo nel flash-container
        // MA esclude quelli dentro ai modali
        const alerts = document.querySelectorAll('.alert:not(.elegant-notification):not(.notification-converted)');
        
        alerts.forEach(alert => {
            // Controlla se l'alert è all'interno di un modale
            const isInModal = alert.closest('.modal') !== null;
            const isInDropdown = alert.closest('.dropdown-menu') !== null;
            const isInOffcanvas = alert.closest('.offcanvas') !== null;
            const isInTooltip = alert.closest('.tooltip') !== null;
            const isInPopover = alert.closest('.popover') !== null;
            
            // Salta gli alert che fanno parte di componenti UI
            if (isInModal || isInDropdown || isInOffcanvas || isInTooltip || isInPopover) {
                return; // Non convertire questi alert
            }
            
            const classList = Array.from(alert.classList);
            let type = 'info';
            
            if (classList.includes('alert-success')) type = 'success';
            else if (classList.includes('alert-danger')) type = 'error';
            else if (classList.includes('alert-warning')) type = 'warning';
            else if (classList.includes('alert-error')) type = 'error';
            
            // Estrae il testo pulito (senza i bottoni di chiusura)
            const textElement = alert.cloneNode(true);
            const closeButtons = textElement.querySelectorAll('.btn-close, button');
            closeButtons.forEach(btn => btn.remove());
            
            const message = textElement.textContent.trim();
            if (message) {
                // Marca subito come convertita per evitare duplicati
                alert.classList.add('notification-converted');
                
                // Usa il sistema di filtraggio
                const notification = this.show(message, type);
                
                if (notification) { // Solo se la notifica non è stata filtrata
                    // Nasconde l'alert originale
                    alert.style.display = 'none';
                }
            }
        });
    }
}

// Inizializza il sistema globale
window.notificationSystem = new NotificationSystem();

// Intercetta e sostituisce gli alert nativi
window.originalAlert = window.alert;
window.alert = function(message) {
    notificationSystem.info(message);
};

// Intercetta e converte le flash messages esistenti
document.addEventListener('DOMContentLoaded', function() {
    // Controlla se siamo in una pagina di navigazione semplice (senza form submission)
    const isSimpleNavigation = !document.referrer.includes('?') && 
                               !window.location.search.includes('success=') &&
                               !window.location.search.includes('action=') &&
                               !window.location.hash.includes('created') &&
                               !window.location.hash.includes('updated');
    
    // Se è una navigazione semplice, riduci ulteriormente il timeout per evitare accumulo
    if (isSimpleNavigation) {
        notificationSystem.duplicateTimeout = 1000; // Solo 1 secondo per duplicati
        notificationSystem.maxNotifications = 2; // Massimo 2 notifiche
    }
    
    // Conversione iniziale delle flash messages
    notificationSystem.convertFlashMessages();
    
    // Controllo periodico più conservativo per flash messages che potrebbero apparire con ritardo
    let checkCount = 0;
    const maxChecks = 3; // Ridotto ulteriormente il numero di controlli
    
    const periodicCheck = setInterval(() => {
        notificationSystem.convertFlashMessages();
        checkCount++;
        
        if (checkCount >= maxChecks) {
            clearInterval(periodicCheck);
        }
    }, 1000); // Controllo meno frequente
    
    // Osserva per flash messages aggiunte dinamicamente - versione migliorata
    const observer = new MutationObserver(function(mutations) {
        let shouldCheck = false;
        
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    // Cerca alert nel nodo aggiunto che non sono già stati convertiti
                    const alerts = node.classList && node.classList.contains('alert') && !node.classList.contains('notification-converted') ? [node] : 
                                  node.querySelectorAll ? node.querySelectorAll('.alert:not(.elegant-notification):not(.notification-converted)') : [];
                    
                    if (alerts.length > 0) {
                        shouldCheck = true;
                    }
                }
            });
        });
        
        if (shouldCheck) {
            // Debounce per evitare conversioni multiple
            setTimeout(() => {
                notificationSystem.convertFlashMessages();
            }, 200);
        }
    });
    
    observer.observe(document.body, { 
        childList: true, 
        subtree: true 
    });
});

// Esporta per l'uso globale con filtri
window.showNotification = function(message, type = 'success', duration = 5000) {
    return notificationSystem.show(message, type, duration);
};

window.showSuccess = function(message) {
    return notificationSystem.success(message);
};

window.showError = function(message) {
    return notificationSystem.error(message);
};

window.showWarning = function(message) {
    return notificationSystem.warning(message);
};

window.showInfo = function(message) {
    return notificationSystem.info(message);
}; 