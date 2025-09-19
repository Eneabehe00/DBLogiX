

// ===== VARIABILI GLOBALI =====
let currentTickets = [];
let previewData = {};
let manualTickets = [];
let addedExistingTickets = []; // Nuova variabile per ticket esistenti aggiunti
let ticketDiscounts = {};
let selectedProducts = [];
let productSearchTimeout;
let existingProductsData = [];
let existingProductsFiltered = [];
let selectedTicketsIds = new Set();

// Carica dati dal server
let serverData, INITIAL_TICKETS_DATA, INITIAL_PREVIEW_DATA, FROM_TASK, CLIENTE_ID, EMPRESA_ID;

// ===== INIZIALIZZAZIONE =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DDT Preview inizializzato');
    
    // Carica dati dal server
    const serverDataElement = document.getElementById('server-data');
    if (serverDataElement) {
        serverData = JSON.parse(serverDataElement.textContent);
        INITIAL_TICKETS_DATA = serverData.INITIAL_TICKETS_DATA;
        INITIAL_PREVIEW_DATA = serverData.INITIAL_PREVIEW_DATA;
        FROM_TASK = serverData.FROM_TASK;
        CLIENTE_ID = serverData.CLIENTE_ID;
        EMPRESA_ID = serverData.EMPRESA_ID;
    }
    
    initializePreviewData();
    setupEventListeners();

    // 🔧 FIX: NON ripristinare automaticamente i prodotti selezionati dal localStorage
    // per evitare che rimangano visibili nella modale dopo la creazione di un ticket
    // I prodotti verranno gestiti solo dalla modale di creazione ticket stessa
    // restoreSelectedProductsFromStorage();

    updateFormData();
    
    // Aggiorna i dettagli prezzi per tutti i ticket caricati
    setTimeout(() => {
        updateAllTicketsPriceDetails();
        // 🔥 AGGIUNTO: Aggiorna anche i totali dopo il caricamento iniziale
        setTimeout(updateTotalsBar, 200);
    }, 500);
    
    // 🔄 SETUP SISTEMA DI REFRESH AUTOMATICO
    setupRefreshSystem();
    
    // ⚡ CONTROLLO FINALE DOPO INIZIALIZZAZIONE COMPLETA
    setTimeout(() => {
        console.log('⚡ Controllo finale prezzi dopo inizializzazione completa...');
        if (typeof window.DDTDebugUtils !== 'undefined' && typeof window.DDTDebugUtils.checkPrices === 'function') {
            window.DDTDebugUtils.checkPrices();
        } else if (typeof checkPriceConsistency === 'function') {
            checkPriceConsistency();
        } else {
            // Callback per quando la funzione sarà disponibile
            const checkWhenReady = () => {
                if (typeof checkPriceConsistency === 'function') {
                    console.log('⚡ Controllo prezzi - funzione finalmente disponibile');
                    checkPriceConsistency();
                } else {
                    setTimeout(checkWhenReady, 500);
                }
            };
            checkWhenReady();
        }
    }, 500);
    
    // Verifica pulsante fattura
    const invoiceButton = document.getElementById('create-invoice-only');
    if (invoiceButton) {
        console.log('✅ Pulsante "Genera solo fattura" trovato');
    } else {
        console.error('❌ Pulsante "Genera solo fattura" NON trovato!');
    }
});

// ===== GESTIONE DATI =====
function initializePreviewData() {
    const initialPreviewData = Array.isArray(INITIAL_PREVIEW_DATA) ? INITIAL_PREVIEW_DATA : [];
    console.log('🚀 Inizializzazione dati preview:', initialPreviewData.length, 'ticket');
    
    // Initialize currentTickets as empty array - we'll populate it with processed tickets
    currentTickets = [];
    
    for (let item of initialPreviewData) {
        if (item && item.ticket && item.ticket.IdTicket) {
            console.log('🔍 DEBUG COMPLETO: Processando ticket', item.ticket.IdTicket);
            console.log('🔍 DEBUG: Dati item completi:', item);
            console.log('🔍 DEBUG: Linee raw:', item.lines);
            
            // Elabora le linee preservando SEMPRE gli ID reali quando disponibili
            const processedLines = Array.isArray(item.lines) ? item.lines.map(line => {
                console.log('🔍 DEBUG: Processando linea:', line);
                console.log('🔍 DEBUG: ID linea trovato:', line.id_linea_ticket);
                
                // IMPORTANTE: Preserva SEMPRE l'ID reale se presente
                let lineId = line.id_linea_ticket;
                if (!lineId) {
                    console.error('❌ ERRORE CRITICO: Linea senza ID reale per ticket', item.ticket.IdTicket);
                    console.error('❌ Dati linea:', line);
                    console.error('❌ Questa linea NON POTRÀ essere modificata');
                    // NON generare ID casuali per ticket iniziali - devono avere ID reali
                    return null;
                }
                
                let lineData = {
                    ...line,
                    id_linea_ticket: lineId,  // SOLO ID reali per ticket iniziali
                    descripcion: line.descripcion || 'Prodotto',
                    peso: line.peso || 0,
                    precio: line.precio || 0,
                    importe: line.importe || (line.peso * line.precio),
                    // 🔥 NUOVO: Lettura campo ImporteSinIVASinDtoL dal database
                    ImporteSinIVASinDtoL: line.ImporteSinIVASinDtoL || line.importe_sin_iva_sin_dto_l || line.importe,
                    comportamiento: line.comportamiento || 0
                };

                // 🔥 APPLICA LISTINO DEDICATO se disponibile
                if (window.hasDedicatedListino) {
                    lineData = applyDedicatedListinoToLine(lineData, item.ticket.IdTicket);
                }

                console.log(`💰 Lettura ImporteSinIVASinDtoL per linea ${lineId}:`, lineData.ImporteSinIVASinDtoL);
                
                console.log('✅ Linea con ID reale caricata:', lineId, 'per ticket', item.ticket.IdTicket);
                console.log('✅ Dati linea processati:', lineData);
                return lineData;
            }).filter(Boolean) : [];

            previewData[item.ticket.IdTicket] = {
                ticket: item.ticket,
                lines: processedLines,
                total: parseFloat(item.ticket_total) || 0
            };
            
            // ✅ IMPORTANTE: Aggiungi il ticket ID all'array currentTickets
            currentTickets.push(item.ticket.IdTicket);
            
            console.log('✅ Ticket iniziale', item.ticket.IdTicket, 'caricato con', processedLines.length, 'linee con ID reali');
            console.log('✅ Ticket aggiunto a currentTickets:', item.ticket.IdTicket);
        }
    }
    
    // Carica i dati dal localStorage
    loadManualTicketsFromStorage();
    loadAddedExistingTicketsFromStorage();
    loadTicketDiscountsFromStorage();
    
    // 🔄 CARICA E APPLICA LE MODIFICHE PERSISTENTI
    loadTicketModificationsFromStorage();
    
    // Pulizia periodica delle modifiche scadute
    clearExpiredModifications();
    
    // ⚡ CONTROLLO IMMEDIATO DEI PREZZI DOPO INIZIALIZZAZIONE
    setTimeout(() => {
        console.log('⚡ Controllo immediato prezzi al caricamento...');
        if (typeof checkPriceConsistency === 'function') {
            checkPriceConsistency();
        } else {
            console.warn('⚠️ Funzione checkPriceConsistency non ancora disponibile, riprovo tra 1 secondo...');
            setTimeout(() => {
                if (typeof checkPriceConsistency === 'function') {
                    checkPriceConsistency();
                }
            }, 1000);
        }
    }, 100);

    // 🔧 FIX: Assicurati che gli event listeners per gli sconti siano impostati dopo che tutti i ticket sono stati aggiunti
    setTimeout(() => {
        setupDiscountEventListeners();
        console.log('✅ Event listeners sconti impostati dopo inizializzazione dati');
    }, 200);
}

// ===== SETUP EVENT LISTENERS =====
function setupEventListeners() {
    console.log('🔗 Setup event listeners...');
    
    // Pulsante crea ticket manuale
    const btnCreateManualTicket = document.getElementById('btn-create-manual-ticket');
    if (btnCreateManualTicket) {
        btnCreateManualTicket.addEventListener('click', function() {
            console.log('🎫 Apertura modale crea ticket manuale');
            openCreateTicketModal();
        });
    }
    
    // Pulsante genera solo fattura
    const createInvoiceButton = document.getElementById('create-invoice-only');
    if (createInvoiceButton) {
        createInvoiceButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('💰 Generazione solo fattura');
            handleCreateInvoiceOnly();
        });
    }
    
    // Event listeners per modifica ticket
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-ticket-btn')) {
            const button = e.target.closest('.edit-ticket-btn');
            const ticketId = button.getAttribute('data-ticket-id');
            console.log('✏️ Modifica ticket:', ticketId);
            openTicketEditModal(ticketId);
        }
        
        if (e.target.closest('.edit-line-btn')) {
            const button = e.target.closest('.edit-line-btn');
            const ticketId = button.getAttribute('data-ticket-id');
            const lineId = button.getAttribute('data-line-id');
            console.log('📝 Modifica linea:', ticketId, lineId);
            openEditLineModal(ticketId, lineId);
        }
        
        if (e.target.closest('.btn-remove-ticket')) {
            const button = e.target.closest('.btn-remove-ticket');
            const ticketId = parseInt(button.getAttribute('data-ticket-id'));
            console.log('🗑️ Rimozione ticket:', ticketId);
            removeTicket(ticketId);
        }
    });
    
    // Event listeners rimossi per righe cliccabili - ora solo pulsanti
    
    // Event listeners per sconti
    setupDiscountEventListeners();

    // Form submission
    const finalForm = document.getElementById('final-ddt-form');
    if (finalForm) {
        finalForm.addEventListener('submit', function(e) {
            updateFormData();
            
            const totalTickets = currentTickets.length + manualTickets.length;
            
            if (totalTickets === 0) {
                e.preventDefault();
                showNotification('Devi selezionare almeno un ticket per creare il DDT.', 'warning');
                return false;
            }
            
            if (!confirm(`Sei sicuro di voler creare il DDT con ${totalTickets} ticket selezionati?`)) {
                e.preventDefault();
                return false;
            }
            
            // Pulisci localStorage dopo conferma
            localStorage.removeItem('ddt_ticket_modifications');
            localStorage.removeItem('ddt_manual_tickets');
            localStorage.removeItem('ddt_added_existing_tickets');
            localStorage.removeItem('ddt_ticket_discounts');
            localStorage.removeItem('ddt_selected_tickets_temp'); // Clear ticket selection from select_tickets page
            
            // Mostra loading
            const btn = document.getElementById('create-final-ddt');
            if (btn) {
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generazione in corso...';
                btn.disabled = true;
            }
        });
    }
    
    // Event listener per aggiornamenti dati ticket da modale
    document.addEventListener('ticketDataChanged', function(event) {
        const { ticketId } = event.detail;
        console.log('🔄 Dati ticket modificati dal modale, aggiorno tabella:', ticketId);

        // Aggiorna tutti i dettagli prezzi e quantità per il ticket modificato
        setTimeout(() => {
            updateTicketPriceDetails(ticketId);
        }, 100);
    });

    // Event listener per pulizia localStorage quando si lascia la pagina
    window.addEventListener('beforeunload', function(e) {
        console.log('🔄 Pulizia localStorage prima di lasciare la pagina ddt/preview');
        clearAllDDTLocalStorage();
    });
}

// ===== PULIZIA LOCALSTORAGE =====
function clearAllDDTLocalStorage() {
    console.log('🧹 Pulizia completa di tutti i localStorage DDT...');

    try {
        // Rimuovi tutti i localStorage specifici del DDT
        const keysToRemove = [
            'ddt_ticket_modifications',
            'ddt_manual_tickets',
            'ddt_added_existing_tickets',
            'ddt_ticket_discounts',
            'ddt_selected_tickets_temp',
            'ddt_recent_products',
            'ddt_selected_products'
        ];

        keysToRemove.forEach(key => {
            localStorage.removeItem(key);
        });

        // Rimuovi anche eventuali modifiche specifiche per DDT (pattern: ddt_modifications_*)
        for (let i = localStorage.length - 1; i >= 0; i--) {
            const key = localStorage.key(i);
            if (key && key.startsWith('ddt_modifications_')) {
                localStorage.removeItem(key);
                console.log('🗑️ Rimosso:', key);
            }
        }

        console.log('✅ Tutti i localStorage DDT sono stati puliti');
    } catch (error) {
        console.error('❌ Errore durante la pulizia del localStorage:', error);
    }
}

function setupDiscountEventListeners() {
    // Event listener per i campi input degli sconti
    document.querySelectorAll('.discount-input-field').forEach(input => {
        input.addEventListener('input', function() {
            const ticketId = this.getAttribute('data-ticket-id');
            updateTicketDiscountFromInput(ticketId, this.value);
        });

        input.addEventListener('blur', function() {
            const ticketId = this.getAttribute('data-ticket-id');
            updateTicketDiscountFromInput(ticketId, this.value);
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur(); // Perdere il focus per applicare lo sconto
            }
        });
    });

    // Event listener per i pulsanti "Rimuovi" sconto
    document.querySelectorAll('.btn-remove-discount').forEach(btn => {
        btn.addEventListener('click', function() {
            const ticketId = this.closest('.discount-container').getAttribute('data-ticket-id');
            removeTicketDiscount(ticketId);
        });
    });
}

// ===== GESTIONE LOCALSTORAGE =====
function loadManualTicketsFromStorage() {
    const stored = localStorage.getItem('ddt_manual_tickets');
    console.log('🔄 Caricamento ticket manuali dal localStorage:', stored);
    
    if (stored) {
        try {
            manualTickets = JSON.parse(stored);
            console.log('📦 Ticket manuali trovati nel storage:', manualTickets.length);
            
            manualTickets.forEach(ticket => {
                console.log('🎫 Ripristinando ticket manuale:', ticket.id_ticket);
                addManualTicketToPreview(ticket);
            });
        } catch (e) {
            console.error('❌ Errore nel caricamento ticket manuali:', e);
            manualTickets = [];
        }
    } else {
        console.log('ℹ️ Nessun ticket manuale trovato nel localStorage');
    }
}

// ===== GESTIONE MODIFICHE PERSISTENTI =====
function loadTicketModificationsFromStorage() {
    console.log('🔄 Caricamento modifiche ticket dal localStorage...');
    
    const stored = localStorage.getItem('ddt_ticket_modifications');
    if (!stored) {
        console.log('ℹ️ Nessuna modifica persistente trovata');
        return;
    }
    
    try {
        const modifications = JSON.parse(stored);
        console.log('📦 Modifiche trovate nel storage:', Object.keys(modifications).length);
        
        // Filtra le modifiche per scadenza (mantieni solo quelle degli ultimi 24 ore)
        const now = Date.now();
        const maxAge = 24 * 60 * 60 * 1000; // 24 ore in millisecondi
        
        const validModifications = {};
        let expiredCount = 0;
        
        Object.keys(modifications).forEach(key => {
            const modification = modifications[key];
            if (modification.timestamp && (now - modification.timestamp) < maxAge) {
                validModifications[key] = modification;
            } else {
                expiredCount++;
            }
        });
        
        if (expiredCount > 0) {
            console.log(`🧹 Rimosse ${expiredCount} modifiche scadute`);
            localStorage.setItem('ddt_ticket_modifications', JSON.stringify(validModifications));
        }
        
        // Applica le modifiche valide ai dati del preview
        Object.keys(validModifications).forEach(key => {
            const modification = validModifications[key];
            applyModificationToPreviewData(modification);
        });
        
        console.log(`✅ Applicate ${Object.keys(validModifications).length} modifiche persistenti`);
        
    } catch (e) {
        console.error('❌ Errore nel caricamento modifiche persistenti:', e);
        localStorage.removeItem('ddt_ticket_modifications');
    }
}

function saveTicketModificationToStorage(ticketId, lineId, field, value, originalValue) {
    console.log('💾 Salvataggio modifica persistente:', {ticketId, lineId, field, value});
    
    try {
        // Carica le modifiche esistenti
        const stored = localStorage.getItem('ddt_ticket_modifications') || '{}';
        const modifications = JSON.parse(stored);
        
        // Crea una chiave univoca per questa modifica
        const modificationKey = `${ticketId}_${lineId}_${field}`;
        
        // Salva la modifica con timestamp
        modifications[modificationKey] = {
            ticketId: ticketId,
            lineId: lineId,
            field: field,
            value: value,
            originalValue: originalValue,
            timestamp: Date.now(),
            applied: false
        };
        
        // Salva nel localStorage
        localStorage.setItem('ddt_ticket_modifications', JSON.stringify(modifications));
        console.log(`✅ Modifica salvata: ${modificationKey}`);
        
    } catch (e) {
        console.error('❌ Errore nel salvataggio modifica persistente:', e);
    }
}

function applyModificationToPreviewData(modification) {
    console.log('🔧 Applicando modifica ai dati preview:', modification);
    
    const {ticketId, lineId, field, value} = modification;
    
    // Verifica che il ticket esista nei dati preview
    if (!previewData[ticketId]) {
        console.warn(`⚠️ Ticket ${ticketId} non trovato nei dati preview, saltando modifica`);
        return false;
    }
    
    const ticketData = previewData[ticketId];
    
    // Trova la linea specifica
    if (ticketData.lines && Array.isArray(ticketData.lines)) {
        const lineIndex = ticketData.lines.findIndex(line => line.id_linea_ticket == lineId);
        if (lineIndex !== -1) {
            const line = ticketData.lines[lineIndex];
            
            // Applica la modifica in base al tipo di campo
            switch (field) {
                case 'peso_quantita':
                    line.peso = parseFloat(value) || 0;
                    break;
                case 'prezzo_unitario':
                    // ✅ MODIFICA: Il prezzo rimane CON IVA (nessun calcolo inverso)
                    line.precio = parseFloat(value) || 0;

                    console.log(`💰 Prezzo modificato: ${line.precio}€ (con IVA - nessun calcolo inverso)`);
                    break;
                case 'prezzo_totale':
                    line.importe = parseFloat(value) || 0;
                    break;
                case 'descrizione':
                    line.descripcion = value || '';
                    break;
                case 'data_scadenza':
                    line.fecha_caducidad = value;
                    break;
                default:
                    console.warn(`⚠️ Campo non riconosciuto: ${field}`);
                    return false;
            }
            
            // Ricalcola il totale della linea se necessario
            if (field === 'peso_quantita' || field === 'prezzo_unitario') {
                // Usa il prezzo SENZA IVA per calcolare l'importo
                const priceToUse = line.precio_senza_iva || line.precio;
                line.importe = line.peso * priceToUse;
            }
            
            // Ricalcola il totale del ticket
            ticketData.total = ticketData.lines.reduce((sum, l) => sum + (parseFloat(l.importe) || 0), 0);
            ticketData.ticket_total = ticketData.total;
            
            console.log(`✅ Modifica applicata alla linea ${lineId} del ticket ${ticketId}`);
            return true;
        }
    }
    
    console.warn(`⚠️ Linea ${lineId} non trovata nel ticket ${ticketId}`);
    return false;
}

function clearExpiredModifications() {
    console.log('🧹 Pulizia modifiche scadute...');
    
    try {
        const stored = localStorage.getItem('ddt_ticket_modifications');
        if (!stored) return;
        
        const modifications = JSON.parse(stored);
        const now = Date.now();
        const maxAge = 24 * 60 * 60 * 1000; // 24 ore
        
        const validModifications = {};
        let removedCount = 0;
        
        Object.keys(modifications).forEach(key => {
            const modification = modifications[key];
            if (modification.timestamp && (now - modification.timestamp) < maxAge) {
                validModifications[key] = modification;
            } else {
                removedCount++;
            }
        });
        
        if (removedCount > 0) {
            localStorage.setItem('ddt_ticket_modifications', JSON.stringify(validModifications));
            console.log(`🗑️ Rimosse ${removedCount} modifiche scadute`);
        }
        
    } catch (e) {
        console.error('❌ Errore nella pulizia modifiche scadute:', e);
    }
}

function markModificationAsApplied(ticketId, lineId, field) {
    try {
        const stored = localStorage.getItem('ddt_ticket_modifications');
        if (!stored) return;
        
        const modifications = JSON.parse(stored);
        const modificationKey = `${ticketId}_${lineId}_${field}`;
        
        if (modifications[modificationKey]) {
            modifications[modificationKey].applied = true;
            localStorage.setItem('ddt_ticket_modifications', JSON.stringify(modifications));
            console.log(`✅ Modifica marcata come applicata: ${modificationKey}`);
        }
    } catch (e) {
        console.error('❌ Errore nel marcare modifica come applicata:', e);
    }
}

function saveManualTicketsToStorage() {
    console.log('💾 Salvataggio ticket manuali nel localStorage:', manualTickets.length, 'ticket');
    localStorage.setItem('ddt_manual_tickets', JSON.stringify(manualTickets));
}

