/**
 * FORNITORI JavaScript - DBLogiX
 * Gestione funzionalità JavaScript per la sezione fornitori
 */

class FornitoriManager {
    constructor() {
        this.init();
    }

    /**
     * Inizializzazione del gestore fornitori
     */
    init() {
        this.setupFormValidation();
        this.setupSearchFilters();
        this.setupFormatting();
        this.setupContactActions();
        this.setupChangeTracking();
        this.setupKeyboardShortcuts();
        this.setupTooltips();
        this.setupAnimations();
        this.setupTableClickableRows();
        
        console.log('✅ FornitoriManager inizializzato');
    }

    /**
     * Configurazione validazione form
     */
    setupFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');
        
        forms.forEach(form => {
            // Validazione Bootstrap
            form.addEventListener('submit', (event) => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                    this.showValidationErrors(form);
                }
                form.classList.add('was-validated');
            }, false);

            // Validazione real-time per campi specifici
            this.setupFieldValidation(form);
        });
    }

    /**
     * Configurazione validazione campi specifici
     */
    setupFieldValidation(form) {
        // Email validation
        const emailField = form.querySelector('#email');
        if (emailField) {
            emailField.addEventListener('blur', () => {
                this.validateEmail(emailField);
            });
        }

        // Partita IVA validation
        const pIvaField = form.querySelector('#partita_iva');
        if (pIvaField) {
            pIvaField.addEventListener('blur', () => {
                this.validatePartitaIVA(pIvaField);
            });
        }

        // Codice fiscale validation
        const cfField = form.querySelector('#codice_fiscale');
        if (cfField) {
            cfField.addEventListener('blur', () => {
                this.validateCodiceFiscale(cfField);
            });
        }

        // IBAN validation
        const ibanField = form.querySelector('#iban');
        if (ibanField) {
            ibanField.addEventListener('input', () => {
                this.formatIBAN(ibanField);
            });
            ibanField.addEventListener('blur', () => {
                this.validateIBAN(ibanField);
            });
        }
    }

    /**
     * Validazione email
     */
    validateEmail(field) {
        const email = field.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (email && !emailRegex.test(email)) {
            this.setFieldError(field, 'Inserisci un indirizzo email valido');
            return false;
        } else {
            this.clearFieldError(field);
            return true;
        }
    }

    /**
     * Validazione Partita IVA italiana
     */
    validatePartitaIVA(field) {
        const piva = field.value.replace(/\s/g, '');
        
        if (piva && piva.length > 0) {
            if (!/^\d{11}$/.test(piva)) {
                this.setFieldError(field, 'La Partita IVA deve essere di 11 cifre');
                return false;
            }
            
            // Algoritmo di controllo P.IVA italiana
            if (!this.checkPartitaIVA(piva)) {
                this.setFieldError(field, 'Partita IVA non valida');
                return false;
            }
        }
        
        this.clearFieldError(field);
        return true;
    }

    /**
     * Algoritmo controllo Partita IVA
     */
    checkPartitaIVA(piva) {
        let sum = 0;
        for (let i = 0; i < 10; i++) {
            let digit = parseInt(piva.charAt(i));
            if (i % 2 === 1) {
                digit *= 2;
                if (digit > 9) digit = digit - 9;
            }
            sum += digit;
        }
        const checkDigit = (10 - (sum % 10)) % 10;
        return checkDigit === parseInt(piva.charAt(10));
    }

    /**
     * Validazione Codice Fiscale
     */
    validateCodiceFiscale(field) {
        const cf = field.value.toUpperCase().replace(/\s/g, '');
        
        if (cf && cf.length > 0) {
            if (!/^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$/.test(cf)) {
                this.setFieldError(field, 'Formato codice fiscale non valido');
                return false;
            }
        }
        
        this.clearFieldError(field);
        return true;
    }

    /**
     * Formattatzione IBAN
     */
    formatIBAN(field) {
        let value = field.value.replace(/\s+/g, '').replace(/[^A-Z0-9]/gi, '');
        let formattedValue = value.match(/.{1,4}/g)?.join(' ') || value;
        field.value = formattedValue.toUpperCase();
    }

    /**
     * Validazione IBAN
     */
    validateIBAN(field) {
        const iban = field.value.replace(/\s/g, '');
        
        if (iban && iban.length > 0) {
            if (!/^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$/.test(iban)) {
                this.setFieldError(field, 'Formato IBAN non valido');
                return false;
            }
        }
        
        this.clearFieldError(field);
        return true;
    }

    /**
     * Imposta errore su campo
     */
    setFieldError(field, message) {
        field.setCustomValidity(message);
        field.classList.add('is-invalid');
        
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.appendChild(feedback);
        }
        feedback.textContent = message;
    }

    /**
     * Rimuove errore da campo
     */
    clearFieldError(field) {
        field.setCustomValidity('');
        field.classList.remove('is-invalid');
        
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    /**
     * Mostra errori di validazione
     */
    showValidationErrors(form) {
        const firstInvalid = form.querySelector('.is-invalid, :invalid');
        if (firstInvalid) {
            firstInvalid.focus();
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    /**
     * Configurazione filtri e ricerca
     */
    setupSearchFilters() {
        // Auto-submit form on sort change
        const sortSelect = document.querySelector('select[name="sort"]');
        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                this.form.submit();
            });
        }

        // Enhanced search with enter key
        const searchInput = document.querySelector('input[name="search"]');
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    this.form.submit();
                }
            });

            // Debounced search
            let searchTimeout;
            searchInput.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    if (this.value.length >= 3 || this.value.length === 0) {
                        this.form.submit();
                    }
                }, 800);
            });
        }

        // Clear search button
        const clearBtn = document.querySelector('.search-clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (searchInput) {
                    searchInput.value = '';
                    searchInput.form.submit();
                }
            });
        }
    }

    /**
     * Configurazione formattazione automatica
     */
    setupFormatting() {
        // CAP formatting (solo numeri)
        const capField = document.querySelector('#cap');
        if (capField) {
            capField.addEventListener('input', function() {
                this.value = this.value.replace(/[^0-9]/g, '');
            });

            // Auto-complete provincia/città da CAP
            capField.addEventListener('blur', () => {
                this.autoCompleteFromCAP(capField);
            });
        }

        // Provincia to uppercase
        const provinciaField = document.querySelector('#provincia');
        if (provinciaField) {
            provinciaField.addEventListener('input', function() {
                this.value = this.value.toUpperCase();
            });
        }

        // Phone number formatting
        const telefonoField = document.querySelector('#telefono');
        if (telefonoField) {
            telefonoField.addEventListener('input', function() {
                let value = this.value.replace(/[^0-9+\s()-]/g, '');
                this.value = value;
            });
        }
    }

    /**
     * Auto-completamento da CAP
     */
    autoCompleteFromCAP(capField) {
        const cap = capField.value;
        const paeseField = document.querySelector('#paese');
        const provinciaField = document.querySelector('#provincia');

        if (cap.length === 5 && paeseField && paeseField.value === 'Italia') {
            const capMappings = {
                '00': { provincia: 'RM' }, '10': { provincia: 'TO' },
                '20': { provincia: 'MI' }, '30': { provincia: 'VE' },
                '40': { provincia: 'BO' }, '50': { provincia: 'FI' },
                '60': { provincia: 'AN' }, '70': { provincia: 'BA' },
                '80': { provincia: 'NA' }, '90': { provincia: 'PA' }
            };

            const prefix = cap.substring(0, 2);
            const mapping = capMappings[prefix];
            
            if (mapping && provinciaField && !provinciaField.value) {
                provinciaField.value = mapping.provincia;
                this.animateField(provinciaField);
            }
        }
    }

    /**
     * Configurazione azioni contatti
     */
    setupContactActions() {
        // Click-to-call functionality
        document.querySelectorAll('a[href^="tel:"]').forEach(link => {
            link.addEventListener('click', function(e) {
                if (!navigator.userAgent.match(/Mobile|iP(hone|od|ad)|Android|BlackBerry|IEMobile/)) {
                    e.preventDefault();
                    this.showCallDialog(this.href.replace('tel:', ''));
                }
            }.bind(this));
        });

        // Click-to-email functionality
        document.querySelectorAll('a[href^="mailto:"]').forEach(link => {
            link.addEventListener('click', function(e) {
                // Analytics tracking potrebbe andare qui
                console.log('Email click:', this.href);
            });
        });
    }

    /**
     * Mostra dialog per chiamata
     */
    showCallDialog(phoneNumber) {
        const dialog = document.createElement('div');
        dialog.className = 'alert alert-info alert-dismissible fade show position-fixed';
        dialog.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        dialog.innerHTML = `
            <i class="fas fa-phone me-2"></i>
            Numero copiato negli appunti: <strong>${phoneNumber}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(dialog);

        // Copia negli appunti
        navigator.clipboard.writeText(phoneNumber).catch(() => {
            console.log('Clipboard copy failed');
        });

        // Rimuovi dopo 3 secondi
        setTimeout(() => {
            if (dialog.parentNode) {
                dialog.remove();
            }
        }, 3000);
    }

    /**
     * Tracking modifiche form
     */
    setupChangeTracking() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            let formChanged = false;
            const originalData = new FormData(form);

            // Track changes
            form.addEventListener('input', () => {
                formChanged = true;
                this.updateSaveButton();
            });

            // Warn before leaving if unsaved changes
            window.addEventListener('beforeunload', (e) => {
                if (formChanged) {
                    e.preventDefault();
                    e.returnValue = 'Hai modifiche non salvate. Sei sicuro di voler uscire?';
                }
            });

            // Reset tracking on form submit
            form.addEventListener('submit', () => {
                formChanged = false;
            });

            // Store form state for comparison
            form.setAttribute('data-original', JSON.stringify(Array.from(originalData.entries())));
        });
    }

    /**
     * Aggiorna stato pulsante salva
     */
    updateSaveButton() {
        const saveButtons = document.querySelectorAll('button[type="submit"]');
        saveButtons.forEach(btn => {
            btn.classList.add('btn-warning');
            btn.innerHTML = '<i class="fas fa-save"></i> Salva Modifiche';
        });
    }

    /**
     * Configurazione shortcut tastiera
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+S per salvare
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                const submitBtn = document.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.click();
                }
            }

            // Ctrl+F per ricerca
            if (e.ctrlKey && e.key === 'f') {
                const searchInput = document.querySelector('input[name="search"]');
                if (searchInput) {
                    e.preventDefault();
                    searchInput.focus();
                    searchInput.select();
                }
            }

            // Escape per cancellare
            if (e.key === 'Escape') {
                const cancelBtn = document.querySelector('a[href*="list"], a[href*="index"]');
                if (cancelBtn && confirm('Vuoi annullare e tornare alla lista?')) {
                    window.location.href = cancelBtn.href;
                }
            }
        });
    }

    /**
     * Configurazione tooltip
     */
    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Custom tooltips for validation
        document.querySelectorAll('.form-control').forEach(field => {
            const help = field.parentNode.querySelector('.form-help');
            if (help) {
                field.setAttribute('title', help.textContent);
                field.setAttribute('data-bs-toggle', 'tooltip');
                field.setAttribute('data-bs-placement', 'top');
            }
        });
    }

    /**
     * Configurazione animazioni
     */
    setupAnimations() {
        // Animazione apparizione card e tabelle
        const elements = document.querySelectorAll('.fornitore-card, .form-section, .detail-section, .table');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = 'fadeInUp 0.3s ease forwards';
                }
            });
        }, { threshold: 0.1 });

        elements.forEach(element => observer.observe(element));

        // Smooth scroll per link interni
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

        /**
     * Configurazione righe cliccabili nella tabella
     */
    setupTableClickableRows() {
        const clickableRows = document.querySelectorAll('.clickable-row');

        clickableRows.forEach(row => {
            // Aggiungi indicatori visivi per accessibilità
            row.setAttribute('role', 'button');
            row.setAttribute('tabindex', '0');

            // Click handler
            row.addEventListener('click', function(e) {
                // Non seguire il link se l'utente ha cliccato su un link/pulsante all'interno della riga
                if (e.target.tagName === 'A' || e.target.closest('a') ||
                    e.target.tagName === 'BUTTON' || e.target.closest('button') ||
                    e.target.tagName === 'FORM' || e.target.closest('form')) {
                    return;
                }

                const href = this.getAttribute('data-href');
                if (href) {
                    // Feedback visivo
                    this.style.background = 'rgba(0, 123, 255, 0.1)';

                    // Navigazione con delay per mostrare il feedback
                    setTimeout(() => {
                        window.location.href = href;
                    }, 100);
                }
            });

            // Keyboard navigation
            row.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });

            // Miglioramento hover effect
            row.addEventListener('mouseenter', function() {
                if (!this.classList.contains('table-row-active')) {
                    this.style.background = 'rgba(0, 123, 255, 0.05)';
                }
            });

            row.addEventListener('mouseleave', function() {
                if (!this.classList.contains('table-row-active')) {
                    this.style.background = '';
                }
            });

            // Aggiungi tooltip informativo per le righe dei fornitori
            const fornitoreNome = row.querySelector('.fornitore-name-cell .fw-semibold')?.textContent;
            if (fornitoreNome && !row.hasAttribute('title')) {
                row.setAttribute('title', `Clicca per visualizzare i dettagli di ${fornitoreNome}`);
            }

            // Aggiungi tooltip informativo per le righe degli ingredienti
            const ingredienteNome = row.querySelector('.ingrediente-name-cell .fw-semibold')?.textContent;
            if (ingredienteNome && !row.hasAttribute('title')) {
                row.setAttribute('title', `Clicca per visualizzare i dettagli di ${ingredienteNome}`);
            }
        });

        // Gestione ordinamento colonne (se necessario in futuro)
        this.setupTableSorting();
    }

    /**
     * Configurazione ordinamento tabella (preparazione per future funzionalità)
     */
    setupTableSorting() {
        const sortableHeaders = document.querySelectorAll('.table th[data-sort]');
        
        sortableHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const sortField = this.getAttribute('data-sort');
                const currentSort = new URLSearchParams(window.location.search).get('sort');
                const newSort = currentSort === sortField ? `-${sortField}` : sortField;
                
                // Aggiorna URL con nuovo ordinamento
                const url = new URL(window.location);
                url.searchParams.set('sort', newSort);
                window.location.href = url.toString();
            });
        });
    }

    /**
     * Anima campo (evidenziazione)
     */
    animateField(field) {
        field.style.background = '#fff3cd';
        field.style.transition = 'background-color 0.3s ease';
        
        setTimeout(() => {
            field.style.background = '';
        }, 1000);
    }

    /**
     * Utility: Mostra notifica
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Utility: Format currency
     */
    formatCurrency(amount) {
        return new Intl.NumberFormat('it-IT', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount);
    }

    /**
     * Utility: Format phone number
     */
    formatPhoneNumber(phone) {
        // Formato italiano di base
        return phone.replace(/(\d{3})(\d{3})(\d{4})/, '$1 $2 $3');
    }
}

// Inizializzazione globale
document.addEventListener('DOMContentLoaded', function() {
    // Inizializza solo se siamo in una pagina fornitori
    if (document.body.classList.contains('fornitori-page') || 
        window.location.pathname.includes('fornitori') ||
        document.querySelector('.fornitore-card') ||
        document.querySelector('#fornitori-form')) {
        
        window.fornitoriManager = new FornitoriManager();
    }
});

// Export per uso in altri moduli
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FornitoriManager;
}