// ===== GESTIONE PRODOTTI RECENTI =====
function loadRecentProductsFromStorage() {
    const stored = localStorage.getItem('ddt_recent_products');
    if (stored) {
        try {
            return JSON.parse(stored);
        } catch (e) {
            console.error('❌ Errore nel caricamento prodotti recenti:', e);
            return [];
        }
    }
    return [];
}

function saveRecentProductsToStorage(products) {
    console.log('💾 Salvataggio prodotti recenti nel localStorage');
    localStorage.setItem('ddt_recent_products', JSON.stringify(products));
}

function addProductToRecentList(product) {
    console.log('📝 Aggiunta prodotto alla lista recenti:', product.descripcion);
    
    let recentProducts = loadRecentProductsFromStorage();
    
    // Rimuovi il prodotto se già presente (per evitare duplicati)
    recentProducts = recentProducts.filter(p => p.id !== product.id);
    
    // Aggiungi il prodotto all'inizio della lista
    const recentProduct = {
        id: product.id,
        descripcion: product.descripcion,
        precio: product.precio,
        iva: product.iva,
        comportamiento: product.comportamiento,
        ean: product.ean || '',
        addedAt: new Date().toISOString()
    };
    
    recentProducts.unshift(recentProduct);
    
    // Mantieni solo gli ultimi 3 prodotti
    recentProducts = recentProducts.slice(0, 3);
    
    saveRecentProductsToStorage(recentProducts);
    
    return recentProducts;
}

function displayRecentProducts() {
    console.log('🔄 Visualizzazione prodotti recenti nel modale');
    
    const recentProducts = loadRecentProductsFromStorage();
    const recentSection = document.getElementById('recent-products-section');
    const recentList = document.getElementById('recent-products-list');
    
    if (!recentSection || !recentList) {
        console.warn('⚠️ Elementi per prodotti recenti non trovati');
        return;
    }
    
    if (recentProducts.length === 0) {
        recentSection.style.display = 'none';
        return;
    }
    
    // Mostra la sezione
    recentSection.style.display = 'block';
    
    // Popola la lista
    let html = '';
    recentProducts.forEach(product => {
        html += `
            <div class="col-md-4 mb-2">
                <div class="card border-primary h-100 product-suggestion-card" 
                     style="cursor: pointer; transition: all 0.3s ease;" 
                     data-product-id="${product.id}"
                     onclick="addRecentProductToTicket(${product.id})">
                    <div class="card-body p-2 text-center">
                        <div class="d-flex justify-content-between align-items-start mb-1">
                            <small class="text-muted">#${product.id}</small>
                            <i class="fas fa-plus-circle text-primary"></i>
                        </div>
                        <h6 class="card-title mb-1 text-truncate" style="font-size: 0.85rem;" title="${product.descripcion}">
                            ${product.descripcion}
                        </h6>
                        <div class="text-success fw-bold" style="font-size: 0.9rem;">
                            €${parseFloat(product.precio).toFixed(2)}
                        </div>
                        <small class="text-muted">${product.comportamiento == 1 ? 'Al peso' : 'A pezzo'}</small>
                    </div>
                </div>
            </div>
        `;
    });
    
    recentList.innerHTML = html;
    
    // Aggiungi effetti hover
    document.querySelectorAll('.product-suggestion-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 12px rgba(0,123,255,0.3)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
}

function addRecentProductToTicket(productId) {
    console.log('🎯 Aggiunta prodotto recente al ticket:', productId);
    
    const recentProducts = loadRecentProductsFromStorage();
    const product = recentProducts.find(p => p.id === productId);
    
    if (!product) {
        console.error('❌ Prodotto recente non trovato:', productId);
        showNotification('Prodotto non trovato', 'error');
        return;
    }
    
    // Usa la funzione esistente per aggiungere il prodotto
    addProductToTicket(product);
    
    // Aggiorna la visualizzazione dei suggerimenti (il prodotto si sposterà in cima)
    const updatedRecentProducts = addProductToRecentList(product);
    displayRecentProducts();
}

function loadTicketDiscountsFromStorage() {
    const stored = localStorage.getItem('ddt_ticket_discounts');
    if (stored) {
        try {
            ticketDiscounts = JSON.parse(stored);
            Object.keys(ticketDiscounts).forEach(ticketId => {
                const discountValue = ticketDiscounts[ticketId];
                const container = document.querySelector(`.discount-container[data-ticket-id="${ticketId}"]`);
                const inputField = container ? container.querySelector('.discount-input-field') : null;

                if (inputField) {
                    // Imposta il valore del campo input
                    inputField.value = discountValue;

                    // Aggiorna gli stili del campo in base allo sconto
                    if (discountValue > 0) {
                        inputField.classList.add('has-discount');
                    } else {
                        inputField.classList.remove('has-discount');
                    }

                    updateTicketTotalDisplay(ticketId, discountValue);
                    updateDiscountInputDisplay(ticketId, discountValue);
                }
            });

            // Reinizializza gli event listener dopo aver caricato gli sconti
            setupDiscountEventListeners();
        } catch (e) {
            console.error('Errore nel caricamento sconti ticket:', e);
            ticketDiscounts = {};
        }
    }
}

function saveTicketDiscountsToStorage() {
    localStorage.setItem('ddt_ticket_discounts', JSON.stringify(ticketDiscounts));
}

// ===== GESTIONE TICKET ESISTENTI AGGIUNTI =====
function loadAddedExistingTicketsFromStorage() {
    const stored = localStorage.getItem('ddt_added_existing_tickets');
    console.log('🔄 Caricamento ticket esistenti dal localStorage:', stored);
    
    if (stored) {
        try {
            addedExistingTickets = JSON.parse(stored);
            console.log('📦 Ticket esistenti trovati nel storage:', addedExistingTickets.length);
            
            addedExistingTickets.forEach(ticket => {
                console.log('🎫 Ripristinando ticket esistente:', ticket.id_ticket);
                addExistingTicketToPreview(ticket);
            });
        } catch (e) {
            console.error('❌ Errore nel caricamento ticket esistenti aggiunti:', e);
            addedExistingTickets = [];
        }
    } else {
        console.log('ℹ️ Nessun ticket esistente trovato nel localStorage');
    }
}

function saveAddedExistingTicketsToStorage() {
    console.log('💾 Salvataggio ticket esistenti nel localStorage:', addedExistingTickets.length, 'ticket');
    localStorage.setItem('ddt_added_existing_tickets', JSON.stringify(addedExistingTickets));
}

function addExistingTicketToPreview(ticketData) {
    // Verifica che il ticket non sia già presente
    const ticketId = ticketData.id_ticket;
    console.log('🔍 Processando ticket esistente:', ticketId);
    
    // Controlla se esiste già in currentTickets
    const existsInCurrentTickets = currentTickets.includes(ticketId);
    console.log('📋 Ticket già in currentTickets?', existsInCurrentTickets);
    
    if (!existsInCurrentTickets) {
        currentTickets.push(ticketId);
        console.log('➕ Aggiunto a currentTickets:', ticketId);
    }
    
    // Assicurati che le linee abbiano tutte le proprietà necessarie
    // IMPORTANTE: SOLO ID reali - non generare mai ID casuali
    const enhancedLines = Array.isArray(ticketData.lines) ? ticketData.lines.map(line => {
        let lineId = line.id_linea_ticket;
        if (!lineId) {
            console.error('❌ ATTENZIONE: Linea del ticket ripristinato senza ID reale dal database:', line);
            console.error('❌ Ticket ID:', ticketId, 'Questa linea NON POTRÀ essere modificata');
            return null; // Rimuovi linee senza ID reale
        }
        return {
            ...line,
            id_linea_ticket: lineId, // USA SEMPRE l'ID reale dal database
            descripcion: line.descripcion || 'Prodotto',
            peso: line.peso || 0,
            precio: line.precio || 0,
            importe: line.importe || (line.peso * line.precio),
            comportamiento: line.comportamiento || 0
        };
    }).filter(Boolean) : [];
    
    // Aggiorna o aggiungi a previewData
    previewData[ticketId] = {
        ticket: ticketData.ticket_data,
        lines: enhancedLines,
        total: ticketData.ticket_data ? ticketData.ticket_data.importe_total : (ticketData.total || 0)
    };
    console.log('➕ Aggiornato previewData per ticket:', ticketId, 'con', enhancedLines.length, 'linee');
    
    // Controlla se la riga della tabella esiste già prima di aggiungerla
    const existingRow = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
    console.log('🔍 Riga tabella già esistente per ticket', ticketId, '?', !!existingRow);
    
    if (!existingRow) {
        console.log('🏗️ Aggiungendo ticket alla tabella:', ticketId);
        // Aggiorna la struttura dei dati per la tabella
        const tableData = {
            ...ticketData,
            lines: enhancedLines
        };
        addTicketToTable(tableData);
    } else {
        console.log('⚠️ Saltata aggiunta alla tabella - riga già esistente:', ticketId);
    }
    
    console.log('🔄 Ticket esistente ripristinato dal storage:', ticketId);
}

// ===== GESTIONE PREZZI DETTAGLIATI =====
function getIvaRate(idIva) {
    /**
     * Converte l'ID IVA in percentuale
     */
    switch (parseInt(idIva)) {
        case 0: return 0.00;  // 0% - Esente IVA
        case 1: return 0.04;  // 4%
        case 2: return 0.10;  // 10%
        case 3: return 0.22;  // 22%
        default: return 0.04; // Default 4%
    }
}

function calculatePriceDetails(line, ticketId = null) {
    /**
     * Calcola i dettagli di prezzo per una linea
     * @param {Object} line - Oggetto linea con peso, precio (CON IVA), precio_senza_iva, porcentaje_iva, comportamiento
     * @param {string} ticketId - ID del ticket per applicare listino dedicato
     * @returns {Object} Dettagli prezzi calcolati
     */
    const peso = parseFloat(line.peso) || 0;
    const comportamiento = parseInt(line.comportamiento) || 0;

    // 🔥 APPLICA LISTINO DEDICATO se disponibile
    if (ticketId && window.hasDedicatedListino) {
        line = applyDedicatedListinoToLine(line, ticketId);
    }
    
    // NUOVO: Il backend ora passa prezzi già calcolati
    let precioConIva, precioSinIva, ivaRate, ivaPercentage;
    
    // Controlla se è un ticket manuale per determinare come interpretare il prezzo
    const isFromManualTicket = line.is_manual || (line.id_linea_ticket && typeof line.id_linea_ticket === 'string');
    
    if (line.precio_senza_iva !== undefined && line.porcentaje_iva !== undefined) {
        // Usa i valori già calcolati dal backend - CORREZIONE: usa !== undefined invece di truthy check
        precioSinIva = parseFloat(line.precio_senza_iva) || 0;
        precioConIva = parseFloat(line.precio) || 0; // Ora precio è CON IVA
        ivaPercentage = parseInt(line.porcentaje_iva) || 4;
        ivaRate = ivaPercentage / 100;
        
        console.log(`💰 Usando prezzi dal backend - Articolo ${line.id_articulo}: €${precioConIva.toFixed(2)} (con IVA ${ivaPercentage}%), €${precioSinIva.toFixed(2)} (senza IVA)`);
    } else {
        // Gestisci diversi formati di IVA
        const precioUnitario = parseFloat(line.precio) || 0;
        
        ivaRate = 0.04; // Default 4%
        ivaPercentage = 4;
        
        if (line.porcentaje_iva) {
            ivaPercentage = parseInt(line.porcentaje_iva);
            ivaRate = ivaPercentage / 100;
        } else if (line.iva) {
            ivaPercentage = parseInt(line.iva);
            ivaRate = ivaPercentage / 100;
        } else {
            // CORREZIONE: Gestisce correttamente id_iva = 0 (IVA esente)
            let idIva = 1; // Default IVA 4%
            if (line.id_iva !== undefined && line.id_iva !== null) {
                idIva = line.id_iva;
            } else if (line.IdIVA !== undefined && line.IdIVA !== null) {
                idIva = line.IdIVA;
            } else if (line.iva !== undefined && line.iva !== null) {
                // Fallback: usa la percentuale IVA per determinare l'ID
                const ivaPercent = parseInt(line.iva);
                switch (ivaPercent) {
                    case 0: idIva = 0; break;
                    case 4: idIva = 1; break;
                    case 10: idIva = 2; break;
                    case 22: idIva = 3; break;
                    default: idIva = 1; break;
                }
            }
            
            ivaRate = getIvaRate(idIva);
            ivaPercentage = Math.round(ivaRate * 100);
            
            console.log(`🚨 DEBUG IVA: line.id_iva=${line.id_iva}, line.iva=${line.iva} → idIva=${idIva} → ivaRate=${ivaRate} → ${ivaPercentage}%`);
        }
        
        // ⚠️ IMPORTANTE: Distingui tra ticket manuali e ticket normali
        if (isFromManualTicket) {
            // Per ticket manuali: il prezzo inserito è già CON IVA
            console.log(`🎫 Ticket manuale - Il prezzo €${precioUnitario.toFixed(2)} è già CON IVA ${ivaPercentage}%`);
            precioConIva = precioUnitario;
            precioSinIva = ivaRate > 0 ? precioConIva / (1 + ivaRate) : precioConIva;
        } else {
            // Per ticket normali: il prezzo è senza IVA (fallback compatibilità)
            console.warn(`⚠️ Fallback calcolo IVA per articolo ${line.id_articulo || 'unknown'} - precio_senza_iva o porcentaje_iva mancanti`);
            precioSinIva = precioUnitario;
            precioConIva = precioSinIva * (1 + ivaRate);
        }
        
        console.log(`💰 Calcolato - €${precioSinIva.toFixed(2)} senza IVA → €${precioConIva.toFixed(2)} con IVA ${ivaPercentage}%`);
    }
    
    // 🔥 NUOVO SISTEMA: Usa ImporteSinIVASinDtoL dal database quando disponibile
    let totaleSinIva;

    if (line.ImporteSinIVASinDtoL !== undefined && line.ImporteSinIVASinDtoL !== null) {
        // Usa il valore dal database (campo ImporteSinIVASinDtoL)
        totaleSinIva = parseFloat(line.ImporteSinIVASinDtoL);
        console.log(`💰 Usando ImporteSinIVASinDtoL dal database: €${totaleSinIva.toFixed(2)} per linea ${line.id_linea_ticket}`);
    } else {
        // Fallback: calcola come prima
        totaleSinIva = peso * precioSinIva;
        console.log(`⚠️ Fallback calcolo ImporteSinIVASinDtoL: €${totaleSinIva.toFixed(2)} per linea ${line.id_linea_ticket}`);
    }

    // Totali usando i prezzi corretti
    const totaleConIva = peso * precioConIva;

    return {
        precioUnitario: precioSinIva,
        precioUnitarioConIva: precioConIva,
        totaleSinIva: totaleSinIva,
        totaleConIva: totaleConIva,
        ivaRate: ivaRate,
        ivaPercentage: ivaPercentage,
        comportamiento: comportamiento,
        unitIcon: comportamiento === 1 ? 'fas fa-weight' : 'fas fa-cubes',
        unitText: comportamiento === 1 ? 'kg' : 'pz'
    };
}

function updateTicketPriceDetails(ticketId) {
    /**
     * Aggiorna i dettagli di prezzo e quantità nella tabella per un ticket specifico
     */
    console.log('💰 Aggiornamento dettagli prezzi e quantità per ticket:', ticketId);
    
    const ticketRow = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
    if (!ticketRow || !previewData[ticketId]) {
        console.warn('❌ Riga ticket o dati non trovati:', ticketId);
        return;
    }
    
    const ticketData = previewData[ticketId];
    let totalTicketSinIva = 0;
    let totalTicketConIva = 0;
    let avgPrecioUnitario = 0;
    let mainComportamiento = 0;
    let totalPeso = 0;
    let totalQuantitaKg = 0;
    let totalQuantitaPz = 0;
    
    // Calcola i totali dalle linee
    if (ticketData.lines && Array.isArray(ticketData.lines)) {
        let totalPrezzoXPeso = 0;
        let totalPrezzoConIvaXPeso = 0; // Nuovo: per calcolare prezzo medio CON IVA
        
        ticketData.lines.forEach(line => {
            const details = calculatePriceDetails(line, ticketId);
            totalTicketSinIva += details.totaleSinIva;
            totalTicketConIva += details.totaleConIva;
            
            // Calcola prezzo medio ponderato (senza IVA per calcoli interni)
            const peso = parseFloat(line.peso) || 0;
            totalPrezzoXPeso += details.precioUnitario * peso;
            totalPrezzoConIvaXPeso += details.precioUnitarioConIva * peso; // Nuovo: prezzo CON IVA
            totalPeso += peso;
            
            // Accumula quantità per tipo
            if (details.comportamiento === 1) {
                totalQuantitaKg += peso;
                mainComportamiento = 1; // Priorità al peso
            } else {
                totalQuantitaPz += peso;
                if (mainComportamiento !== 1) mainComportamiento = 0;
            }
        });
        
        avgPrecioUnitario = totalPeso > 0 ? totalPrezzoXPeso / totalPeso : 0;
        const avgPrecioUnitarioConIva = totalPeso > 0 ? totalPrezzoConIvaXPeso / totalPeso : 0; // Nuovo
        
        // Usa il prezzo CON IVA per la visualizzazione
        avgPrecioUnitario = avgPrecioUnitarioConIva;
    }
    
    // Aggiorna i valori nella tabella
    const unitPriceSpan = ticketRow.querySelector('.unit-price-value');
    const unitIconSpan = ticketRow.querySelector('.unit-type-icon');
    const quantityValueSpan = ticketRow.querySelector('.quantity-value');
    const quantityUnitSpan = ticketRow.querySelector('.quantity-unit');
    const priceNoVatSpan = ticketRow.querySelector('.price-no-vat');
    const priceWithVatSpan = ticketRow.querySelector('.price-with-vat');
    
    if (unitPriceSpan) {
        unitPriceSpan.textContent = avgPrecioUnitario > 0 ? `€${avgPrecioUnitario.toFixed(2)}` : '--';
    }
    
    if (unitIconSpan) {
        const iconClass = mainComportamiento === 1 ? 'fas fa-weight' : 'fas fa-cubes';
        const title = mainComportamiento === 1 ? 'Prezzo per kg' : 'Prezzo per pezzo';
        unitIconSpan.innerHTML = `<i class="${iconClass}" title="${title}"></i>`;
    }
    
    // Aggiorna quantità
    if (quantityValueSpan && quantityUnitSpan) {
        if (totalQuantitaKg > 0 && totalQuantitaPz > 0) {
            // Ticket misto: mostra entrambi
            quantityValueSpan.textContent = `${totalQuantitaKg.toFixed(3)} + ${totalQuantitaPz.toFixed(0)}`;
            quantityUnitSpan.innerHTML = '<i class="fas fa-weight me-1" title="kg"></i><i class="fas fa-cubes" title="pz"></i>';
        } else if (totalQuantitaKg > 0) {
            // Solo peso
            quantityValueSpan.textContent = totalQuantitaKg.toFixed(3);
            quantityUnitSpan.innerHTML = '<i class="fas fa-weight text-primary" title="kg"></i>';
        } else if (totalQuantitaPz > 0) {
            // Solo pezzi
            quantityValueSpan.textContent = totalQuantitaPz.toFixed(0);
            quantityUnitSpan.innerHTML = '<i class="fas fa-cubes text-info" title="pz"></i>';
        } else {
            quantityValueSpan.textContent = '--';
            quantityUnitSpan.innerHTML = '';
        }
    }
    
    // Applica sconto se presente
    const currentDiscount = ticketDiscounts[ticketId] || 0;
    let finalTotalSinIva = totalTicketSinIva;
    let finalTotalConIva = totalTicketConIva;
    let finalAvgPrecioUnitario = avgPrecioUnitario;

    if (currentDiscount > 0) {
        finalTotalSinIva = totalTicketSinIva * (1 - currentDiscount / 100);
        finalTotalConIva = totalTicketConIva * (1 - currentDiscount / 100);
        finalAvgPrecioUnitario = avgPrecioUnitario * (1 - currentDiscount / 100);
    }

    // Mostra prezzo originale barrato + prezzo scontato, oppure solo prezzo normale
    if (priceNoVatSpan) {
        if (currentDiscount > 0 && totalTicketSinIva > 0) {
            const risparmio = totalTicketSinIva - finalTotalSinIva;
            priceNoVatSpan.innerHTML = `<span style="text-decoration: line-through; opacity: 0.6; font-size: 0.85em;">€${totalTicketSinIva.toFixed(2)}</span> <strong>€${finalTotalSinIva.toFixed(2)}</strong>`;
            priceNoVatSpan.title = `Risparmio: €${risparmio.toFixed(2)} (${currentDiscount}% sconto)`;
        } else {
            priceNoVatSpan.textContent = finalTotalSinIva > 0 ? `€${finalTotalSinIva.toFixed(2)}` : '--';
            priceNoVatSpan.title = '';
        }
    }
    
    if (priceWithVatSpan) {
        if (currentDiscount > 0 && totalTicketConIva > 0) {
            const risparmio = totalTicketConIva - finalTotalConIva;
            priceWithVatSpan.innerHTML = `<span style="text-decoration: line-through; opacity: 0.6; font-size: 0.85em;">€${totalTicketConIva.toFixed(2)}</span> <strong>€${finalTotalConIva.toFixed(2)}</strong>`;
            priceWithVatSpan.title = `Risparmio: €${risparmio.toFixed(2)} (${currentDiscount}% sconto)`;
        } else {
            priceWithVatSpan.textContent = finalTotalConIva > 0 ? `€${finalTotalConIva.toFixed(2)}` : '--';
            priceWithVatSpan.title = '';
        }
    }

    // Aggiorna anche il prezzo unitario con lo sconto applicato
    if (unitPriceSpan) {
        if (currentDiscount > 0 && avgPrecioUnitario > 0) {
            const risparmio = avgPrecioUnitario - finalAvgPrecioUnitario;
            unitPriceSpan.innerHTML = `<span style="text-decoration: line-through; opacity: 0.6; font-size: 0.85em;">€${avgPrecioUnitario.toFixed(2)}</span> <strong>€${finalAvgPrecioUnitario.toFixed(2)}</strong>`;
            unitPriceSpan.title = `Risparmio unitario: €${risparmio.toFixed(2)} (${currentDiscount}% sconto)`;
        } else {
            unitPriceSpan.textContent = finalAvgPrecioUnitario > 0 ? `€${finalAvgPrecioUnitario.toFixed(2)}` : '--';
            unitPriceSpan.title = '';
        }
    }
    
    const risparmioSinIva = currentDiscount > 0 ? totalTicketSinIva - finalTotalSinIva : 0;
    const risparmioConIva = currentDiscount > 0 ? totalTicketConIva - finalTotalConIva : 0;
    
    console.log('✅ Dettagli prezzi e quantità aggiornati per ticket', ticketId, {
        avgPrecioUnitarioOriginale: avgPrecioUnitario.toFixed(2),
        avgPrecioUnitarioFinale: finalAvgPrecioUnitario.toFixed(2),
        totalSinIvaOriginale: totalTicketSinIva.toFixed(2),
        totalSinIvaFinale: finalTotalSinIva.toFixed(2),
        totalConIvaOriginale: totalTicketConIva.toFixed(2),
        totalConIvaFinale: finalTotalConIva.toFixed(2),
        scontoApplicato: currentDiscount + '%',
        risparmioSinIva: risparmioSinIva.toFixed(2),
        risparmioConIva: risparmioConIva.toFixed(2),
        quantitaKg: totalQuantitaKg.toFixed(3),
        quantitaPz: totalQuantitaPz.toFixed(0),
        comportamiento: mainComportamiento
    });
}

function updateAllTicketsPriceDetails() {
    /**
     * Aggiorna i dettagli di prezzo per tutti i ticket visibili
     */
    console.log('🔄 Aggiornamento dettagli prezzi per tutti i ticket...');
    
    if (!previewData) {
        console.warn('❌ Dati preview non disponibili');
        return;
    }
    
    Object.keys(previewData).forEach(ticketId => {
        updateTicketPriceDetails(ticketId);
    });
    
    console.log('✅ Dettagli prezzi aggiornati per tutti i ticket');
}

// ===== GESTIONE RIEPILOGO =====
// Questa funzione è duplicata - verrà rimossa, quella principale è più sotto


// ===== GESTIONE FORM =====
function updateFormData() {
    // Convert currentTickets (array of IDs) to proper format expected by server
    const ticketsForServer = currentTickets.map(ticketId => ({
        id_ticket: ticketId,
        id_empresa: EMPRESA_ID || 1,
        id_tienda: 1,
        id_balanza_maestra: 1,
        id_balanza_esclava: -1,
        tipo_venta: 2
    }));

    document.getElementById('final-tickets-data').value = JSON.stringify(ticketsForServer);

    const form = document.getElementById('final-ddt-form');
    let manualTicketsInput = form.querySelector('input[name="manual_tickets"]');

    if (!manualTicketsInput) {
        manualTicketsInput = document.createElement('input');
        manualTicketsInput.type = 'hidden';
        manualTicketsInput.name = 'manual_tickets';
        form.appendChild(manualTicketsInput);
    }

    manualTicketsInput.value = JSON.stringify(manualTickets);

    let discountsInput = form.querySelector('input[name="ticket_discounts"]');

    if (!discountsInput) {
        discountsInput = document.createElement('input');
        discountsInput.type = 'hidden';
        discountsInput.name = 'ticket_discounts';
        form.appendChild(discountsInput);
    }

    discountsInput.value = JSON.stringify(ticketDiscounts);

    // 🔥 NUOVO: Aggiungi le modifiche del localStorage per dare priorità ai prezzi modificati
    let ticketModificationsInput = form.querySelector('input[name="ticket_modifications"]');

    if (!ticketModificationsInput) {
        ticketModificationsInput = document.createElement('input');
        ticketModificationsInput.type = 'hidden';
        ticketModificationsInput.name = 'ticket_modifications';
        form.appendChild(ticketModificationsInput);
    }

    // Carica le modifiche dal localStorage
    const storedModifications = localStorage.getItem('ddt_ticket_modifications') || '{}';
    ticketModificationsInput.value = storedModifications;

    console.log('📤 Modifiche ticket inviate al server:', storedModifications);
}

// ===== CORREZIONE EVENT LISTENERS =====
// Ho rimosso la seconda definizione duplicata di setupEventListeners()
// La funzione originale ora dovrebbe contenere tutti gli event listeners necessari

// ===== GESTIONE FATTURA =====
function handleInvoiceOnly(e) {
    e.preventDefault();
    console.log('🎯 Pulsante "Genera solo fattura" cliccato');
    
    if (currentTickets.length === 0 && manualTickets.length === 0) {
        showNotification('Nessun ticket selezionato per la fattura', 'warning');
        return;
    }
    
    if (!confirm('Sei sicuro di voler generare solo la fattura elettronica senza creare il DDT?')) {
        return;
    }
    
    const btn = document.getElementById('create-invoice-only');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generazione fattura...';
    btn.disabled = true;
    
    const formData = new FormData();
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;
    
    // Convert currentTickets (array of IDs) to proper format expected by server
    const ticketsForServer = currentTickets.map(ticketId => ({
        id_ticket: ticketId,
        id_empresa: EMPRESA_ID || 1,
        id_tienda: 1,
        id_balanza_maestra: 1,
        id_balanza_esclava: -1,
        tipo_venta: 2
    }));
    
    formData.append('csrf_token', csrfToken);
    formData.append('cliente_id', CLIENTE_ID);
    formData.append('id_empresa', EMPRESA_ID);
    formData.append('tickets', JSON.stringify(ticketsForServer));
    formData.append('manual_tickets', JSON.stringify(manualTickets));
    formData.append('ticket_discounts', JSON.stringify(ticketDiscounts));
    formData.append('note', document.getElementById('ddt-notes').value || '');
    formData.append('generate_invoice_only', 'true');
    
    fetch('/ddt/create_invoice_only', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification('Fattura elettronica generata con successo!', 'success');
            if (data.invoice_url) {
                window.location.href = data.invoice_url;
            }
        } else {
            showNotification('Errore nella generazione della fattura: ' + (data.error || 'Errore sconosciuto'), 'danger');
        }
    })
    .catch(error => {
        console.error('Errore fetch:', error);
        showNotification('Errore di rete durante la generazione della fattura: ' + error.message, 'danger');
    })
    .finally(() => {
        btn.innerHTML = '<i class="fas fa-file-invoice-dollar me-2"></i>Genera solo fattura';
        btn.disabled = false;
    });
}

// ===== GESTIONE CLICK TABELLA =====
function handleTableClicks(e) {
    // Click su riga espandibile
    if (e.target.closest('.clickable-row')) {
        const row = e.target.closest('.clickable-row');
        if (e.target.closest('button, select, input')) return;
        
        const ticketId = row.getAttribute('data-ticket-id');
        const detailsRow = document.querySelector(`.ticket-details-row[data-ticket-id="${ticketId}"]`);
        
        if (detailsRow) {
            detailsRow.style.display = detailsRow.style.display === 'none' ? 'table-row' : 'none';
        }
    }
    
    // Click su rimozione ticket
    if (e.target.closest('.btn-remove-ticket')) {
        const btn = e.target.closest('.btn-remove-ticket');
        const ticketId = parseInt(btn.getAttribute('data-ticket-id'));
        removeTicket(ticketId);
    }
    
    // Click su modifica ticket
    if (e.target.closest('.edit-ticket-btn')) {
        const btn = e.target.closest('.edit-ticket-btn');
        const ticketId = btn.getAttribute('data-ticket-id');
        openTicketEditModal(ticketId);
    }
    
    // Click su modifica linea
    if (e.target.closest('.edit-line-btn')) {
        const btn = e.target.closest('.edit-line-btn');
        const ticketId = btn.getAttribute('data-ticket-id');
        const lineId = btn.getAttribute('data-line-id');
        openEditLineModal(ticketId, lineId);
    }
}

// ===== UTILITY FUNCTIONS =====
function showNotification(message, type = 'info', duration = 5000) {
    const existing = document.querySelectorAll('.notification-toast');
    existing.forEach(el => el.remove());
    
    const notification = document.createElement('div');
    notification.className = 'notification-toast';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        max-width: 300px;
        background: ${type === 'success' ? '#28a745' : type === 'warning' ? '#ffc107' : type === 'danger' ? '#dc3545' : '#007bff'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        font-weight: 500;
        animation: slideIn 0.3s ease;
    `;
    notification.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: white; font-size: 18px; cursor: pointer; margin-left: 10px;">&times;</button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, duration);
    }
}

// ===== FUNZIONI PLACEHOLDER =====
// Queste funzioni sono definite per evitare errori, le implementazioni complete sono nel file originale

function addManualTicketToPreview(ticket) {
    // Aggiungi ai dati preview se non esiste già
    if (!previewData[ticket.id_ticket]) {
        previewData[ticket.id_ticket] = {
            ticket: ticket,
            lines: ticket.lines,
            total: ticket.total
        };
        
        // Aggiungi alla tabella visuale
        addTicketToTable(ticket);
        
        console.log('🔄 Ticket manuale ripristinato dal storage:', ticket.id_ticket);
    }
}

function removeTicket(ticketId) {
    if (confirm('Sei sicuro di voler rimuovere questo ticket dal DDT?')) {
        const isManual = ticketId < 0;
        
        if (isManual) {
            // Rimuovi ticket manuale
            manualTickets = manualTickets.filter(t => t.id_ticket !== ticketId);
            saveManualTicketsToStorage();
        } else {
            // Rimuovi ticket esistente aggiunto
            addedExistingTickets = addedExistingTickets.filter(t => t.id_ticket !== ticketId);
            saveAddedExistingTicketsToStorage();
            
            // Rimuovi dai ticket correnti
            currentTickets = currentTickets.filter(t => t !== ticketId);
        }
        
        // Rimuovi dai dati preview
        delete previewData[ticketId];
        
        // Rimuovi dalle righe della tabella
        const ticketRows = document.querySelectorAll(`[data-ticket-id="${ticketId}"]`);
        ticketRows.forEach(row => row.remove());

        // Aggiorna UI
        updateFormData();

        // Aggiorna la barra dei totali
        setTimeout(updateTotalsBar, 100);

        // Ricarica la lista dei ticket esistenti per includere quello appena rimosso (solo se la modale è aperta)
        if (!isManual && document.getElementById('existingTicketsModal').classList.contains('show')) {
            setTimeout(() => {
                loadExistingTickets();
            }, 100);
        }

        showNotification('Ticket rimosso con successo', 'success');
    }
}

function searchProducts(query) {
    const resultsContainer = document.getElementById('product-search-results');
    resultsContainer.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Ricerca...</div>';
    
    fetch(`/ddt/api_search_products?q=${encodeURIComponent(query)}&cliente_id=${CLIENTE_ID}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayProductResults(data.products);
        } else {
            resultsContainer.innerHTML = '<div class="text-danger">Errore nella ricerca</div>';
        }
    })
    .catch(error => {
        console.error('Errore:', error);
        resultsContainer.innerHTML = '<div class="text-danger">Errore di rete</div>';
    });
}

function displayProductResults(products) {
    console.log('📦 Display prodotti:', products.length);
    
    const resultsContainer = document.getElementById('product-search-results');
    if (!resultsContainer) return;
    
    if (products.length === 0) {
        resultsContainer.innerHTML = '<div class="text-muted text-center py-3"><i class="fas fa-search me-2"></i>Nessun prodotto trovato</div>';
        return;
    }
    
    let html = '';
    products.forEach(product => {
        html += `
            <div class="product-result-item mb-2 p-3 border rounded cursor-pointer"
                 onclick="addProductToTicketFromSearch(${product.id}, '${product.descripcion.replace(/'/g, '\\\'')}', ${product.precio}, ${product.iva_from_db || 0})"
                 style="cursor: pointer; transition: background-color 0.2s;"
                 onmouseover="this.style.backgroundColor='#f8f9fa'"
                 onmouseout="this.style.backgroundColor='white'">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1 fw-bold">${product.descripcion}</h6>
                        <small class="text-muted">ID: ${product.id} ${product.ean ? `| EAN: ${product.ean}` : ''}</small>
                    </div>
                    <div class="text-end">
                        <div class="fw-bold text-success">€ ${parseFloat(product.precio).toFixed(2)}</div>
                        <small class="text-muted">IVA DB: ${product.iva_from_db || 'N/A'}% | Ticket: ${product.iva}%</small>
                    </div>
                </div>
                <div class="mt-2">
                    <span class="badge bg-light text-dark">
                        ${product.comportamiento == 1 ? 'Vendita a peso (kg)' : 'Vendita a unità (pz)'}
                    </span>
                </div>
            </div>
        `;
    });
    
    resultsContainer.innerHTML = html;
}

function addProductToTicket(product) {
    console.log('➕ Aggiunta prodotto al ticket:', product);
    
    // Verifica se il prodotto è già stato aggiunto
    const existingIndex = selectedProducts.findIndex(p => p.id === product.id);
    if (existingIndex !== -1) {
        // Se esiste già, incrementa la quantità
        selectedProducts[existingIndex].peso += (product.comportamiento == 1 ? 0.1 : 1);
        showNotification(`Quantità di "${product.descripcion}" incrementata`, 'info');
    } else {
        // Aggiungi nuovo prodotto con valori di default
        // 🎯 IMPORTANTE: L'IVA è sempre quella di DEFAULT per ticket manuali, NON dal database
        const newProduct = {
            id: product.id,
            descripcion: product.descripcion,
            precio: parseFloat(product.precio) || 0,
            peso: product.comportamiento == 1 ? 0.1 : 1, // Default: 0.1kg o 1 pezzo
            iva: product.iva_from_db || 4, // Usa IVA dal database o 4% come fallback
            iva_from_db: product.iva_from_db || 0, // IVA originale dal database (solo per riferimento)
            comportamiento: product.comportamiento || 1, // Default: peso (kg)
            ean: product.ean || '',
            lotto: '' // Campo lotto vuoto per default
        };
        
        console.log(`➕ Prodotto aggiunto: ${product.descripcion} con IVA DEFAULT ${newProduct.iva}% (DB aveva ${newProduct.iva_from_db}%)`);
        
        selectedProducts.push(newProduct);

        // Salva nel localStorage
        saveSelectedProductsToStorage();

        showNotification(`"${product.descripcion}" aggiunto al ticket (IVA iniziale: 4%, modificabile)`, 'success');
    }

    // Aggiungi il prodotto alla lista dei recenti
    addProductToRecentList(product);

    updateSelectedProductsList();
}

function updateSelectedProductsList() {
    console.log('🔄 Aggiornamento lista prodotti selezionati');
    
    const listContainer = document.getElementById('selected-products-list');
    if (!listContainer) return;
    
    if (selectedProducts.length === 0) {
        listContainer.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-box-open fa-3x mb-3 opacity-50"></i>
                <p class="mb-0">Nessun prodotto selezionato</p>
                <small>Cerca e aggiungi prodotti dalla colonna di sinistra</small>
            </div>
        `;
        
        // Disabilita il pulsante salva
        const saveBtn = document.getElementById('save-manual-ticket');
        if (saveBtn) saveBtn.disabled = true;
        
        return;
    }
    
    let html = '';
    selectedProducts.forEach((product, index) => {
        html += `
            <div class="selected-product-item mb-3 p-3 border rounded" data-product-index="${index}">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h6 class="mb-1 fw-bold">${product.descripcion}</h6>
                        <small class="text-muted">ID: ${product.id}</small>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeSelectedProduct(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label small">Peso/Quantità</label>
                        <div class="input-group input-group-sm">
                            <input type="number" class="form-control" 
                                   value="${product.peso}" 
                                   step="0.001" min="0"
                                   onchange="updateSelectedProduct(${index}, 'peso', this.value)">
                            <span class="input-group-text">${product.comportamiento === 1 || product.comportamiento === undefined ? 'kg' : 'pz'}</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small">Prezzo unitario (con IVA)</label>
                        <div class="input-group input-group-sm">
                            <span class="input-group-text">€</span>
                            <input type="number" class="form-control" 
                                   value="${product.precio}" 
                                   step="0.01" min="0"
                                   onchange="updateSelectedProduct(${index}, 'precio', this.value)">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small">Aliquota IVA</label>
                        <select class="form-select form-select-sm" 
                                onchange="updateSelectedProduct(${index}, 'iva', this.value)">
                            <option value="0" ${product.iva == 0 ? 'selected' : ''}>🚫 0% - Esente</option>
                            <option value="4" ${product.iva == 4 ? 'selected' : ''}>🥬 4% - Alimentari Base</option>
                            <option value="10" ${product.iva == 10 ? 'selected' : ''}>🍕 10% - Alimentari</option>
                            <option value="22" ${product.iva == 22 ? 'selected' : ''}>🥤 22% - Bevande/Altri</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small">Totale (IVA ${product.iva}%)</label>
                        <div class="fw-bold text-success">
                            € ${(product.peso * product.precio).toFixed(2)}
                        </div>
                        ${product.iva_from_db !== undefined && product.iva_from_db !== product.iva ? 
                            `<small class="text-muted">DB aveva: ${product.iva_from_db}%</small>` : ''
                        }
                    </div>
                </div>
            </div>
        `;
    });
    
    listContainer.innerHTML = html;
    
    // Abilita il pulsante salva
    const saveBtn = document.getElementById('save-manual-ticket');
    if (saveBtn) saveBtn.disabled = false;
    
    // Aggiorna il totale del ticket
    updateTicketTotal();
}

function removeSelectedProduct(index) {
    if (confirm('Rimuovere questo prodotto dal ticket?')) {
        selectedProducts.splice(index, 1);
        updateSelectedProductsList();
    }
}

function updateSelectedProduct(index, field, value) {
    if (selectedProducts[index]) {
        if (field === 'iva') {
            // Per l'IVA, gestisci correttamente anche il caso 0% (esente IVA)
            const oldIva = selectedProducts[index][field];
            const newIva = parseInt(value);
            selectedProducts[index][field] = isNaN(newIva) ? 4 : newIva; // Se NaN usa 4%, altrimenti usa il valore (anche 0%)
            
            console.log(`🎯 IVA aggiornata per prodotto "${selectedProducts[index].descripcion}": ${oldIva}% → ${selectedProducts[index][field]}%`);
            
            // Mostra notifica di conferma del cambio IVA
            const ivaText = selectedProducts[index][field] === 0 ? "Esente IVA (0%)" : `${selectedProducts[index][field]}%`;
            showNotification(`IVA aggiornata a ${ivaText} per "${selectedProducts[index].descripcion}"`, 'success', 3000);
        } else {
            selectedProducts[index][field] = parseFloat(value) || 0;
        }
        updateSelectedProductsList();
    }
}

function updateTicketTotal() {
    console.log('🧮 Aggiornamento totale ticket');
    
    const totalProducts = selectedProducts.length;
    const totalWeight = selectedProducts.reduce((sum, p) => sum + (p.comportamiento == 1 ? p.peso : 0), 0);
    const totalPieces = selectedProducts.reduce((sum, p) => sum + (p.comportamiento == 0 ? p.peso : 0), 0);
    const totalAmount = selectedProducts.reduce((sum, p) => sum + (p.peso * p.precio), 0);
    
    // Aggiorna i display del totale se esistono
    const productsEl = document.getElementById('ticket-total-products');
    const weightEl = document.getElementById('ticket-total-weight');
    const piecesEl = document.getElementById('ticket-total-pieces');
    const amountEl = document.getElementById('ticket-total-amount');
    
    if (productsEl) productsEl.textContent = totalProducts;
    if (weightEl) weightEl.textContent = `${totalWeight.toFixed(3)} kg`;
    if (piecesEl) piecesEl.textContent = `${Math.round(totalPieces)} pz`;
    if (amountEl) amountEl.textContent = `€ ${totalAmount.toFixed(2)}`;
}

// Funzione loadExistingTickets() implementata più avanti nel file

function saveManualTicket() {
    console.log('🎫 Salvataggio ticket manuale - Prodotti selezionati:', selectedProducts.length);

    const btn = document.getElementById('save-manual-ticket');
    const originalHTML = btn.innerHTML;

    // Mostra loading
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creazione ticket...';
    btn.disabled = true;

    try {
        // Validazione: almeno un prodotto selezionato
        if (!selectedProducts || selectedProducts.length === 0) {
            showNotification('Seleziona almeno un prodotto per creare i ticket', 'warning');
            btn.innerHTML = originalHTML;
            btn.disabled = false;
            return;
        }

        // Crea un ticket separato per ciascun prodotto selezionato
        let createdTicketsCount = 0;
        const baseTimestamp = Date.now();

        selectedProducts.forEach((product, index) => {
            // Genera ID univoco negativo per ciascun ticket manuale
            // Usa baseTimestamp + index per garantire unicità
            const manualTicketId = -(baseTimestamp + index);
            console.log(`🎫 Creazione ticket manuale ${index + 1}/${selectedProducts.length} - ID:`, manualTicketId);

            const peso = parseFloat(product.peso) || 0;
            const precio = parseFloat(product.precio) || 0;
            const ivaValue = parseInt(product.iva) || 4;

            // Calcola importi con IVA per questo singolo prodotto
            let importe = 0;
            let importeConIVA = 0;

            if (peso > 0 && precio > 0) {
                // Per ticket manuali, il prezzo è sempre CON IVA
                importeConIVA = peso * precio;
                importe = importeConIVA / (1 + (ivaValue / 100));
            }

            // Crea la linea del ticket (solo una per ticket)
            const ticketLine = {
                id_linea_ticket: Math.random().toString(36).substr(2, 9), // ID univoco per la linea
                id_articulo: product.id,
                descripcion: product.descripcion || 'Prodotto',
                peso: peso,
                precio: precio, // Prezzo CON IVA
                precio_con_iva: precio, // Prezzo CON IVA
                importe: importe, // Senza IVA
                importe_con_iva: importeConIVA, // Con IVA
                comportamiento: product.comportamiento || 0,
                iva: ivaValue,
                id_iva: ivaValue === 0 ? 4 : (ivaValue === 4 ? 1 : (ivaValue === 10 ? 2 : (ivaValue === 22 ? 3 : 1))), // Mappa frontend a backend
                vat_rate: ivaValue / 100,
                porcentaje_iva: ivaValue,
                lotto: product.lotto || '' // Campo lotto se presente
            };

            // Crea oggetto ticket manuale (uno per prodotto)
        const manualTicket = {
            id_ticket: manualTicketId,
                num_ticket: `MANUAL-${manualTicketId.toString().replace('-', '')}`,
            fecha: new Date().toISOString().split('T')[0],
            fecha_formateada: new Date().toLocaleDateString('it-IT'),
            ticket_data: {
                IdTicket: manualTicketId,
                    NumTicket: `MANUAL-${manualTicketId.toString().replace('-', '')}`,
                fecha: new Date().toISOString().split('T')[0],
                fecha_formateada: new Date().toLocaleDateString('it-IT'),
                    importe_total: importeConIVA,
                    peso_total: peso,
                is_manual: true
            },
                lines: [ticketLine], // Solo una linea per ticket
                total: importeConIVA,
                ticket_total: importeConIVA,
            is_manual: true,
            id_empresa: EMPRESA_ID || 1
        };

            console.log(`🎫 Ticket manuale creato per "${product.descripcion}":`, manualTicket);

        // Aggiungi alla lista dei ticket manuali
        manualTickets.push(manualTicket);

        // Aggiungi ai dati preview
        previewData[manualTicketId] = {
            ticket: manualTicket.ticket_data,
                lines: [ticketLine],
                total: importeConIVA
        };

        // Aggiungi alla tabella visuale
        addManualTicketToTable(manualTicket);

            createdTicketsCount++;
        });

        // Salva nel localStorage
        saveManualTicketsToStorage();

        // Aggiorna riepilogo e form
        updateFormData();

        // Aggiorna la barra dei totali
        setTimeout(updateTotalsBar, 100);

        // Chiudi il modale e reset selezioni
        const modal = bootstrap.Modal.getInstance(document.getElementById('createTicketModal'));
        if (modal) {
            modal.hide();
            // Forza la rimozione del backdrop dopo un piccolo delay
            setTimeout(() => {
                forceRemoveModalBackdrop();
            }, 300);
        }

    // Reset prodotti selezionati per ticket futuri
    selectedProducts = [];
    clearSelectedProductsFromStorage(); // Pulisce il localStorage
    updateSelectedProductsList();

    // Forza l'aggiornamento dell'UI per mostrare stato vuoto
    const emptyState = document.getElementById('empty-products-state');
    const ticketSummary = document.getElementById('ticket-summary');
    const productsCountBadge = document.getElementById('products-count-badge');

    if (emptyState) emptyState.style.display = 'block';
    if (ticketSummary) ticketSummary.style.display = 'none';
    if (productsCountBadge) productsCountBadge.textContent = '0 prodotti';

    showNotification(`${createdTicketsCount} ticket manuale${createdTicketsCount === 1 ? '' : 'i'} creato${createdTicketsCount === 1 ? '' : 'i'} con successo!`, 'success');

        // Ripristina pulsante
        btn.innerHTML = originalHTML;
        btn.disabled = false;

    } catch (error) {
        console.error('❌ Errore nella creazione del ticket manuale:', error);
        showNotification('Errore nella creazione del ticket manuale', 'danger');

        // Ripristina pulsante
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

function selectAllTickets() {
    document.querySelectorAll('.ticket-checkbox').forEach(checkbox => {
        checkbox.checked = true;
    });
    updateSelectedTicketsCount();
}

function deselectAllTickets() {
    document.querySelectorAll('.ticket-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    updateSelectedTicketsCount();
}

function updateSelectedTicketsCount() {
    const selectedCheckboxes = document.querySelectorAll('.ticket-checkbox:checked');
    const count = selectedCheckboxes.length;
    
    const countElement = document.getElementById('selected-tickets-count');
    const addButton = document.getElementById('add-selected-tickets');
    
    // Aggiorna il testo del contatore con controllo di esistenza
    if (countElement) {
        if (count === 0) {
            countElement.innerHTML = '<i class="fas fa-info-circle me-1"></i>Nessun ticket selezionato';
        } else {
            countElement.innerHTML = `<i class="fas fa-check-circle me-1 text-success"></i>${count} ticket selezionato${count > 1 ? 'i' : ''}`;
        }
    }
    
    // Aggiorna lo stato del pulsante con controllo di esistenza
    if (addButton) {
        addButton.disabled = count === 0;
    }
    
    // Aggiorna il Set dei ticket selezionati
    selectedTicketsIds.clear();
    selectedCheckboxes.forEach(checkbox => {
        const ticketId = checkbox.getAttribute('data-ticket-id');
        if (ticketId) {
            selectedTicketsIds.add(ticketId);
        }
    });
    
    console.log('🔄 Ticket selezionati aggiornati:', selectedTicketsIds.size, 'di', count);
}

 function addSelectedTicketsToPreview() {
     console.log('📋 Aggiunta ticket selezionati:', selectedTicketsIds.size);
     
     if (selectedTicketsIds.size === 0) {
         showNotification('Seleziona almeno un ticket da aggiungere', 'warning');
         return;
     }
     
     // Verifica che i dati esistenti siano caricati
     if (!existingProductsData || existingProductsData.length === 0) {
         console.error('❌ Dati prodotti esistenti non caricati');
         showNotification('Errore: dati prodotti non disponibili. Riprova a caricare i ticket esistenti.', 'danger');
         return;
     }
     
     console.log('📊 Dati prodotti disponibili:', existingProductsData.length);
     
     // Raccogli i dati dei ticket selezionati
     const ticketsToAdd = [];
     selectedTicketsIds.forEach(ticketId => {
         console.log('🔍 Cercando ticket ID:', ticketId);
         
         // Trova il ticket nei dati esistenti
         let ticketFound = false;
         for (let product of existingProductsData) {
             const ticket = product.tickets.find(t => t.IdTicket.toString() === ticketId);
             if (ticket) {
                 console.log('✅ Ticket trovato:', ticket);
                 
                                 ticketsToAdd.push({
                    id_ticket: ticket.IdTicket,
                    id_empresa: ticket.id_empresa || EMPRESA_ID,
                    num_ticket: ticket.IdTicket,
                     fecha: ticket.fecha_formateada,
                     ticket_data: ticket,
                     lines: ticket.lines || [{
                         id_articulo: product.id_articulo,
                         descripcion: product.descripcion,
                         peso: ticket.peso_total,
                         // ✅ MANTIENI I CAMPI ORIGINALI DAL BACKEND
                         precio: ticket.peso_total > 0 ? parseFloat(ticket.importe_total || 0) / ticket.peso_total : 0,
                         precio_con_iva: ticket.peso_total > 0 ? parseFloat(ticket.importe_total || 0) / ticket.peso_total : 0,
                         importe: parseFloat(ticket.importe_total || 0),
                         importe_con_iva: parseFloat(ticket.importe_total || 0),
                         comportamiento: product.comportamiento || 0,
                         id_linea_ticket: Math.random().toString(36).substr(2, 9)
                     }]
                 });
                 ticketFound = true;
                 break;
             }
         }
         
         if (!ticketFound) {
             console.error('❌ Ticket non trovato nei dati esistenti:', ticketId);
         }
     });
     
     console.log('📦 Ticket da aggiungere:', ticketsToAdd.length);
     
     if (ticketsToAdd.length === 0) {
         showNotification('Nessun ticket valido trovato per l\'aggiunta', 'warning');
         return;
     }
     
         // Aggiungi i ticket al DDT
    ticketsToAdd.forEach(ticket => {
        // ✅ CORREZIONE: Controlla se il ticket è già presente per evitare duplicati
        if (currentTickets.includes(ticket.id_ticket)) {
            console.log('⚠️ Ticket già presente in currentTickets, skip:', ticket.id_ticket);
            return;
        }

        // Aggiungi ai ticket correnti
        currentTickets.push(ticket.id_ticket);
        
        // Assicurati che le linee abbiano tutte le proprietà necessarie
        // IMPORTANTE: SOLO ID reali - non generare mai ID casuali
        const enhancedLines = ticket.lines.map(line => {
            let lineId = line.id_linea_ticket;
            if (!lineId) {
                console.error('❌ ATTENZIONE: Linea senza ID reale dal database:', line);
                console.error('❌ Questo ticket NON POTRÀ essere modificato correttamente');
                return null; // Rimuovi linee senza ID reale
            }

            // ✅ PRESERVA TUTTI I CAMPI IVA ORIGINALI DAL BACKEND
            let lineData = {
                ...line, // Mantieni TUTTI i campi originali
                id_linea_ticket: lineId, // USA SEMPRE l'ID reale dal database
                // Assicurati che i campi IVA siano presenti (non sovrascriverli se esistono già)
                precio_con_iva: line.precio_con_iva || line.precio || 0,
                importe_con_iva: line.importe_con_iva || (line.peso * (line.precio_con_iva || line.precio || 0)) || 0,
                // 🔥 NUOVO: Lettura campo ImporteSinIVASinDtoL dal database
                ImporteSinIVASinDtoL: line.ImporteSinIVASinDtoL || line.importe_sin_iva_sin_dto_l || line.importe,
                // Mantieni gli altri campi originali
                descripcion: line.descripcion || 'Prodotto',
                peso: line.peso || 0,
                precio: line.precio || 0,
                importe: line.importe || 0,
                comportamiento: line.comportamiento || 0
            };

            // 🔥 APPLICA LISTINO DEDICATO se disponibile
            if (window.hasDedicatedListino) {
                lineData = applyDedicatedListinoToLine(lineData, ticket.id_ticket);
            }

            console.log(`💰 Lettura ImporteSinIVASinDtoL per linea esistente ${lineId}:`, lineData.ImporteSinIVASinDtoL);

            return lineData;
        }).filter(Boolean);
        
        // Aggiungi ai dati preview
        previewData[ticket.id_ticket] = {
            ticket: ticket.ticket_data,
            lines: enhancedLines,
            total: ticket.ticket_data.importe_total
        };
        
        // Prepara i dati nel formato corretto per la tabella
        const tableTicketData = {
            id_ticket: ticket.id_ticket,
            IdTicket: ticket.id_ticket,
            num_ticket: ticket.id_ticket,
            NumTicket: ticket.id_ticket,
            fecha: ticket.fecha,
            fecha_formateada: ticket.fecha,
            lines: enhancedLines, // Usa le linee arricchite
            total: ticket.ticket_data.importe_total,
            ticket_total: ticket.ticket_data.importe_total,
            importe_total: ticket.ticket_data.importe_total,
            is_manual: false,
            ticket_data: ticket.ticket_data,
            id_empresa: ticket.id_empresa
        };
        
        // Aggiungi alla lista dei ticket esistenti aggiunti per la persistenza (solo se non esiste già)
        if (!addedExistingTickets.find(t => t.id_ticket === ticket.id_ticket)) {
            addedExistingTickets.push(tableTicketData);
        }
        
        // Aggiungi alla tabella visuale
        addTicketToTable(tableTicketData);
        
        console.log('✅ Ticket esistente aggiunto con linee verificate:', ticket.id_ticket, enhancedLines.length, 'linee');
    });
     
     // Salva nel localStorage
     saveAddedExistingTicketsToStorage();
     
    // Aggiorna riepilogo e form
    updateFormData();

    // Aggiorna la barra dei totali
    setTimeout(updateTotalsBar, 100);

    // Ricarica la lista dei ticket esistenti per escludere quelli appena aggiunti (solo se la modale è aperta)
    if (document.getElementById('existingTicketsModal').classList.contains('show')) {
    setTimeout(() => {
        loadExistingTickets();
    }, 100);
    }
     
     showNotification(`${ticketsToAdd.length} ticket aggiunti al DDT con successo!`, 'success');
     
         // Chiudi la modale ticket esistenti e reset selezioni
    const modal = bootstrap.Modal.getInstance(document.getElementById('existingTicketsModal'));
    if (modal) {
        modal.hide();
        // Forza la rimozione del backdrop dopo un piccolo delay
        setTimeout(() => {
            forceRemoveModalBackdrop();
        }, 300);
    }
     
     // Reset selezioni
     selectedTicketsIds.clear();
     document.querySelectorAll('.ticket-checkbox:checked').forEach(cb => cb.checked = false);
     updateSelectedTicketsCount();
 }

function openTicketEditModal(ticketId) {
    const firstLineButton = document.querySelector(`button[data-ticket-id="${ticketId}"][data-bs-target="#editLineModal"]`);
    
    if (firstLineButton) {
        firstLineButton.click();
    } else {
        showNotification('Impossibile aprire il modale di modifica per questo ticket', 'error');
    }
}

function openEditLineModal(ticketId, lineId) {
    // Implementazione apertura modal modifica linea
    console.log('Apertura modal modifica linea:', ticketId, lineId);
}

function saveLineChanges() {
    // Implementazione salvataggio modifiche linea
    console.log('Salvataggio modifiche linea');
}

function updateTicketTotalDisplay(ticketId, discount) {
    const ticketData = previewData[ticketId];
    if (ticketData) {
        const originalTotal = ticketData.total;
        const discountedTotal = originalTotal * (1 - discount / 100);
        
        const badge = document.querySelector(`[data-ticket-id="${ticketId}"] .badge-amount`);
        if (badge) {
            if (discount > 0) {
                badge.innerHTML = `
                    <span style="text-decoration: line-through; font-size: 0.65rem;">€ ${originalTotal.toFixed(2)}</span><br>
                    € ${discountedTotal.toFixed(2)}
                `;
                badge.style.lineHeight = '1.1';
        } else {
                badge.innerHTML = `€ ${originalTotal.toFixed(2)}`;
                badge.style.lineHeight = '1.4';
            }
        }
    }
}

// ===== GESTIONE SCONTI =====

function updateTicketDiscountFromInput(ticketId, discount) {
    const discountValue = parseFloat(discount);
    const container = document.querySelector(`.discount-container[data-ticket-id="${ticketId}"]`);
    const input = container ? container.querySelector('.discount-input-field') : null;

    if (discount === '' || isNaN(discountValue) || discountValue < 0) {
        if (discount === '') {
            // 🔥 MODIFICATO: Usa applyDiscountToTicket invece di updateTicketDiscount
            applyDiscountToTicket(ticketId, 0);
        }
        return;
    }

    if (discountValue > 100) {
        if (input) {
            input.value = 100;
        }
        // 🔥 MODIFICATO: Usa applyDiscountToTicket invece di updateTicketDiscount
        applyDiscountToTicket(ticketId, 100);
    } else {
        // 🔥 MODIFICATO: Usa applyDiscountToTicket invece di updateTicketDiscount
        applyDiscountToTicket(ticketId, discountValue);
    }

    if (input) {
        input.style.borderColor = '#28a745';
        input.style.boxShadow = '0 0 0 3px rgba(40, 167, 69, 0.3)';

        setTimeout(() => {
            input.style.borderColor = '#007bff';
            input.style.boxShadow = '0 2px 4px rgba(0,123,255,0.2)';
        }, 1000);
    }
}

function updateTicketDiscount(ticketId, discount) {
    const discountValue = parseFloat(discount) || 0;
    ticketDiscounts[ticketId] = discountValue;
    saveTicketDiscountsToStorage();

    updateTicketTotalDisplay(ticketId, discountValue);
    updateDiscountInputDisplay(ticketId, discountValue);
}

// Nuova funzione per aggiornare la visualizzazione del campo input sconto
function updateDiscountInputDisplay(ticketId, discountValue) {
    const container = document.querySelector(`.discount-container[data-ticket-id="${ticketId}"]`);
    if (!container) return;

    const inputField = container.querySelector('.discount-input-field');
    const btnRemove = container.querySelector('.btn-remove-discount');

    if (inputField) {
        // Aggiorna il valore del campo input
        inputField.value = discountValue;

        // Aggiorna gli stili del campo in base allo sconto
        if (discountValue > 0) {
            inputField.classList.add('has-discount');
        } else {
            inputField.classList.remove('has-discount');
        }
    }

    // Mostra/nascondi pulsante rimuovi solo se c'è uno sconto applicato
    if (btnRemove) {
        if (discountValue > 0) {
            btnRemove.style.display = 'flex';
        } else {
            btnRemove.style.display = 'none';
        }
    }
}

// Nuova funzione per rimuovere lo sconto
function removeTicketDiscount(ticketId) {
    const container = document.querySelector(`.discount-container[data-ticket-id="${ticketId}"]`);
    if (!container) return;

    const inputField = container.querySelector('.discount-input-field');

    // Reset campo input a 0
    if (inputField) {
        inputField.value = '0';
        inputField.classList.remove('has-discount');
    }

    // Nascondi pulsante rimuovi
    const btnRemove = container.querySelector('.btn-remove-discount');
    if (btnRemove) {
        btnRemove.style.display = 'none';
    }

    // 🔥 MODIFICATO: Usa applyDiscountToTicket invece di updateTicketDiscount
    applyDiscountToTicket(ticketId, 0);
}

// ===== GESTIONE MODALI =====
function openCreateTicketModal() {
    console.log('🎫 Apertura modale crea ticket manuale');

    // Reset sempre i prodotti selezionati per un modale pulito
    // Forza il reset anche se ci sono dati nel localStorage
    selectedProducts = [];
    clearSelectedProductsFromStorage(); // Pulisce anche il localStorage per questo modale

    // Forza il reset della variabile globale per sicurezza
    window.selectedProductsBackup = null;

    // Reset dei campi se esistono
    const searchInput = document.getElementById('product-search');
    const dropdown = document.getElementById('product-search-dropdown');
    const emptyState = document.getElementById('empty-products-state');
    const ticketSummary = document.getElementById('ticket-summary');
    const productsCountBadge = document.getElementById('products-count-badge');
    const selectedProductsList = document.getElementById('selected-products-list');

    if (searchInput) searchInput.value = '';
    if (dropdown) dropdown.style.display = 'none';
    if (emptyState) emptyState.style.display = 'block';
    if (ticketSummary) ticketSummary.style.display = 'none';
    if (productsCountBadge) productsCountBadge.textContent = '0 prodotti';

    // Forza la pulizia della lista prodotti selezionati
    if (selectedProductsList) {
        selectedProductsList.innerHTML = `
            <div class="text-center text-muted py-5" id="empty-products-state">
                <div class="mb-4">
                    <i class="fas fa-box-open fa-4x opacity-25"></i>
                </div>
                <h5 class="text-muted mb-2">Nessun prodotto nel ticket</h5>
                <p class="mb-0">Cerca e seleziona i prodotti dalla barra di ricerca sopra</p>
                <small class="text-muted">
                    <i class="fas fa-lightbulb me-1"></i>
                    Suggerimento: Puoi cercare per nome, ID o codice a barre
                </small>
            </div>
        `;
    }

    // Aggiorna la visualizzazione per mostrare stato vuoto
    updateSelectedProductsList();
    
    // Mostra i prodotti recenti
    displayRecentProducts();
    
    // Setup ricerca prodotti se non già fatto
    setupProductSearch();
    
    // Setup event listener per salvataggio se non già fatto
    const saveBtn = document.getElementById('save-manual-ticket');
    if (saveBtn && !saveBtn.hasAttribute('data-listener-attached')) {
        saveBtn.setAttribute('data-listener-attached', 'true');
        saveBtn.addEventListener('click', saveManualTicket);
    }
    
    const modal = new bootstrap.Modal(document.getElementById('createTicketModal'));
    modal.show();
}

function setupProductSearch() {
    const searchInput = document.getElementById('product-search');
    const dropdown = document.getElementById('product-search-dropdown');
    
    if (searchInput && !searchInput.hasAttribute('data-listener-attached')) {
        searchInput.setAttribute('data-listener-attached', 'true');
        
        // Event listener per la ricerca
        searchInput.addEventListener('input', function() {
            clearTimeout(productSearchTimeout);
            const query = this.value.trim();
            
            if (query.length < 2) {
                if (dropdown) dropdown.style.display = 'none';
                return;
            }
            
            productSearchTimeout = setTimeout(() => {
                console.log('🔍 Ricerca prodotti per:', query);
                searchProducts(query);
            }, 300);
        });
        
        // Event listener per focus - mostra dropdown se ci sono risultati
        searchInput.addEventListener('focus', function() {
            if (this.value.trim().length >= 2 && dropdown && dropdown.innerHTML.trim()) {
                dropdown.style.display = 'block';
            }
        });
    }
    
    // Event listener globale per nascondere dropdown quando si clicca fuori
    document.addEventListener('click', function(e) {
        if (dropdown && !searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

function handleCreateInvoiceOnly() {
    console.log('💰 Gestione generazione solo fattura');

    // Verifica sia i ticket correnti che i dati preview esistenti
    const totalTickets = currentTickets.length + manualTickets.length + Object.keys(previewData).length;

    console.log('📊 Debug ticket counts:', {
        currentTickets: currentTickets.length,
        manualTickets: manualTickets.length,
        previewData: Object.keys(previewData).length,
        total: totalTickets
    });

    if (totalTickets === 0) {
        showNotification('Nessun ticket selezionato per la fattura', 'warning');
        return;
    }

    if (!confirm('Sei sicuro di voler generare solo la fattura elettronica senza creare il DDT?')) {
        return;
    }

    // Pulisci localStorage prima della generazione
    localStorage.removeItem('ddt_ticket_modifications');
    localStorage.removeItem('ddt_manual_tickets');
    localStorage.removeItem('ddt_added_existing_tickets');
    localStorage.removeItem('ddt_ticket_discounts');
    localStorage.removeItem('ddt_selected_tickets_temp');

    const btn = document.getElementById('create-invoice-only');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generazione fattura...';
    btn.disabled = true;
    
    setTimeout(() => {
        showNotification('Fattura elettronica generata con successo!', 'success');
        btn.innerHTML = '<i class="fas fa-file-invoice-dollar me-2"></i>Genera solo fattura';
        btn.disabled = false;
    }, 2000);
}




function updateFormData() {
    const finalTicketsInput = document.getElementById('final-tickets-data');
    if (finalTicketsInput) {
        // Convert currentTickets (array of IDs) to proper format expected by server
        const ticketsForServer = currentTickets.map(ticketId => ({
            id_ticket: ticketId,
            id_empresa: EMPRESA_ID || 1,
            id_tienda: 1,
            id_balanza_maestra: 1,
            id_balanza_esclava: -1,
            tipo_venta: 2
        }));
        
        finalTicketsInput.value = JSON.stringify(ticketsForServer);
    }
    
    // ✅ IMPORTANTE: Aggiungi anche i ticket manuali al form
    const form = document.getElementById('final-ddt-form');
    if (form) {
        let manualTicketsInput = form.querySelector('input[name="manual_tickets"]');
        
        if (!manualTicketsInput) {
            manualTicketsInput = document.createElement('input');
            manualTicketsInput.type = 'hidden';
            manualTicketsInput.name = 'manual_tickets';
            form.appendChild(manualTicketsInput);
        }
        
        manualTicketsInput.value = JSON.stringify(manualTickets);
        
        let discountsInput = form.querySelector('input[name="ticket_discounts"]');
        
        if (!discountsInput) {
            discountsInput = document.createElement('input');
            discountsInput.type = 'hidden';
            discountsInput.name = 'ticket_discounts';
            form.appendChild(discountsInput);
        }
        
        discountsInput.value = JSON.stringify(ticketDiscounts);
    }
}

// ===== GESTIONE RICERCA PRODOTTI =====
function searchProducts(query) {
    const dropdownContainer = document.getElementById('product-search-dropdown');
    if (!dropdownContainer) return;
    
    dropdownContainer.innerHTML = '<div class="p-3 text-center"><i class="fas fa-spinner fa-spin me-2"></i>Ricerca in corso...</div>';
    dropdownContainer.style.display = 'block';
    dropdownContainer.style.zIndex = '9999';
    
    // Chiamata API reale per la ricerca prodotti
    fetch(`/articles/api/search?query=${encodeURIComponent(query)}`)
    .then(response => response.json())
    .then(data => {
        if (Array.isArray(data) && data.length > 0) {
            // Converte i dati degli articoli nel formato atteso
            const products = data.map(article => ({
                id: article.id,
                descripcion: article.description || article.text || `Articolo ${article.id}`,
                precio: parseFloat(article.price) || 0,
                iva: article.iva || 4, // Usa IVA dall'articolo o 4% come fallback
                iva_from_db: article.iva || 0, // IVA originale dal database (solo per riferimento)
                has_custom_price: false,
                comportamiento: article.comportamiento || 1, // Usa comportamiento dal database o default peso
                ean: article.ean || ''
            }));
            
            displayProductResults(products);
        } else {
            dropdownContainer.innerHTML = `
                <div class="p-4 text-center text-muted">
                    <i class="fas fa-search fa-2x mb-3 opacity-50"></i>
                    <p class="mb-0">Nessun prodotto trovato</p>
                    <small>Prova con un termine di ricerca diverso</small>
                </div>
            `;
            dropdownContainer.style.zIndex = '9999';
        }
    })
    .catch(error => {
        console.error('Errore nella ricerca prodotti:', error);
        dropdownContainer.innerHTML = `
            <div class="p-4 text-center text-danger">
                <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                <p class="mb-0">Errore nella ricerca</p>
                <small>Riprova tra qualche istante</small>
            </div>
        `;
        dropdownContainer.style.zIndex = '9999';
    });
}

// Funzione helper per determinare l'IVA dall'articolo
function getIvaFromArticle(article) {
    // Logica per determinare l'IVA basata sull'articolo
    // Puoi adattare questa logica in base ai tuoi dati
    if (article.Iva !== undefined) return article.Iva;
    if (article.iva !== undefined) return article.iva;
    
    // Default: 4% per prodotti alimentari
    return 4;
}

function displayProductResults(products) {
    const dropdownContainer = document.getElementById('product-search-dropdown');
    
    if (!dropdownContainer) return;
    
    if (products.length === 0) {
        dropdownContainer.innerHTML = `
            <div class="p-4 text-center text-muted">
                <i class="fas fa-search fa-2x mb-3 opacity-50"></i>
                <p class="mb-0">Nessun prodotto trovato</p>
                <small>Prova con un termine di ricerca diverso</small>
            </div>
        `;
        dropdownContainer.style.display = 'block';
        dropdownContainer.style.zIndex = '9999';
        return;
    }
    
    let html = '<div class="list-group list-group-flush">';
    products.forEach((product, index) => {
        html += `
            <div class="list-group-item list-group-item-action p-3" 
                 style="cursor: pointer; border-left: 4px solid transparent; transition: all 0.2s ease;"
                 onmouseover="this.style.borderLeftColor='#0d6efd'; this.style.backgroundColor='#f8f9ff'"
                 onmouseout="this.style.borderLeftColor='transparent'; this.style.backgroundColor='white'"
                 onclick="selectProductFromDropdown(${product.id}, '${product.descripcion.replace(/'/g, "\\'")}', ${product.precio}, ${product.iva_from_db || 0}, ${product.comportamiento || 1})">
                
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1 fw-bold text-dark">${product.descripcion}</h6>
                        <div class="d-flex align-items-center gap-3 mb-2">
                            <span class="badge bg-primary">ID: ${product.id}</span>
                            <span class="badge ${product.comportamiento == 1 ? 'bg-success' : 'bg-info'}">
                                ${product.comportamiento == 1 ? '⚖️ Peso (kg)' : '🔢 Pezzo (pz)'}
                            </span>
                            ${product.ean ? `<span class="badge bg-secondary">EAN: ${product.ean}</span>` : ''}
                    </div>
                        <div class="d-flex align-items-center gap-3">
                            <span class="text-success fw-semibold">
                                <i class="fas fa-euro-sign me-1"></i>€${product.precio.toFixed(2)}/${product.comportamiento == 1 ? 'kg' : 'pz'}
                            </span>
                            <span class="text-muted small">
                                <i class="fas fa-percentage me-1"></i>IVA: ${product.iva || 4}%
                            </span>
                        </div>
                    </div>
                    <div class="text-end">
                        <button class="btn btn-success btn-sm" onclick="event.stopPropagation(); selectProductFromDropdown(${product.id}, '${product.descripcion.replace(/'/g, "\\'")}', ${product.precio}, ${product.iva_from_db || 0}, ${product.comportamiento || 1})">
                            <i class="fas fa-plus me-1"></i>Aggiungi
                    </button>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    dropdownContainer.innerHTML = html;
    dropdownContainer.style.display = 'block';
    dropdownContainer.style.zIndex = '9999';
}

// Nuova funzione per selezionare prodotto dal dropdown
function selectProductFromDropdown(id, descripcion, precio, iva_from_db, comportamiento) {
    console.log('➕ Prodotto selezionato dal dropdown:', {id, descripcion, precio, iva_from_db, comportamiento});
    
    // Aggiungi il prodotto al ticket
    selectedProducts.push({
        id: id,
        descripcion: descripcion,
        precio: precio,
        iva: iva_from_db || 4, // Usa IVA dal database o 4% come fallback
        iva_from_db: iva_from_db || 0, // IVA originale dal database (solo per riferimento)
        peso: comportamiento == 1 ? 0.1 : 1, // Default: 0.1kg o 1 pezzo
        comportamiento: comportamiento || 1, // Usa il comportamiento dal database
        lotto: '' // Campo lotto vuoto per default
    });

    // Salva nel localStorage
    saveSelectedProductsToStorage();

    updateSelectedProductsList();
    updateTicketTotal();

    // Pulisci ricerca e nascondi dropdown
    const searchInput = document.getElementById('product-search');
    const dropdown = document.getElementById('product-search-dropdown');
    
    if (searchInput) searchInput.value = '';
    if (dropdown) dropdown.style.display = 'none';
    
    showNotification(`"${descripcion}" aggiunto al ticket`, 'success');
}

function addProductToTicketFromSearch(id, descripcion, precio, iva_from_db) {
    console.log('➕ Aggiungendo prodotto al ticket dalla ricerca:', {id, descripcion, precio, iva_from_db});

    // 🚨 IMPORTANTE: IVA è sempre 4% di default per ticket manuali, NON dal database
    selectedProducts.push({
        id: id,
        descripcion: descripcion,
        precio: precio,
        iva: iva_from_db || 4, // Usa IVA dal database o 4% come fallback
        iva_from_db: iva_from_db || 0, // IVA originale dal database (solo per riferimento)
        peso: 1.0,
        comportamiento: 1, // Default: peso (kg)
        lotto: '' // Campo lotto vuoto per default
    });

    // Salva nel localStorage
    saveSelectedProductsToStorage();

    updateSelectedProductsList();
    updateTicketTotal();

    // Pulisci ricerca
    const searchInput = document.getElementById('product-search');
    const dropdown = document.getElementById('product-search-dropdown');

    if (searchInput) searchInput.value = '';
    if (dropdown) dropdown.style.display = 'none';

    showNotification(`Prodotto "${descripcion}" aggiunto al ticket (IVA iniziale: 4%, modificabile)`, 'success');
}

// ===== GESTIONE LOCAL STORAGE PER PRODOTTI SELEZIONATI =====
function saveSelectedProductsToStorage() {
    try {
        localStorage.setItem('ddt_selected_products', JSON.stringify(selectedProducts));
        console.log('💾 Prodotti selezionati salvati nel localStorage:', selectedProducts.length, 'prodotti');
    } catch (error) {
        console.error('❌ Errore nel salvataggio prodotti selezionati:', error);
    }
}

function restoreSelectedProductsFromStorage() {
    try {
        const stored = localStorage.getItem('ddt_selected_products');
        if (stored) {
            selectedProducts = JSON.parse(stored);
            console.log('📦 Prodotti selezionati ripristinati dal localStorage:', selectedProducts.length, 'prodotti');

            // Aggiorna l'UI se ci sono prodotti ripristinati
            if (selectedProducts.length > 0) {
                updateSelectedProductsList();
            }
        }
    } catch (error) {
        console.error('❌ Errore nel ripristino prodotti selezionati:', error);
        selectedProducts = [];
    }
}

function clearSelectedProductsFromStorage() {
    try {
        localStorage.removeItem('ddt_selected_products');
        console.log('🗑️ Prodotti selezionati rimossi dal localStorage');
    } catch (error) {
        console.error('❌ Errore nella rimozione prodotti selezionati:', error);
    }
}

function updateSelectedProductsList() {
    const container = document.getElementById('selected-products-list');
    const emptyState = document.getElementById('empty-products-state');
    const ticketSummary = document.getElementById('ticket-summary');
    const productsCountBadge = document.getElementById('products-count-badge');
    const ticketItemsSummary = document.getElementById('ticket-items-summary');
    const ticketTotalAmount = document.getElementById('ticket-total-amount');
    
    if (selectedProducts.length === 0) {
        // Mostra stato vuoto
        if (emptyState) emptyState.style.display = 'block';
        if (ticketSummary) ticketSummary.style.display = 'none';
        if (productsCountBadge) productsCountBadge.textContent = '0 prodotti';
        
        const saveBtn = document.getElementById('save-manual-ticket');
        if (saveBtn) saveBtn.disabled = true;
        return;
    }
    
    // Nascondi stato vuoto e mostra contenuto
    if (emptyState) emptyState.style.display = 'none';
    if (ticketSummary) ticketSummary.style.display = 'block';
    
    // Aggiorna badge conteggio
    if (productsCountBadge) {
        productsCountBadge.textContent = `${selectedProducts.length} prodott${selectedProducts.length === 1 ? 'o' : 'i'}`;
    }
    
    let html = '<div class="p-3">';
    let totalTicket = 0;
    
    selectedProducts.forEach((product, index) => {
        const total = product.peso * product.precio;
        totalTicket += total;
        
        html += `
            <div class="product-card mb-4 p-4 border rounded-3 shadow-sm bg-white" style="border-left: 4px solid #0d6efd !important;" data-product-index="${index}">
                <!-- Header Prodotto -->
                <div class="d-flex justify-content-between align-items-start mb-4">
                        <div class="flex-grow-1">
                        <h5 class="fw-bold text-primary mb-1">${product.descripcion}</h5>
                        <div class="d-flex align-items-center gap-3">
                            <span class="badge bg-light text-dark">ID: ${product.id}</span>
                            <small class="text-muted">
                                <i class="fas fa-tag me-1"></i>Prodotto ${product.comportamiento === 1 || product.comportamiento === undefined ? 'pesabile' : 'numerabile'}
                            </small>
                        </div>
                    </div>
                    <button type="button" class="btn btn-outline-danger btn-sm" onclick="event.preventDefault(); event.stopPropagation(); removeProductFromTicket(${index});"
                            title="Rimuovi prodotto">
                        <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                    
                <!-- Controlli Principali -->
                <div class="row g-3 mb-4">
                    <!-- Tipo Articolo -->
                    <div class="col-lg-3 col-md-6">
                        <label class="form-label fw-semibold text-dark">
                            <i class="fas fa-toggle-on text-primary me-2"></i>Tipo Articolo
                            </label>
                        <select class="form-select form-select-lg" onchange="updateProductType(${index}, this.value)">
                            <option value="1" ${product.comportamiento === 1 || product.comportamiento === undefined ? 'selected' : ''}>⚖️ Peso (kg)</option>
                            <option value="0" ${product.comportamiento === 0 ? 'selected' : ''}>🔢 Pezzo (pz)</option>
                        </select>
                        </div>
                    
                    <!-- Quantità/Peso -->
                    <div class="col-lg-3 col-md-6">
                        <label class="form-label fw-semibold text-dark">
                            <i class="fas fa-${product.comportamiento === 1 || product.comportamiento === undefined ? 'weight-hanging' : 'hashtag'} text-success me-2"></i>
                            ${product.comportamiento === 1 || product.comportamiento === undefined ? 'Peso (kg)' : 'Quantità (pz)'}
                            </label>
                        <input type="number" class="form-control form-control-lg" 
                               value="${product.peso}" 
                               step="${product.comportamiento === 1 || product.comportamiento === undefined ? '0.001' : '1'}"
                               min="${product.comportamiento === 1 || product.comportamiento === undefined ? '0.001' : '1'}"
                               onchange="updateProductWeight(${index}, this.value)">
                    </div>
                    
                    <!-- Prezzo Unitario -->
                    <div class="col-lg-3 col-md-6">
                        <label class="form-label fw-semibold text-dark">
                            <i class="fas fa-euro-sign text-warning me-2"></i>
                            Prezzo (€/${product.comportamiento === 1 || product.comportamiento === undefined ? 'kg' : 'pz'})
                        </label>
                        <input type="number" class="form-control form-control-lg" 
                                   value="${product.precio}" step="0.01" min="0.01"
                               onchange="updateProductPrice(${index}, this.value)">
                        </div>
                    
                    <!-- IVA -->
                    <div class="col-lg-3 col-md-6">
                        <label class="form-label fw-semibold text-dark">
                            <i class="fas fa-percentage text-info me-2"></i>Aliquota IVA
                            </label>
                        <select class="form-select form-select-lg" onchange="updateProductIva(${index}, this.value)">
                                <option value="0" ${product.iva == 0 ? 'selected' : ''}>🚫 0% - Esente</option>
                            <option value="4" ${product.iva == 4 ? 'selected' : ''}>🥬 4% - Alimentari Base</option>
                            <option value="10" ${product.iva == 10 ? 'selected' : ''}>🍕 10% - Alimentari</option>
                            <option value="22" ${product.iva == 22 ? 'selected' : ''}>🥤 22% - Bevande/Altri</option>
                            </select>
                        </div>
                </div>
                
                <!-- Campo Lotto -->
                <div class="row g-3 mb-3">
                    <div class="col-md-8">
                        <label class="form-label fw-semibold text-dark">
                            <i class="fas fa-barcode text-secondary me-2"></i>Codice Lotto
                            </label>
                        <input type="text" class="form-control form-control-lg" 
                               value="${product.lotto || ''}" 
                               placeholder="Inserisci codice lotto (opzionale)"
                               oninput="updateProductLotto(${index}, this.value)">
                            </div>
                    <div class="col-md-4 d-flex align-items-end">
                        <div class="alert alert-info mb-0 w-100">
                            <small class="mb-0">
                                <i class="fas fa-info-circle me-1"></i>
                                Il lotto verrà incluso nel DDT e nella fattura
                            </small>
                        </div>
                    </div>
                </div>
                
                <!-- Totale Riga -->
                <div class="row">
                    <div class="col-12">
                        <div class="alert alert-success mb-0 d-flex justify-content-between align-items-center">
                            <span class="fw-semibold">
                                <i class="fas fa-calculator me-2"></i>Totale Riga:
                            </span>
                            <span class="fs-4 fw-bold">€ ${total.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
    
    // Aggiorna il riepilogo
    if (ticketItemsSummary) {
        ticketItemsSummary.textContent = `${selectedProducts.length} articol${selectedProducts.length === 1 ? 'o' : 'i'} → ${selectedProducts.length} ticket${selectedProducts.length === 1 ? '' : ' separati'}`;
    }
    if (ticketTotalAmount) {
        ticketTotalAmount.textContent = totalTicket.toFixed(2);
    }
    
    const saveBtn = document.getElementById('save-manual-ticket');
    if (saveBtn) saveBtn.disabled = false;
}

function removeProductFromTicket(index) {
    const product = selectedProducts[index];
    selectedProducts.splice(index, 1);

    // Salva nel localStorage
    saveSelectedProductsToStorage();

    updateSelectedProductsList();
    updateTicketTotal();
    showNotification(`Prodotto "${product.descripcion}" rimosso dalla selezione`, 'info');
}

function updateProductWeight(index, weight) {
    selectedProducts[index].peso = parseFloat(weight) || 1.0;

    // Salva nel localStorage
    saveSelectedProductsToStorage();

    updateSelectedProductsList();
    updateTicketTotal();
}

function updateProductPrice(index, price) {
    selectedProducts[index].precio = parseFloat(price) || 0.01;

    // Salva nel localStorage
    saveSelectedProductsToStorage();

    updateSelectedProductsList();
    updateTicketTotal();
}

function updateProductIva(index, iva) {
    // CORREZIONE: Gestisce correttamente IVA 0% che è un valore valido
    const ivaValue = parseInt(iva);
    const oldIva = selectedProducts[index].iva;
    selectedProducts[index].iva = isNaN(ivaValue) ? 4 : ivaValue;  // Solo se NaN usa default 4%
    
    console.log(`🎯 IVA cambiata per prodotto ${index}: ${oldIva}% → ${iva}% → SALVATA: ${selectedProducts[index].iva}%`);
    console.log(`🚨 DEBUG updateProductIva: input="${iva}" (${typeof iva}) → parseInt=${ivaValue} → isNaN=${isNaN(ivaValue)} → finale=${selectedProducts[index].iva}`);

    // Salva nel localStorage
    saveSelectedProductsToStorage();

    // Notifica all'utente per confermare che il cambio è andato a buon fine
    const ivaText = selectedProducts[index].iva === 0 ? "🚫 Esente IVA (0%)" : `${selectedProducts[index].iva}%`;
    showNotification(`IVA aggiornata a ${ivaText} per "${selectedProducts[index].descripcion}"`, 'success', 2000);
    
    updateSelectedProductsList();  // Aggiorna la lista per mostrare il nuovo calcolo
    updateTicketTotal();
}

function updateProductType(index, comportamiento) {
    const oldType = selectedProducts[index].comportamiento || 1;
    const newType = parseInt(comportamiento);

    // Validazione: comportamento deve essere 0 o 1
    if (newType !== 0 && newType !== 1) {
        console.error(`❌ Tipo articolo non valido: ${comportamiento}`);
        return;
    }

    // Prima aggiorna i dati locali
    selectedProducts[index].comportamiento = newType;
    
    // Se cambia da peso a pezzo, imposta quantità a numero intero
    if (oldType === 1 && newType === 0) {
        selectedProducts[index].peso = Math.max(1, Math.round(selectedProducts[index].peso));
    }
    
    const typeText = newType === 1 ? "⚖️ Peso (kg)" : "🔢 Pezzo (pz)";
    console.log(`🔄 Tipo articolo cambiato per "${selectedProducts[index].descripcion}": ${typeText} (old: ${oldType}, new: ${newType})`);

    // Salva nel localStorage
    saveSelectedProductsToStorage();

    // Poi aggiorna la visualizzazione per riflettere il cambiamento
    updateSelectedProductsList();
    updateTicketTotal();

    showNotification(`Tipo articolo cambiato a ${typeText}`, 'success', 1500);
}


function updateProductLotto(index, lotto) {
    const trimmedLotto = lotto.trim();
    selectedProducts[index].lotto = trimmedLotto;
    console.log(`📦 Lotto aggiornato per "${selectedProducts[index].descripcion}": "${trimmedLotto}"`);

    // Salva nel localStorage immediatamente
    saveSelectedProductsToStorage();

    if (trimmedLotto) {
        showNotification(`Lotto "${trimmedLotto}" assegnato a "${selectedProducts[index].descripcion}"`, 'success', 2000);
    }

    // Non serve aggiornare la lista per il lotto, è solo un campo di testo
}

function updateTicketTotal() {
    const totalProducts = selectedProducts.length;
    const totalWeight = selectedProducts.reduce((sum, product) => sum + product.peso, 0);
    const totalAmount = selectedProducts.reduce((sum, product) => sum + (product.peso * product.precio), 0);
    
    const productsEl = document.getElementById('ticket-total-products');
    const weightEl = document.getElementById('ticket-total-weight');
    const amountEl = document.getElementById('ticket-total-amount');
    
    if (productsEl) productsEl.textContent = totalProducts;
    if (weightEl) weightEl.textContent = `${totalWeight.toFixed(3)} kg`;
    if (amountEl) amountEl.textContent = `€ ${totalAmount.toFixed(2)}`;
}

// ===== GESTIONE TICKET ESISTENTI =====
function loadExistingTickets() {
    console.log('📋 Caricamento ticket esistenti...');
    
    const loadingDiv = document.getElementById('existing-tickets-loading');
    const listDiv = document.getElementById('existing-products-list');
    
    if (loadingDiv) loadingDiv.style.display = 'block';
    if (listDiv) listDiv.innerHTML = '';
    
    // Verifica che abbiamo il cliente ID
    if (!CLIENTE_ID) {
        console.error('❌ Cliente ID non disponibile');
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (listDiv) {
            listDiv.innerHTML = '<div class="text-danger text-center py-4"><i class="fas fa-exclamation-triangle me-2"></i>Cliente non selezionato</div>';
        }
        return;
    }
    
    // Chiamata API reale per caricare i ticket esistenti
    fetch(`/ddt/api/preview/search_tickets?cliente_id=${CLIENTE_ID}&limit=100`)
    .then(response => response.json())
    .then(data => {
        if (loadingDiv) loadingDiv.style.display = 'none';
        
        if (data.success && data.products && data.products.length > 0) {
            // Carica i dati reali e filtra i ticket già aggiunti al DDT
            existingProductsData = data.products;
            
            // Crea set degli ID dei ticket già inclusi nel DDT
            const excludedTicketIds = new Set();
            
            // Aggiungi ticket iniziali già selezionati
            currentTickets.forEach(ticketId => {
                excludedTicketIds.add(parseInt(ticketId));
            });
            
            // Aggiungi ticket esistenti già aggiunti
            addedExistingTickets.forEach(ticket => {
                excludedTicketIds.add(parseInt(ticket.id_ticket));
            });
            
            // I ticket manuali hanno ID negativi quindi non dovrebbero essere nel database
            // ma per sicurezza li aggiungiamo comunque al set di esclusione
            manualTickets.forEach(ticket => {
                excludedTicketIds.add(parseInt(ticket.id_ticket));
            });
            
            console.log('🚫 Ticket da escludere dal modale:', Array.from(excludedTicketIds));
            
            // Filtra i prodotti rimuovendo i ticket già inclusi nel DDT
            const filteredProducts = existingProductsData.map(product => {
                const filteredTickets = product.tickets.filter(ticket => {
                    const ticketId = parseInt(ticket.IdTicket);
                    return !excludedTicketIds.has(ticketId);
                });
                
                // Ritorna il prodotto solo se ha ancora ticket disponibili
                if (filteredTickets.length > 0) {
                    return {
                        ...product,
                        tickets: filteredTickets
                    };
                }
                return null;
            }).filter(product => product !== null);
            
            existingProductsFiltered = filteredProducts;
            
            displayExistingTickets(filteredProducts);
            console.log(`✅ Caricati ${data.products.length} prodotti, ${filteredProducts.length} con ticket disponibili dopo filtro`);
        } else {
            if (listDiv) {
                listDiv.innerHTML = '<div class="text-muted text-center py-4"><i class="fas fa-box-open fa-2x mb-3 opacity-50"></i><br>Nessun ticket disponibile per questo cliente</div>';
            }
            console.log('ℹ️ Nessun ticket esistente trovato');
        }
    })
    .catch(error => {
        console.error('❌ Errore nel caricamento ticket esistenti:', error);
        if (loadingDiv) loadingDiv.style.display = 'none';
        if (listDiv) {
            listDiv.innerHTML = '<div class="text-danger text-center py-4"><i class="fas fa-exclamation-triangle me-2"></i>Errore nel caricamento</div>';
        }
    });
}
// Fine della nuova implementazione loadExistingTickets() - dati mock rimossi

function displayExistingTickets(productsData) {
    const listDiv = document.getElementById('existing-products-list');
    const loadingDiv = document.getElementById('existing-tickets-loading');
    const emptyDiv = document.getElementById('existing-tickets-empty');
    
    if (!listDiv) return;
    
    // Nascondi loading
    if (loadingDiv) loadingDiv.style.display = 'none';
    
    if (productsData.length === 0) {
        listDiv.innerHTML = '';
        if (emptyDiv) {
            emptyDiv.classList.remove('d-none');
        }
        return;
    }
    
    // Nascondi stato vuoto
    if (emptyDiv) {
        emptyDiv.classList.add('d-none');
    }
    
    let html = '';
    productsData.forEach((product, index) => {
        const accordionId = `product-accordion-${index}`;
        
        // Calcola i totali per unità di misura
        let totalWeightKg = 0;
        let totalWeightPz = 0;
        let totalAmount = 0;
        
        product.tickets.forEach(ticket => {
            // Usa l'array lines se disponibile, altrimenti usa i dati diretti del ticket
            if (ticket.lines && Array.isArray(ticket.lines)) {
                ticket.lines.forEach(line => {
                    const peso = parseFloat(line.peso || 0);
                    // ✅ MODIFICA: Usa precio_con_iva per mostrare prezzi con IVA
                    const precio = parseFloat(line.precio_con_iva || line.precio || 0);

                    if (parseInt(line.comportamiento) === 1) {
                        totalWeightKg += peso;
                    } else {
                        totalWeightPz += peso;
                    }
                    // ✅ MODIFICA: Calcola il totale usando il prezzo con IVA
                    totalAmount += peso * precio;
                });
            } else {
                // Fallback: usa i dati aggregati del ticket
                const peso = parseFloat(ticket.peso_total || 0);
                // ✅ MODIFICA: Usa il prezzo con IVA dal ticket se disponibile
                const precio = parseFloat(ticket.lines && ticket.lines[0] ? ticket.lines[0].precio_con_iva : ticket.importe_total / peso || 0);
                totalAmount += peso * precio;

                // Assumiamo che se comportamiento non è specificato, usiamo il comportamiento del prodotto
                if (parseInt(product.comportamiento) === 1) {
                    totalWeightKg += peso;
                } else {
                    totalWeightPz += peso;
                }
            }
        });
        
        // Costruisci la stringa del totale in base alle unità presenti
        let totalQuantityText = '';
        if (totalWeightKg > 0 && totalWeightPz > 0) {
            totalQuantityText = `${totalWeightKg.toFixed(3)} kg | ${Math.round(totalWeightPz)} pz`;
        } else if (totalWeightKg > 0) {
            totalQuantityText = `${totalWeightKg.toFixed(3)} kg`;
        } else if (totalWeightPz > 0) {
            totalQuantityText = `${Math.round(totalWeightPz)} pz`;
        } else {
            totalQuantityText = '0 kg';
        }
        
        html += `
            <div class="accordion-item" style="border: 1px solid #e9ecef; margin-bottom: 2px;">
                <!-- Header del prodotto -->
                <div class="accordion-header">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#${accordionId}" aria-expanded="false" aria-controls="${accordionId}"
                            style="background: #f8f9fa; border: none; padding: 15px 20px;">
                        <div class="d-flex w-100 justify-content-between align-items-center">
                            <div class="d-flex align-items-center gap-3">
                                <i class="fas fa-box text-primary"></i>
                                <div>
                                    <h6 class="mb-0 fw-bold">${product.descripcion}</h6>
                                    <small class="text-muted">Codice: ${product.id_articulo}</small>
                                </div>
                            </div>
                            <div class="d-flex gap-3 text-end">
                                <div>
                                    <span class="badge bg-primary">${product.tickets.length} ticket</span>
                                </div>
                                <div>
                                    <small class="text-muted">Tot. ${totalQuantityText}</small>
                                </div>
                                <div>
                                    <small class="text-success fw-bold">€${totalAmount.toFixed(2)}</small>
                                </div>
                            </div>
                        </div>
                    </button>
                </div>
                
                <!-- Contenuto espandibile con i ticket -->
                <div id="${accordionId}" class="accordion-collapse collapse">
                    <div class="accordion-body p-0">
                        ${product.tickets.map(ticket => {
                            // Calcola i totali del singolo ticket per unità di misura
                            let ticketWeightKg = 0;
                            let ticketWeightPz = 0;
                            
                            if (ticket.lines && Array.isArray(ticket.lines)) {
                                ticket.lines.forEach(line => {
                                    const peso = parseFloat(line.peso || 0);
                                    if (parseInt(line.comportamiento) === 1) {
                                        ticketWeightKg += peso;
                                    } else {
                                        ticketWeightPz += peso;
                                    }
                                });
                            } else {
                                // Fallback: usa i dati aggregati del ticket
                                const peso = parseFloat(ticket.peso_total || 0);
                                if (parseInt(product.comportamiento) === 1) {
                                    ticketWeightKg += peso;
                                } else {
                                    ticketWeightPz += peso;
                                }
                            }
                            
                            // Costruisci la stringa della quantità del singolo ticket
                            let ticketQuantityText = '';
                            if (ticketWeightKg > 0 && ticketWeightPz > 0) {
                                ticketQuantityText = `${ticketWeightKg.toFixed(3)} kg | ${Math.round(ticketWeightPz)} pz`;
                            } else if (ticketWeightKg > 0) {
                                ticketQuantityText = `${ticketWeightKg.toFixed(3)} kg`;
                            } else if (ticketWeightPz > 0) {
                                ticketQuantityText = `${Math.round(ticketWeightPz)} pz`;
                            } else {
                                ticketQuantityText = '0 kg';
                            }
                            
                            return `
                                <div class="existing-ticket-item" style="border-bottom: 1px solid #e9ecef; padding: 12px 20px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; background: white;"
                                     data-ticket-id="${ticket.IdTicket}"
                                     onclick="toggleTicketSelection('${ticket.IdTicket}')">
                                    <div style="display: flex; align-items: center; gap: 15px; flex: 1;">
                                        <div style="min-width: 30px;">
                                            <input type="checkbox" class="form-check-input ticket-checkbox" 
                                                   data-ticket-id="${ticket.IdTicket}" 
                                                   style="width: 18px; height: 18px;">
                                        </div>
                                        <div style="min-width: 100px; font-size: 1rem; font-weight: 700; color: var(--primary-dark);">
                                            #${ticket.IdTicket}
                                        </div>
                                        <div style="min-width: 120px; font-size: 0.9rem; color: #6c757d;">
                                            ${ticket.fecha_formateada}
                                        </div>
                                        <div style="min-width: 120px; text-align: center; font-size: 0.9rem; color: var(--accent-blue); font-weight: 600;">
                                            ${ticketQuantityText}
                                        </div>
                                        <div style="min-width: 90px; text-align: center; font-size: 0.9rem; color: var(--warning-orange); font-weight: 600;">
                                            €${(() => {
                                                // ✅ MODIFICA: Calcola il prezzo con IVA per il singolo ticket
                                                if (ticket.lines && ticket.lines.length > 0) {
                                                    const line = ticket.lines[0];
                                                    const peso = parseFloat(line.peso || 0);
                                                    const precio = parseFloat(line.precio_con_iva || line.precio || 0);
                                                    return (peso * precio).toFixed(2);
                                                } else {
                                                    // Fallback al valore esistente se non ci sono linee
                                                    return parseFloat(ticket.importe_total || 0).toFixed(2);
                                                }
                                            })()}
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            </div>
        `;
    });
    
    listDiv.innerHTML = html;
    
    // Setup event listeners per checkbox
    document.querySelectorAll('.ticket-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedTicketsCount);
    });
    
    // Setup event listeners per pulsanti di controllo
    const selectAllBtn = document.getElementById('select-all-tickets');
    const deselectAllBtn = document.getElementById('deselect-all-tickets');
    const addSelectedBtn = document.getElementById('add-selected-tickets');
    
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            document.querySelectorAll('.ticket-checkbox').forEach(cb => cb.checked = true);
            updateSelectedTicketsCount();
        });
    }
    
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function() {
            document.querySelectorAll('.ticket-checkbox').forEach(cb => cb.checked = false);
            updateSelectedTicketsCount();
        });
    }
    
         if (addSelectedBtn) {
         addSelectedBtn.addEventListener('click', function() {
             const selectedCheckboxes = document.querySelectorAll('.ticket-checkbox:checked');
             if (selectedCheckboxes.length > 0) {
                 console.log('🔄 Aggiungo ticket selezionati al DDT...');
                 
                 // Chiamata alla funzione principale di aggiunta
                 addSelectedTicketsToPreview();
             } else {
                 showNotification('Seleziona almeno un ticket da aggiungere', 'warning');
             }
         });
     }
}

function toggleTicketSelection(ticketId) {
    const checkbox = document.querySelector(`input[data-ticket-id="${ticketId}"]`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        updateSelectedTicketsCount();
    }
}



// ===== SALVATAGGIO TICKET MANUALE =====
function saveManualTicket() {
    console.log('💾 Salvataggio ticket manuale');
    
    if (selectedProducts.length === 0) {
        showNotification('Aggiungi almeno un prodotto al ticket prima di salvare', 'warning');
        return;
    }
    
    // 🚨 DEBUG: Stampa tutte le IVA dei prodotti prima del salvataggio
    console.log('🔍 DEBUG - Prodotti nel ticket:');
    selectedProducts.forEach((product, index) => {
        console.log(`   Prodotto ${index + 1}: "${product.descripcion}"`);
        console.log(`     → IVA: ${product.iva}% (tipo: ${typeof product.iva})`);
        console.log(`     → Prezzo: €${product.precio}`);
        console.log(`     → Peso: ${product.peso}`);
    });
    
    const btn = document.getElementById('save-manual-ticket');
    const originalHTML = btn.innerHTML;
    
    // Mostra loading
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creazione...';
    btn.disabled = true;
    
    // Simula creazione ticket manuale
    setTimeout(() => {
        // 🔍 DEBUG: Verifica che l'IVA selezionata sia corretta prima del salvataggio
        console.log('🚨 VERIFICA IVA PRIMA DEL SALVATAGGIO:');
        selectedProducts.forEach((product, index) => {
            console.log(`   Prodotto ${index + 1}: "${product.descripcion}" → IVA ${product.iva}%`);
        });
        
        const newTicket = {
            id_ticket: -(new Date().getTime()), // ID negativo per ticket manuali
            num_ticket: `MANUAL-${Date.now()}`,
            fecha: new Date().toLocaleDateString('it-IT'),
            total: selectedProducts.reduce((sum, product) => sum + (product.peso * product.precio), 0),
            lines: selectedProducts.map(product => {
                // Mappa la percentuale IVA al corrispondente ID
                let idIva = 1; // Default 4%
                const ivaPercent = product.iva !== undefined ? product.iva : 4;  // CORRETTO: gestisce IVA 0%
                switch (ivaPercent) {
                    case 0: idIva = 0; break;  // 0% - Esente
                    case 4: idIva = 1; break;  // 4% - Alimentari Base
                    case 10: idIva = 2; break; // 10% - Alimentari
                    case 22: idIva = 3; break; // 22% - Bevande/Altri
                    default: idIva = 1; break; // Default 4%
                }
                
                console.log(`🎫 Prodotto ${product.descripcion}: IVA SELEZIONATA ${ivaPercent}% → ID ${idIva} (CONFERMATA dall'utente nel modale)`);
                console.log(`🚨 DEBUG MAPPING IVA: product.iva=${product.iva} (${typeof product.iva}) → ivaPercent=${ivaPercent} → idIva=${idIva}`);
                
                return {
                    id_articulo: product.id,
                    descripcion: product.descripcion,
                    peso: product.peso,
                    precio: product.precio, // Questo è già CON IVA
                    importe: product.peso * product.precio,
                    comportamiento: product.comportamiento,
                    id_iva: idIva, // ID IVA mappato correttamente
                    iva: ivaPercent, // Percentuale IVA SELEZIONATA dall'utente
                    porcentaje_iva: ivaPercent, // Campo aggiuntivo per compatibilità
                    id_linea_ticket: Math.random().toString(36).substr(2, 9),
                    lotto: product.lotto || '', // Campo lotto
                    is_manual: true // 🎫 Flag per identificare le linee dei ticket manuali
                };
            }),
            is_manual: true
        };
        
        // Aggiungi ai ticket manuali
        manualTickets.push(newTicket);
        saveManualTicketsToStorage();
        
        // Salva i prodotti selezionati nella lista recenti
        selectedProducts.forEach(product => {
            addProductToRecentList(product);
        });
        
        // 🚨 DEBUG: Verifica i dati IVA nelle linee del ticket manuale prima di aggiungerli a previewData
        console.log('🔍 DEBUG - Linee del ticket manuale prima di aggiungerle a previewData:');
        newTicket.lines.forEach((line, index) => {
            console.log(`   Linea ${index + 1}: id_iva=${line.id_iva}, iva=${line.iva}, descripcion="${line.descripcion}"`);
        });
        
        // Aggiungi ai dati preview con correzione dati IVA
        previewData[newTicket.id_ticket] = {
            ticket: newTicket,
            lines: newTicket.lines.map(line => ({
                ...line,
                // 🔧 CORREZIONE: Assicurati che entrambi i campi IVA siano presenti
                id_iva: line.id_iva !== undefined ? line.id_iva : (line.iva === 0 ? 0 : 1),
                iva: line.iva !== undefined ? line.iva : 4,
                porcentaje_iva: line.iva !== undefined ? line.iva : 4
            })),
            total: newTicket.total
        };
        
        console.log('✅ previewData aggiornato per ticket manuale:', newTicket.id_ticket);
        
        // Aggiorna UI dinamicamente senza ricaricare
        updateFormData();
        addTicketToTable(newTicket);
        
        showNotification('Ticket manuale creato con successo!', 'success');
        
        // Chiudi il modale e rimuovi backdrop
        const modal = bootstrap.Modal.getInstance(document.getElementById('createTicketModal'));
        if (modal) {
            modal.hide();
            // Forza la rimozione del backdrop dopo un piccolo delay
            setTimeout(() => {
                forceRemoveModalBackdrop();
            }, 300);
        }
        
        // Reset form
        selectedProducts = [];
        clearSelectedProductsFromStorage();
        updateSelectedProductsList();
        
        // Ripristina il pulsante
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        
    }, 1000);
}

// ===== FUNZIONI HELPER PER AGGIORNAMENTO TABELLA =====
function addTicketToTable(ticket) {
    console.log('📋 Aggiunta ticket alla tabella:', ticket);

    const tableBody = document.querySelector('#ddtTicketTable tbody');
    if (!tableBody) {
        console.error('❌ Tabella DDT non trovata');
        return;
    }

    // ✅ CORREZIONE: Controlla se il ticket è già presente nella tabella per evitare duplicati
    const ticketId = ticket.id_ticket || ticket.IdTicket;
    const existingRow = tableBody.querySelector(`tr[data-ticket-id="${ticketId}"]`);
    if (existingRow) {
        console.log('⚠️ Ticket già presente nella tabella, skip:', ticketId);
        return;
    }
    
    // Determina se è un ticket manuale o esistente
    const isManual = ticket.id_ticket < 0 || ticket.is_manual;
    const numTicket = ticket.IdTicket || ticket.id_ticket || ticket.num_ticket || ticket.NumTicket || ticketId;
    const fecha = ticket.fecha || ticket.fecha_formateada || new Date().toLocaleDateString('it-IT');
    
    // Calcola i dettagli del prodotto
    let productDescription = '';
    let hasLines = false;
    let firstLineId = null;
    
    if (ticket.lines && Array.isArray(ticket.lines) && ticket.lines.length > 0) {
        // Verifica che la prima linea abbia un ID valido
        const firstLine = ticket.lines[0];
        if (firstLine && (firstLine.id_linea_ticket || firstLine.IdLineaTicket)) {
            hasLines = true;
            firstLineId = firstLine.id_linea_ticket || firstLine.IdLineaTicket;
            productDescription = firstLine.descripcion || firstLine.Descripcion || 'Prodotto';
            
            if (ticket.lines.length > 1) {
                productDescription += ` + ${ticket.lines.length - 1} altri`;
            }
        } else {
            // Se non ha ID valido, NON permettere la modifica
            console.error('❌ ERRORE CRITICO: Ticket senza ID reale della linea:', firstLine);
            console.error('❌ Ticket ID:', ticketId, 'Non sarà possibile modificare questo ticket');
            
            hasLines = false;  // Non mostrare il pulsante di modifica
            firstLineId = null;
            productDescription = firstLine.descripcion || firstLine.Descripcion || 'Prodotto (NON MODIFICABILE)';
            
            if (ticket.lines.length > 1) {
                productDescription += ` + ${ticket.lines.length - 1} altri (NON MODIFICABILI)`;
            }
        }
    } else {
        productDescription = 'Nessun prodotto';
    }
    
    console.log('🔍 Debug ticket:', ticketId, 'hasLines:', hasLines, 'firstLineId:', firstLineId, 'lines:', ticket.lines?.length || 0);
    
    // ✅ MODIFICA: Calcola il totale del ticket usando prezzi con IVA
    const totalAmount = (() => {
        if (ticket.lines && ticket.lines.length > 0) {
            // Calcola il totale dalle linee usando prezzi con IVA
            return ticket.lines.reduce((sum, line) => {
                const peso = parseFloat(line.peso || 0);
                const precio = parseFloat(line.precio_con_iva || line.precio || 0);
                return sum + (peso * precio);
            }, 0);
        } else {
            // Fallback ai valori esistenti
            return ticket.total || ticket.ticket_total || ticket.importe_total || 0;
        }
    })();
    
    // Crea l'HTML della riga
    const rowHTML = `
        <tr data-ticket-id="${ticketId}">
            <td data-label="ID Ticket">
                <span class="badge ${isManual ? 'bg-warning' : 'bg-primary'}">#${numTicket}</span>
                ${isManual ? '<small class="text-muted d-block">Manuale</small>' : ''}
            </td>
            <td data-label="Data">
                <small class="text-muted">${fecha}</small>
            </td>
            <td data-label="Prodotti">
                <div class="text-truncate" style="max-width: 200px;" title="${productDescription}">
                    <i class="fas fa-cube text-muted me-1"></i>
                    <strong>${productDescription}</strong>
                </div>
            </td>
            <td data-label="Prezzo Unit.">
                <div class="d-flex align-items-center">
                    <span class="unit-price-value">--</span>
                    <span class="unit-type-icon ms-1"></span>
                </div>
            </td>
            <td data-label="Quantità">
                <div class="d-flex align-items-center">
                    <span class="quantity-value fw-bold">--</span>
                    <span class="quantity-unit ms-1"></span>
                </div>
            </td>
            <td data-label="Senza IVA">
                <span class="text-muted">
                    €&nbsp;<span class="price-no-vat">--</span>
                </span>
            </td>
            <td data-label="Con IVA">
                <span class="text-success">
                    €&nbsp;<span class="price-with-vat">--</span>
                </span>
            </td>
            <td data-label="Sconto">
                <div class="discount-container" data-ticket-id="${ticketId}">
                    <div class="discount-dropdown-wrapper">
                        <input type="number"
                               class="discount-input-field"
                               data-ticket-id="${ticketId}"
                               placeholder="%"
                               min="0"
                               max="100"
                               step="0.1"
                               value="0"
                               title="Inserisci percentuale di sconto (0-100)">
                        <button type="button"
                                class="btn-remove-discount"
                                title="Rimuovi sconto"
                                style="display: none;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </td>
            <td data-label="Azioni" class="text-center">
                <div class="d-flex gap-1 justify-content-center">
                    ${hasLines && firstLineId ? 
                        `<button type="button" class="btn btn-sm btn-outline-primary edit-line-btn" 
                                data-ticket-id="${ticketId}"
                                data-line-id="${firstLineId}"
                                title="Modifica ticket">
                            <i class="fas fa-edit"></i>
                        </button>` : ''
                    }
                    <button type="button" class="btn btn-sm btn-outline-danger btn-remove-ticket" 
                            data-ticket-id="${ticketId}"
                            title="Rimuovi ticket">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
    
    // Aggiungi la riga alla tabella
    tableBody.insertAdjacentHTML('beforeend', rowHTML);
    
    // Setup event listeners per la nuova riga
    setupTableRowEventListeners(ticketId);

    // Setup event listeners per gli sconti
    setupDiscountEventListeners();

    // Aggiorna i dettagli prezzi per il ticket appena aggiunto
    setTimeout(() => {
        updateTicketPriceDetails(ticketId);
        // 🔥 AGGIUNTO: Aggiorna anche i totali dopo l'aggiunta
        setTimeout(updateTotalsBar, 150);
    }, 100);

    console.log(`✅ Ticket ${ticketId} aggiunto alla tabella`);

}

function setupTableRowEventListeners(ticketId) {
    // Event listener per il pulsante di rimozione
    const removeBtn = document.querySelector(`[data-ticket-id="${ticketId}"] .btn-remove-ticket`);
    if (removeBtn) {
        removeBtn.addEventListener('click', () => removeTicket(ticketId));
    }
    
    // Event listener per il pulsante di modifica
    const editBtn = document.querySelector(`[data-ticket-id="${ticketId}"] .edit-line-btn`);
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            const lineId = editBtn.getAttribute('data-line-id');
            openEditLineModal(ticketId, lineId);
        });
    }
    
    // Event listeners per gli sconti
    const discountSelect = document.querySelector(`[data-ticket-id="${ticketId}"] .ticket-discount`);
    const discountInput = document.querySelector(`[data-ticket-id="${ticketId}"] .ticket-discount-input`);
    
    if (discountSelect) {
        discountSelect.addEventListener('change', function() {
            const value = this.value;
            if (value === 'custom') {
                discountInput.style.display = 'block';
                discountInput.focus();
            } else {
                discountInput.style.display = 'none';
                discountInput.value = '';
                updateTicketDiscount(ticketId, parseFloat(value));
            }
        });
    }
    
    if (discountInput) {
        discountInput.addEventListener('input', function() {
            const value = parseFloat(this.value) || 0;
            updateTicketDiscount(ticketId, value);
        });
    }
}

// ===== FUNZIONE PULIZIA BACKDROP CONDIVISA =====
function forceRemoveModalBackdrop() {
    console.log('🧹 Rimozione forzata backdrop modale...');
    
    // Rimuovi tutti i backdrop rimasti
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => {
        console.log('🗑️ Rimuovendo backdrop:', backdrop);
        backdrop.remove();
    });
    
    // Rimuovi la classe modal-open dal body
    document.body.classList.remove('modal-open');
    
    // Rimuovi eventuali stili inline che bloccano lo scroll
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    console.log('✅ Cleanup backdrop completato');
}

// ===== FUNZIONE DI EMERGENZA PER L'UTENTE =====
// L'utente può chiamare questa funzione dalla console se si blocca
window.clearAllModalBackdrops = function() {
    console.log('🆘 FUNZIONE DI EMERGENZA: Pulizia completa backdrop');
    
    // Forza la chiusura di tutte le modali aperte
    const openModals = document.querySelectorAll('.modal.show');
    openModals.forEach(modal => {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
    });
    
    // Aspetta un momento e poi pulisci tutto
    setTimeout(() => {
        forceRemoveModalBackdrop();
        
        // Cleanup aggiuntivo per casi estremi
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        
        // Rimuovi anche overflow hidden che potrebbe essere rimasto
        document.documentElement.style.overflow = '';
        
        console.log('🎉 EMERGENZA RISOLTA: Tutti i backdrop rimossi');
        alert('✅ Backdrop puliti! La pagina dovrebbe essere nuovamente utilizzabile.');
    }, 500);
};

// Event listener globale per doppio ESC come scorciatoia di emergenza
let escPressCount = 0;
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        escPressCount++;
        if (escPressCount === 2) {
            console.log('🆘 Doppio ESC rilevato - pulizia emergenza backdrop');
            window.clearAllModalBackdrops();
            escPressCount = 0;
        }
        
        // Reset counter dopo 1 secondo
        setTimeout(() => {
            escPressCount = 0;
        }, 1000);
    }
});

// ===== SISTEMA DI REFRESH E GESTIONE CONFLITTI =====
function setupRefreshSystem() {
    console.log('🔄 Setup sistema di refresh automatico...');
    
    // Aggiungi listener per l'evento di cambiamento dati ticket
    document.addEventListener('ticketDataChanged', function(event) {
        console.log('📨 Ricevuto evento cambiamento ticket:', event.detail);
        // Potresti aggiungere qui logica per sincronizzazione in tempo reale
    });
    
    // Aggiungi pulsante di refresh forzato (nascosto, utilizzabile da console)
    if (!document.getElementById('force-refresh-data')) {
        const refreshBtn = document.createElement('button');
        refreshBtn.id = 'force-refresh-data';
        refreshBtn.className = 'btn btn-outline-info btn-sm';
        refreshBtn.style.display = 'none';
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Aggiorna Dati';
        refreshBtn.addEventListener('click', forceRefreshTicketData);
        document.body.appendChild(refreshBtn);
        
        // Esponi la funzione globalmente per debugging
        window.forceRefreshTicketData = forceRefreshTicketData;
    }
    
    // Setup pulizia automatica ogni 5 minuti
    setInterval(() => {
        clearExpiredModifications();
    }, 5 * 60 * 1000);
    
    // ⚡ CONTROLLO IMMEDIATO DEI PREZZI AL SETUP
    setTimeout(() => {
        console.log('⚡ Controllo prezzi al setup sistema refresh...');
        if (typeof checkPriceConsistency === 'function') {
            checkPriceConsistency();
        }
    }, 200);
    
    console.log('✅ Sistema di refresh configurato');
}

function forceRefreshTicketData() {
    console.log('🔄 Refresh forzato dati ticket...');
    
    if (!CLIENTE_ID) {
        console.error('❌ Impossibile aggiornare: Cliente ID non disponibile');
        showNotification('Errore: Cliente non selezionato', 'danger');
        return;
    }
    
    // Mostra indicatore di caricamento
    showNotification('Aggiornamento dati in corso...', 'info', 0);
    
    // Chiama l'API per ottenere i dati più recenti
    fetch(`/ddt/api/preview/refresh_ticket_data?cliente_id=${CLIENTE_ID}`)
    .then(response => response.json())
    .then(data => {
        if (data.success && data.preview_data) {
            console.log('✅ Dati aggiornati ricevuti dal server');
            
            // Confronta e aggiorna i dati mantenendo le modifiche locali
            mergeUpdatedTicketData(data.preview_data);

            showNotification('Dati aggiornati con successo!', 'success');
        } else {
            console.error('❌ Errore nell\'aggiornamento dati:', data.error);
            showNotification('Errore nell\'aggiornamento dati: ' + (data.error || 'Errore sconosciuto'), 'danger');
        }
    })
    .catch(error => {
        console.error('❌ Errore di rete nell\'aggiornamento:', error);
        showNotification('Errore di rete durante l\'aggiornamento', 'danger');
    });
}

function mergeUpdatedTicketData(serverData) {
    console.log('🔀 Merge dati aggiornati dal server...');
    
    try {
        // Carica le modifiche locali
        const stored = localStorage.getItem('ddt_ticket_modifications');
        const localModifications = stored ? JSON.parse(stored) : {};
        
        // Per ogni ticket nel server data
        serverData.forEach(item => {
            if (item && item.ticket && item.ticket.IdTicket) {
                const ticketId = item.ticket.IdTicket;
                
                // Aggiorna i dati base dal server
                if (previewData[ticketId]) {
                    previewData[ticketId].ticket = item.ticket;
                    previewData[ticketId].total = parseFloat(item.ticket_total) || 0;
                    
                    // Aggiorna le linee mantenendo le modifiche locali
                    if (item.lines && Array.isArray(item.lines)) {
                        item.lines.forEach(serverLine => {
                            const lineId = serverLine.id_linea_ticket;
                            if (lineId) {
                                // Trova la linea corrispondente nei dati locali
                                const localLineIndex = previewData[ticketId].lines.findIndex(
                                    line => line.id_linea_ticket == lineId
                                );
                                
                                if (localLineIndex !== -1) {
                                    // Aggiorna la linea locale con i dati del server
                                    const localLine = previewData[ticketId].lines[localLineIndex];
                                    const updatedLine = {...serverLine};
                                    
                                    // Applica le modifiche locali se esistono
                                    Object.keys(localModifications).forEach(modKey => {
                                        const mod = localModifications[modKey];
                                        if (mod.ticketId == ticketId && mod.lineId == lineId && !mod.applied) {
                                            console.log('🔧 Riapplicando modifica locale:', mod);
                                            applyModificationToLine(updatedLine, mod.field, mod.value);
                                        }
                                    });
                                    
                                    previewData[ticketId].lines[localLineIndex] = updatedLine;
                                } else {
                                    // Nuova linea dal server
                                    previewData[ticketId].lines.push(serverLine);
                                }
                            }
                        });
                    }
                    
                    // Ricalcola il totale
                    previewData[ticketId].total = previewData[ticketId].lines.reduce(
                        (sum, l) => sum + (parseFloat(l.importe) || 0), 0
                    );
                    
                    console.log(`✅ Ticket ${ticketId} aggiornato e mergiato`);
                }
            }
        });
        
        // Aggiorna la visualizzazione della tabella
        refreshTicketTable();
        
        console.log('✅ Merge dati completato');
        
    } catch (e) {
        console.error('❌ Errore nel merge dati:', e);
    }
}

function applyModificationToLine(line, field, value) {
    switch (field) {
        case 'peso_quantita':
            line.peso = parseFloat(value) || 0;
            break;
        case 'prezzo_unitario':
            line.precio = parseFloat(value) || 0;
            break;
        case 'prezzo_totale':
            line.importe = parseFloat(value) || 0;
            break;
        case 'descrizione':
            line.descripcion = value || '';
            break;
        case 'data_scadenza':
            line.fecha_caducidad = value;
            break;
    }
    
    // Ricalcola l'importe se necessario
    if (field === 'peso_quantita' || field === 'prezzo_unitario') {
        line.importe = line.peso * line.precio;
    }
}

function refreshTicketTable() {
    console.log('🔄 Refresh tabella ticket...');
    
    // Aggiorna i valori nella tabella esistente
    Object.keys(previewData).forEach(ticketId => {
        const ticketRow = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
        if (ticketRow) {
            const priceElement = ticketRow.querySelector('.price-value');
            if (priceElement) {
                const newTotal = previewData[ticketId].total || 0;
                priceElement.textContent = newTotal.toFixed(2);
            }
        }
    });
}

// ===== FUNZIONI HELPER PER DEBUGGING =====
window.debugDDTPreview = {
    showStoredModifications: function() {
        const stored = localStorage.getItem('ddt_ticket_modifications');
        console.log('Modifiche salvate:', stored ? JSON.parse(stored) : 'Nessuna');
    },
    
    clearStoredModifications: function() {
        localStorage.removeItem('ddt_ticket_modifications');
        console.log('🗑️ Modifiche salvate cancellate');
    },
    
    forceRefresh: forceRefreshTicketData,
    
    showPreviewData: function() {
        console.log('Dati preview attuali:', previewData);
    }
};

// ===== NUOVO SISTEMA SCONTI UX =====

// Inizializzazione sistema sconti migliorato
function initializeDiscountSystem() {
    console.log('🎯 Inizializzazione sistema sconti UX...');

    // Event listeners per i bottoni di sconto rapido
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('discount-btn')) {
            const ticketId = e.target.getAttribute('data-ticket-id');
            const discountValue = parseFloat(e.target.getAttribute('data-discount'));

            applyDiscountToTicket(ticketId, discountValue);
            updateDiscountButtonsUI(ticketId, discountValue);
        }

        if (e.target.classList.contains('apply-custom-discount')) {
            const ticketId = e.target.getAttribute('data-ticket-id');
            applyCustomDiscount(ticketId);
        }

        if (e.target.classList.contains('remove-discount')) {
            const ticketId = e.target.getAttribute('data-ticket-id');
            removeDiscountFromTicket(ticketId);
        }
    });

    // Event listener per input sconto personalizzato (invio con Enter)
    document.addEventListener('keydown', function(e) {
        if (e.target.classList.contains('custom-discount-value') && e.key === 'Enter') {
            const ticketId = e.target.getAttribute('data-ticket-id');
            applyCustomDiscount(ticketId);
        }
    });

    // Carica sconti salvati dal localStorage all'avvio
    loadSavedDiscountsFromStorage();

    console.log('✅ Sistema sconti UX inizializzato');
}

// Applica sconto a un ticket
function applyDiscountToTicket(ticketId, discountValue) {
    console.log(`💰 Applicando sconto ${discountValue}% al ticket ${ticketId}`);

    // Salva lo sconto nel sistema esistente
    updateTicketDiscount(ticketId, discountValue);

    // Aggiorna l'interfaccia
    updateDiscountDisplay(ticketId, discountValue);

    // Aggiorna immediatamente i prezzi nella tabella con lo sconto applicato
    updateTicketPriceDetails(ticketId);

    // Aggiorna i prezzi nella tabella con animazione
    updateTicketPricesWithAnimation(ticketId, discountValue);

    // Mostra tasto "Rimuovi sconto" se applicato uno sconto
    if (discountValue > 0) {
        showRemoveDiscountButton(ticketId);
    } else {
        hideRemoveDiscountButton(ticketId);
    }

    // Feedback visivo
    showDiscountAppliedFeedback(ticketId);

    // 🔥 AGGIUNTO: Aggiorna sempre i totali dopo l'applicazione dello sconto
    setTimeout(updateTotalsBar, 150);
}

// Applica sconto personalizzato
function applyCustomDiscount(ticketId) {
    const input = document.querySelector(`.custom-discount-value[data-ticket-id="${ticketId}"]`);
    if (!input) return;

    const discountValue = parseFloat(input.value);

    if (isNaN(discountValue) || discountValue < 0 || discountValue > 100) {
        showCustomDiscountError(input);
        return;
    }

    applyDiscountToTicket(ticketId, discountValue);
    input.value = ''; // Pulisce il campo dopo l'applicazione
}

// Rimuovi sconto da un ticket
function removeDiscountFromTicket(ticketId) {
    console.log(`❌ Rimuovendo sconto dal ticket ${ticketId}`);

    applyDiscountToTicket(ticketId, 0);
}

// Aggiorna il display dello sconto corrente
function updateDiscountDisplay(ticketId, discountValue) {
    const display = document.getElementById(`discount-display-${ticketId}`);
    if (display) {
        display.textContent = `${discountValue}%`;
        display.className = `current-discount-value fw-bold ${
            discountValue === 0 ? 'text-muted' :
            discountValue <= 10 ? 'text-success' :
            discountValue <= 20 ? 'text-warning' : 'text-danger'
        }`;
    }
}

// Aggiorna l'aspetto dei bottoni degli sconti
function updateDiscountButtonsUI(ticketId, activeDiscount) {
    // Rimuovi classe active da tutti i bottoni di questo ticket
    const buttons = document.querySelectorAll(`.discount-btn[data-ticket-id="${ticketId}"]`);
    buttons.forEach(btn => {
        const btnDiscount = parseFloat(btn.getAttribute('data-discount'));
        if (btnDiscount === activeDiscount && activeDiscount > 0) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Mostra il tasto "Rimuovi sconto"
function showRemoveDiscountButton(ticketId) {
    const removeBtn = document.querySelector(`.remove-discount[data-ticket-id="${ticketId}"]`);
    if (removeBtn) {
        removeBtn.style.display = 'block';
    }
}

// Nasconde il tasto "Rimuovi sconto"
function hideRemoveDiscountButton(ticketId) {
    const removeBtn = document.querySelector(`.remove-discount[data-ticket-id="${ticketId}"]`);
    if (removeBtn) {
        removeBtn.style.display = 'none';
    }
}

// Aggiorna i prezzi nella tabella con animazione
function updateTicketPricesWithAnimation(ticketId, discount) {
    const priceElements = document.querySelectorAll(`[data-ticket-id="${ticketId}"] .price-with-vat, [data-ticket-id="${ticketId}"] .price-no-vat, [data-ticket-id="${ticketId}"] .unit-price-value`);

    priceElements.forEach(el => {
        el.classList.add('price-discounted');
        setTimeout(() => {
            el.classList.remove('price-discounted');
        }, 600);
    });
}

// Feedback visivo quando viene applicato uno sconto
function showDiscountAppliedFeedback(ticketId) {
    const container = document.querySelector(`.discount-container[data-ticket-id="${ticketId}"]`);
    const tableRow = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);

    if (container) {
        container.style.transform = 'scale(1.02)';
        setTimeout(() => {
            container.style.transform = 'scale(1)';
        }, 200);
    }

    // Evidenzia la riga della tabella se è applicato uno sconto
    if (tableRow) {
        const discountValue = ticketDiscounts[ticketId] || 0;
        if (discountValue > 0) {
            tableRow.classList.add('discount-applied');
        } else {
            tableRow.classList.remove('discount-applied');
        }
    }
}

// Mostra errore per sconto personalizzato non valido
function showCustomDiscountError(input) {
    input.style.borderColor = '#dc3545';
    input.style.boxShadow = '0 0 0 0.2rem rgba(220, 53, 69, 0.25)';

    setTimeout(() => {
        input.style.borderColor = '';
        input.style.boxShadow = '';
    }, 2000);
}

// Carica sconti salvati dal localStorage all'avvio
function loadSavedDiscountsFromStorage() {
    console.log('🔄 Caricamento sconti salvati dal localStorage...');

    if (typeof ticketDiscounts !== 'undefined') {
        Object.keys(ticketDiscounts).forEach(ticketId => {
            const discount = ticketDiscounts[ticketId];
            if (discount > 0) {
                updateDiscountDisplay(ticketId, discount);
                updateDiscountButtonsUI(ticketId, discount);
                showRemoveDiscountButton(ticketId);

                // Aggiorna immediatamente i prezzi con lo sconto applicato
                updateTicketPriceDetails(ticketId);

                // Evidenzia la riga della tabella
                const tableRow = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
                if (tableRow) {
                    tableRow.classList.add('discount-applied');
                }
            }
        });

        // 🔥 AGGIUNTO: Aggiorna i totali dopo aver caricato tutti gli sconti
        setTimeout(updateTotalsBar, 150);
    }

    // Caricamento sconti completato
}

// ===== GESTIONE LISTINO DEDICATO =====
function getDedicatedListinoData(ticketId, lineId) {
    /**
     * Recupera i dati del listino dedicato dal localStorage
     */
    const listinoKey = `listino_imponibile_${ticketId}_${lineId}`;
    const stored = localStorage.getItem(listinoKey);

    if (stored) {
        try {
            const data = JSON.parse(stored);
            console.log(`💰 Dati listino dedicato trovati per ${ticketId}_${lineId}:`, data);
            return data;
        } catch (e) {
            console.error(`❌ Errore parsing dati listino dedicato per ${ticketId}_${lineId}:`, e);
            return null;
        }
    }

    return null;
}

function applyDedicatedListinoToLine(line, ticketId) {
    /**
     * Applica i dati del listino dedicato a una linea se disponibili
     */
    if (!line.id_linea_ticket) return line;

    const listinoData = getDedicatedListinoData(ticketId, line.id_linea_ticket);
    if (listinoData) {
        // Sovrascrivi l'imponibile senza IVA con il valore del listino dedicato
        line.ImporteSinIVASinDtoL = listinoData.imponibile_sin_iva;
        console.log(`🎯 Listino dedicato applicato: €${listinoData.imponibile_sin_iva.toFixed(2)} per linea ${line.id_linea_ticket}`);
    }

    return line;
}

// ===== BARRA TOTALI IN TEMPO REALE =====
// 🔥 ESPORTA updateTotalsBar NEL CONTESTO GLOBALE per compatibilità con altri file
window.updateTotalsBar = function() {
    /**
     * Calcola e aggiorna i totali nella barra verde in tempo reale
     */
    console.log('🔄 Aggiornamento barra totali...');

    let totalKg = 0;
    let totalPz = 0;
    let totalWithoutVat = 0;
    let totalWithVat = 0;

    // Itera attraverso tutti i ticket nella tabella
    const ticketRows = document.querySelectorAll('#ddtTicketTable tbody tr');

    ticketRows.forEach(row => {
        // Estrai i valori da ogni riga
        const quantityValueSpan = row.querySelector('.quantity-value');
        const priceNoVatSpan = row.querySelector('.price-no-vat');
        const priceWithVatSpan = row.querySelector('.price-with-vat');

        if (quantityValueSpan && priceNoVatSpan && priceWithVatSpan) {
            const quantityText = quantityValueSpan.textContent.trim();
            const priceNoVatText = priceNoVatSpan.textContent.replace('€', '').replace('--', '0').trim();
            const priceWithVatText = priceWithVatSpan.textContent.replace('€', '').replace('--', '0').trim();

            // Gestisci quantità miste (kg + pz)
            if (quantityText.includes('+')) {
                const parts = quantityText.split('+');
                if (parts.length === 2) {
                    const kgPart = parseFloat(parts[0].trim()) || 0;
                    const pzPart = parseFloat(parts[1].trim()) || 0;
                    totalKg += kgPart;
                    totalPz += pzPart;
                }
            } else {
                // Determina se è kg o pz basandosi sulle icone
                const quantityUnitSpan = row.querySelector('.quantity-unit');
                const hasWeightIcon = quantityUnitSpan && quantityUnitSpan.innerHTML.includes('fa-weight');
                const hasCubesIcon = quantityUnitSpan && quantityUnitSpan.innerHTML.includes('fa-cubes');

                const quantity = parseFloat(quantityText.replace('--', '0')) || 0;

                if (hasWeightIcon && !hasCubesIcon) {
                    totalKg += quantity;
                } else if (hasCubesIcon && !hasWeightIcon) {
                    totalPz += quantity;
                } else {
                    // Default: assumi pezzi se non specificato
                    totalPz += quantity;
                }
            }

            // Gestisci prezzi con sconto (testo barrato)
            let priceNoVat = 0;
            let priceWithVat = 0;

            // Se c'è testo barrato, prendi il prezzo scontato (quello in bold)
            if (priceNoVatSpan.innerHTML.includes('line-through')) {
                const match = priceNoVatSpan.innerHTML.match(/<strong>€([0-9.,]+)<\/strong>/);
                if (match) {
                    priceNoVat = parseFloat(match[1].replace(',', '.')) || 0;
                }
            } else {
                priceNoVat = parseFloat(priceNoVatText.replace(',', '.')) || 0;
            }

            if (priceWithVatSpan.innerHTML.includes('line-through')) {
                const match = priceWithVatSpan.innerHTML.match(/<strong>€([0-9.,]+)<\/strong>/);
                if (match) {
                    priceWithVat = parseFloat(match[1].replace(',', '.')) || 0;
                }
            } else {
                priceWithVat = parseFloat(priceWithVatText.replace(',', '.')) || 0;
            }

            totalWithoutVat += priceNoVat;
            totalWithVat += priceWithVat;
        }
    });

    // Aggiorna gli elementi della barra con animazione
    const elements = [
        { id: 'total-quantity-kg', value: totalKg, format: 'decimal', decimals: 3, suffix: 'kg' },
        { id: 'total-quantity-pz', value: totalPz, format: 'integer', decimals: 0, suffix: 'pz' },
        { id: 'total-without-vat', value: totalWithoutVat, format: 'currency', decimals: 2, prefix: '€' },
        { id: 'total-with-vat', value: totalWithVat, format: 'currency', decimals: 2, prefix: '€' }
    ];

    elements.forEach(element => {
        const elementDiv = document.getElementById(element.id);
        if (elementDiv) {
            const valueSpan = elementDiv.querySelector('.value');

            if (valueSpan) {
                let formattedValue = '';

                if (element.format === 'currency') {
                    formattedValue = element.prefix + element.value.toFixed(element.decimals);
                } else if (element.format === 'decimal') {
                    formattedValue = element.value.toFixed(element.decimals);
                } else {
                    formattedValue = Math.round(element.value).toString();
                }

                // Applica animazione se il valore è cambiato
                if (valueSpan.textContent !== formattedValue) {
                    elementDiv.classList.add('updating');
                    valueSpan.textContent = formattedValue;

                    // Rimuovi l'animazione dopo che è completata
                    setTimeout(() => {
                        elementDiv.classList.remove('updating');
                    }, 300);
                }
            }
        }
    });

    console.log('✅ Barra totali aggiornata:', {
        quantitaKg: totalKg.toFixed(3),
        quantitaPz: Math.round(totalPz),
        totaleSenzaIva: totalWithoutVat.toFixed(2),
        totaleConIva: totalWithVat.toFixed(2)
    });
};

// ===== CHIAMATA ALL'AGGIORNAMENTO TOTALI =====
// Aggiungi chiamata alla funzione updateTotalsBar dopo ogni aggiornamento dei prezzi
const originalUpdateTicketPriceDetails = updateTicketPriceDetails;
updateTicketPriceDetails = function(ticketId) {
    originalUpdateTicketPriceDetails(ticketId);
    // Aggiorna i totali dopo un breve delay per permettere al DOM di aggiornarsi
    setTimeout(updateTotalsBar, 100);
};

const originalUpdateAllTicketsPriceDetails = updateAllTicketsPriceDetails;
updateAllTicketsPriceDetails = function() {
    originalUpdateAllTicketsPriceDetails();
    // Aggiorna i totali dopo un breve delay per permettere al DOM di aggiornarsi
    setTimeout(updateTotalsBar, 200);
};

// Inizializza il sistema quando il DOM è pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDiscountSystem);
} else {
    initializeDiscountSystem();
}

// ===== GESTIONE MODIFICHE DDT =====

// Funzione per salvare automaticamente le modifiche nel localStorage durante la modifica
function saveDDTModificationsToStorage() {
    const ddtId = getDDTIdFromURL();
    if (!ddtId) return;

    const modifications = {
        ddt_id: ddtId,
        timestamp: new Date().toISOString(),
        lines: []
    };

    // Raccogli tutte le linee modificate dalla tabella
    document.querySelectorAll('#ddtTicketTable tbody tr').forEach(row => {
        const ticketId = row.getAttribute('data-ticket-id');
        if (!ticketId) return;

        const line = {
            ticket_id: ticketId,
            descripcion: row.querySelector('td[data-label="Prodotti"] .text-truncate')?.textContent?.trim() || '',
            peso: parseFloat(row.querySelector('.quantity-value')?.textContent?.replace(',', '.')) || 0,
            precio: parseFloat(row.querySelector('.unit-price-value')?.textContent?.replace('€', '').replace(',', '.')) || 0,
            iva: parseInt(row.querySelector('.vat-rate-display')?.textContent?.replace('%', '')) || 22,
            importe: parseFloat(row.querySelector('.price-with-vat')?.textContent?.replace('€', '').replace(',', '.')) || 0,
            texto_lote: row.querySelector('.lot-text-display')?.textContent?.trim() || '',
            fecha_caducidad: row.querySelector('.expiry-date-display')?.textContent?.trim() || ''
        };

        modifications.lines.push(line);
    });

    // Salva nel localStorage con chiave specifica per il DDT
    const storageKey = `ddt_modifications_${ddtId}`;
    localStorage.setItem(storageKey, JSON.stringify(modifications));

    console.log('💾 Modifiche DDT salvate nel localStorage:', modifications);
}

// Funzione per caricare le modifiche dal localStorage
function loadDDTModificationsFromStorage() {
    const ddtId = getDDTIdFromURL();
    if (!ddtId) return null;

    const storageKey = `ddt_modifications_${ddtId}`;
    const stored = localStorage.getItem(storageKey);

    if (stored) {
        try {
            const modifications = JSON.parse(stored);
            console.log('📦 Modifiche DDT caricate dal localStorage:', modifications);
            return modifications;
        } catch (e) {
            console.error('❌ Errore parsing modifiche DDT dal localStorage:', e);
            return null;
        }
    }

    return null;
}

// Funzione per ottenere l'ID del DDT
function getDDTIdFromURL() {
    // Prima cerca nei serverData se disponibile
    if (typeof serverData !== 'undefined' && serverData && serverData.DDT_ID) {
        return serverData.DDT_ID;
    }

    // Poi cerca nei parametri dell'URL
    const urlParams = new URLSearchParams(window.location.search);
    const urlDdtId = urlParams.get('ddt_id');

    if (urlDdtId) return urlDdtId;

    // Cerca nell'HTML per elementi che potrebbero contenere il ddt_id
    const ddtIdElement = document.querySelector('[data-ddt-id]');
    if (ddtIdElement) {
        return ddtIdElement.getAttribute('data-ddt-id');
    }

    // Estrai dall'URL della pagina corrente se siamo nella pagina detail
    const pathMatch = window.location.pathname.match(/\/ddt\/(\d+)/);
    if (pathMatch) {
        return pathMatch[1];
    }

    return null;
}

// Funzione per salvare le modifiche del DDT nel database
async function saveDDTModifications() {
    const ddtId = getDDTIdFromURL();
    if (!ddtId) {
        alert('ID DDT non trovato');
        return;
    }

    // Mostra loading
    const saveBtn = document.getElementById('save-ddt-modifications');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Salvataggio...';
    saveBtn.disabled = true;

    try {
        // Raccogli le modifiche dal localStorage
        const modifications = loadDDTModificationsFromStorage();
        if (!modifications) {
            alert('Nessuna modifica trovata da salvare');
            return;
        }

        // Invia le modifiche al server
        const response = await fetch(`/ddt/api/save_modifications/${ddtId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
            },
            body: JSON.stringify(modifications)
        });

        const result = await response.json();

        if (result.success) {
            // Pulisci il localStorage dopo il salvataggio riuscito
            const storageKey = `ddt_modifications_${ddtId}`;
            localStorage.removeItem(storageKey);
            localStorage.removeItem('ddt_ticket_modifications');
            localStorage.removeItem('ddt_manual_tickets');
            localStorage.removeItem('ddt_added_existing_tickets');
            localStorage.removeItem('ddt_ticket_discounts');
            localStorage.removeItem('ddt_selected_tickets_temp');

            // Mostra messaggio di successo
            alert('Modifiche salvate con successo!');

            // Reindirizza al dettaglio del DDT modificato invece di ricaricare
            window.location.href = `/ddt/${ddtId}`;
        } else {
            alert('Errore durante il salvataggio: ' + (result.message || 'Errore sconosciuto'));
        }

    } catch (error) {
        console.error('❌ Errore salvataggio modifiche DDT:', error);
        alert('Errore durante il salvataggio delle modifiche');
    } finally {
        // Ripristina il pulsante
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    }
}

// Funzione per applicare le modifiche salvate nel localStorage alla tabella
function applyDDTModificationsFromStorage() {
    const modifications = loadDDTModificationsFromStorage();
    if (!modifications || !modifications.lines) return;

    modifications.lines.forEach(line => {
        // Trova la riga corrispondente nella tabella
        const row = document.querySelector(`#ddtTicketTable tbody tr[data-ticket-id="${line.ticket_id}"]`);
        if (row) {
            // Aggiorna i valori nella riga
            const quantityElement = row.querySelector('.quantity-value');
            const priceElement = row.querySelector('.unit-price-value');
            const vatElement = row.querySelector('.vat-rate-display');
            const totalElement = row.querySelector('.price-with-vat');

            if (quantityElement) quantityElement.textContent = line.peso.toFixed(3);
            if (priceElement) priceElement.textContent = `€${line.precio.toFixed(2)}`;
            if (vatElement) vatElement.textContent = `${line.iva}%`;
            if (totalElement) totalElement.textContent = `€${line.importe.toFixed(2)}`;
        }
    });

    console.log('✅ Modifiche DDT applicate dalla cache');
}

// Inizializzazione per la modalità modifica DDT
function initializeDDTModifyMode() {
    // Verifica se siamo in modalità modifica
    let fromModify = false;

    // Prima verifica nei serverData se disponibili
    if (typeof serverData !== 'undefined' && serverData && serverData.FROM_MODIFY) {
        fromModify = serverData.FROM_MODIFY;
    }

    // Altrimenti cerca nell'URL
    if (!fromModify) {
        const urlParams = new URLSearchParams(window.location.search);
        fromModify = urlParams.get('from_modify') === 'true';
    }

    // Verifica anche se esiste il pulsante di salvataggio modifiche
    if (!fromModify) {
        const saveBtn = document.getElementById('save-ddt-modifications');
        if (saveBtn) {
            fromModify = true;
        }
    }

    if (fromModify) {
        console.log('🔧 Modalità modifica DDT attivata');

        // Applica le modifiche salvate dal localStorage
        setTimeout(applyDDTModificationsFromStorage, 500);

        // Configura il salvataggio automatico ogni 30 secondi
        setInterval(saveDDTModificationsToStorage, 30000);

        // Aggiungi event listener per il pulsante di salvataggio
        const saveBtn = document.getElementById('save-ddt-modifications');
        if (saveBtn) {
            saveBtn.addEventListener('click', saveDDTModifications);
            console.log('✅ Event listener aggiunto per il pulsante di salvataggio');
        }

        // Salva automaticamente quando si modificano i valori negli input della modale di modifica
        document.addEventListener('input', function(e) {
            if (e.target.matches('#editLineModal input, #editLineModal select, #editLineModal textarea')) {
                setTimeout(saveDDTModificationsToStorage, 1000); // Salva dopo 1 secondo
            }
        });

        // Salva anche quando si chiude la modale di modifica
        document.addEventListener('hidden.bs.modal', function(e) {
            if (e.target.id === 'editLineModal') {
                setTimeout(saveDDTModificationsToStorage, 500);
            }
        });

        console.log('🔧 Sistema di salvataggio automatico configurato');
    }
}

// Inizializza la modalità modifica quando il DOM è pronto
document.addEventListener('DOMContentLoaded', function() {
    // Attendi un po' per assicurarsi che tutto sia caricato
    setTimeout(initializeDDTModifyMode, 1000);
});

console.log('✅ DDT Preview JS caricato completamente');
console.log('🔧 Debug helper disponibili in window.debugDDTPreview');