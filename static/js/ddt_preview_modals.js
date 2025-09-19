/**
 * DDT Preview Modals - Gestione modali per preview DDT
 */

// Funzione per arrotondamento tradizionale (0.04 per difetto, 0.05 per eccesso)
function roundCommercial(value, decimals = 2) {
    // Arrotondamento tradizionale: 0.04 → per difetto, 0.05 → per eccesso
    const factor = Math.pow(10, decimals);
    return Math.round(value * factor) / factor;
}

// Funzione di test per mostrare esempi di arrotondamento
function testRoundingExamples() {
    console.log('🧮 ESEMPI ARROTONDAMENTO COMMERCIALE:');
    console.log('Valore → Arrotondato (massimo 2 decimali)');
    console.log('─────────────────────────────────────');

    const examples = [
        10.123,   // → 10.12 (3 < 5, per difetto)
        10.125,   // → 10.13 (5 ≥ 5, per eccesso)
        10.134,   // → 10.13 (4 < 5, per difetto)
        10.135,   // → 10.14 (5 ≥ 5, per eccesso)
        10.144,   // → 10.14 (4 < 5, per difetto)
        10.145,   // → 10.15 (5 ≥ 5, per eccesso)
        10.154,   // → 10.15 (4 < 5, per difetto)
        10.155,   // → 10.16 (5 ≥ 5, per eccesso)
        10.164,   // → 10.16 (4 < 5, per difetto)
        10.165    // → 10.17 (5 ≥ 5, per eccesso)
    ];

    examples.forEach(example => {
        const rounded = roundCommercial(example, 2);
        console.log(`${example.toFixed(3)} → ${rounded.toFixed(2)}`);
    });

    console.log('─────────────────────────────────────');
    console.log('💡 Regola: terzo decimale < 5 → per difetto, ≥ 5 → per eccesso');
}

// Esponi la funzione di test globalmente per debug
window.testRoundingExamples = testRoundingExamples;

// ===== GESTIONE MODAL MODIFICA LINEA =====
// Funzione per calcolare l'importo totale compreso di IVA
function calculateTotalWithVAT(lineData, ticketData) {
    const peso = parseFloat(lineData.peso) || 0;

    // Determina l'aliquota IVA
    let ivaRate = 0.04; // Default 4%
    if (lineData.porcentaje_iva) {
        ivaRate = parseInt(lineData.porcentaje_iva) / 100;
    } else if (lineData.iva) {
        ivaRate = parseInt(lineData.iva) / 100;
    } else if (lineData.id_iva) {
        switch (parseInt(lineData.id_iva)) {
            case 0: ivaRate = 0.00; break; // 0% - Esente IVA
            case 1: ivaRate = 0.04; break;
            case 2: ivaRate = 0.10; break;
            case 3: ivaRate = 0.22; break;
            default: ivaRate = 0.04; break;
        }
    }

    // ✅ CORREZIONE: Usiamo direttamente il prezzo CON IVA dal database
    const precioConIVA = parseFloat(lineData.precio) || 0;

    // ✅ CORREZIONE: Tutti i prezzi sono CON IVA, calcolo semplificato
    const totalWithVAT = peso * precioConIVA;
    console.log(`💰 Calcolo totale semplificato: €${precioConIVA.toFixed(2)} × ${peso} = €${totalWithVAT.toFixed(2)} (prezzo con IVA)`);

    return totalWithVAT;
}

function openEditLineModal(ticketId, lineId) {
    console.log('📝 Apertura modale modifica linea:', ticketId, lineId);

    // Trova i dati della linea
    const ticketData = previewData[ticketId];
    if (!ticketData) {
        showNotification('Dati del ticket non trovati', 'danger');
        return;
    }

    const lineData = ticketData.lines.find(line => line.id_linea_ticket == lineId);
    if (!lineData) {
        showNotification('Dati della linea non trovati', 'danger');
        return;
    }

    // Popola il modale
    populateEditLineModal(ticketData, lineData, ticketId, lineId);

    // Apri il modale
    const modal = new bootstrap.Modal(document.getElementById('editLineModal'));
    modal.show();

    // Setup event listeners del modale
    setTimeout(() => {
        setupModalEventListeners();
    }, 100);
}

function populateEditLineModal(ticketData, lineData, ticketId, lineId) {
    // Popola l'intestazione del modale
    document.getElementById('edit-ticket-number').textContent = ticketData.ticket.NumTicket || ticketId;
    document.getElementById('edit-product-description').textContent = lineData.descripcion || 'Prodotto';
    document.getElementById('edit-product-code').textContent = lineData.id_articulo || '--';
    document.getElementById('edit-product-type').textContent = lineData.comportamiento == 1 ? 'Peso (kg)' : 'Unità (pz)';
    document.getElementById('edit-current-price').textContent = (parseFloat(lineData.precio) || 0).toFixed(2);
    
    // Popola i campi nascosti
    document.getElementById('edit-ticket-id').value = ticketId;
    document.getElementById('edit-line-id').value = lineId;
    document.getElementById('edit-id-articulo').value = lineData.id_articulo || '';
    document.getElementById('edit-descripcion').value = lineData.descripcion || '';
    
    // Popola i campi di visualizzazione (read-only)
    document.getElementById('edit-id-articulo-display').textContent = lineData.id_articulo || '--';
    document.getElementById('edit-descripcion-display').textContent = lineData.descripcion || '--';
    
    // Popola i campi modificabili
    document.getElementById('edit-peso').value = lineData.peso || '';

    // ✅ CORREZIONE: Il campo "Prezzo Unitario" contiene il prezzo CON IVA dal database
    let precioUnitarioConIVA = lineData.precio || 0;
    console.log(`💰 Popolamento modale: usando prezzo CON IVA dal database €${precioUnitarioConIVA.toFixed(2)}`);

    document.getElementById('edit-precio').value = precioUnitarioConIVA.toFixed(2);

    // ✅ CORREZIONE: Per ticket esistenti dal modale, usa sempre il calcolo con IVA
    let importeConIVA;
    if (lineData.importe_con_iva !== undefined && lineData.importe_con_iva !== null) {
        // Usa il valore con IVA se disponibile
        importeConIVA = parseFloat(lineData.importe_con_iva);
        console.log(`💰 Popolamento modale: usando importo_con_iva dal database €${importeConIVA.toFixed(2)}`);
    } else if (lineData.peso && lineData.precio_con_iva) {
        // Calcola con IVA se abbiamo peso e prezzo con IVA
        importeConIVA = parseFloat(lineData.peso) * parseFloat(lineData.precio_con_iva);
        console.log(`💰 Popolamento modale: calcolato con IVA (peso × precio_con_iva) €${importeConIVA.toFixed(2)}`);
    } else if (lineData.peso && lineData.precio) {
        // Fallback: usa prezzo come con IVA
        importeConIVA = parseFloat(lineData.peso) * parseFloat(lineData.precio);
        console.log(`💰 Popolamento modale: calcolato con prezzo disponibile €${importeConIVA.toFixed(2)}`);
    } else {
        // Ultimo fallback
        importeConIVA = parseFloat(lineData.importe) || 0;
        console.log(`💰 Popolamento modale: usando importo di fallback €${importeConIVA.toFixed(2)}`);
    }
    document.getElementById('edit-importe').value = importeConIVA.toFixed(2);
    document.getElementById('edit-comportamiento').value = lineData.comportamiento || '0';

    // ✅ CORREZIONE TICKET MANUALI: Recupera texto_lote dal localStorage per ticket manuali
    let textoLoteValue = '';
    const isManualTicket = ticketData.ticket && (ticketData.ticket.is_manual || ticketData.ticket.id_ticket < 0);

    if (isManualTicket) {
        // Per ticket manuali, recupera dal localStorage
        try {
            const stored = localStorage.getItem('ddt_manual_tickets');
            if (stored) {
                const manualTickets = JSON.parse(stored);
                // Trova il ticket manuale corrispondente
                const manualTicket = manualTickets.find(t => t.id_ticket == ticketId);
                if (manualTicket && manualTicket.lines) {
                    // Trova la linea corrispondente
                    const manualLine = manualTicket.lines.find(l => l.id_linea_ticket == lineId);
                    if (manualLine) {
                        // Il texto_lote è salvato nel campo 'lotto' per i ticket manuali
                        textoLoteValue = manualLine.lotto || '';
                        console.log(`📦 Ticket manuale ${ticketId}: recuperato texto_lote "${textoLoteValue}" dal localStorage`);
                    }
                }
            }
        } catch (error) {
            console.error('❌ Errore nel recupero texto_lote dal localStorage:', error);
        }
    } else {
        // Per ticket normali, usa i dati dal database
        textoLoteValue = lineData.texto_lote || '';
        console.log(`📊 Ticket normale ${ticketId}: usando texto_lote dal database "${textoLoteValue}"`);
    }

    document.getElementById('edit-texto-lote').value = textoLoteValue;

    // ✅ CORREZIONE MAPPATURA IVA: Converti valori backend in valori frontend
    // Backend:  4=Esente, 1=4%, 2=10%, 3=22%
    // Frontend: 0=Esente, 4=4%, 10=10%, 22=22%
    let ivaValue = '4'; // Default 4%
    if (lineData.id_iva !== undefined) {
        // Usa id_iva se disponibile (valore backend)
        if (lineData.id_iva === 4) ivaValue = '0';      // Esente IVA (id_iva = 4)
        else if (lineData.id_iva === 1) ivaValue = '4';  // 4%
        else if (lineData.id_iva === 2) ivaValue = '10'; // 10%
        else if (lineData.id_iva === 3) ivaValue = '22'; // 22%
    } else {
        // Fallback al vat_rate
        const vatRate = lineData.vat_rate || 0;
        if (vatRate === 0.04) ivaValue = '4';
        else if (vatRate === 0.10) ivaValue = '10';
        else if (vatRate === 0.22) ivaValue = '22';
        else if (vatRate === 0) ivaValue = '0';
    }
    document.getElementById('edit-iva').value = ivaValue;
    
    // Gestisci la data di scadenza
    if (lineData.fecha_caducidad) {
        const date = new Date(lineData.fecha_caducidad);
        const dateString = date.toISOString().split('T')[0];
        document.getElementById('edit-fecha-caducidad').value = dateString;
    } else {
        document.getElementById('edit-fecha-caducidad').value = '';
    }
    
    // Aggiorna l'unità di misura
    updatePesoUnit();
}

function setupModalEventListeners() {
    console.log('🔗 Setup event listeners modale...');
    
    // Rimuovi event listeners esistenti per evitare duplicati
    const saveBtn = document.getElementById('save-line-changes');
    if (saveBtn) {
        const newSaveBtn = saveBtn.cloneNode(true);
        saveBtn.parentNode.replaceChild(newSaveBtn, saveBtn);
        
        newSaveBtn.addEventListener('click', saveLineChanges);
    }
    
    // Event listeners per calcoli automatici
    const pesoEl = document.getElementById('edit-peso');
    const precioEl = document.getElementById('edit-precio');
    const importeEl = document.getElementById('edit-importe');
    const ivaEl = document.getElementById('edit-iva');
    const comportamientoEl = document.getElementById('edit-comportamiento');

    if (pesoEl) {
        pesoEl.addEventListener('input', calculateLineTotal);
    }
    if (precioEl) {
        precioEl.addEventListener('input', calculateLineTotal);
    }
    if (importeEl) {
        importeEl.addEventListener('input', calculateUnitPrice);
    }
    if (ivaEl) {
        // ✅ AGGIUNTO: Event listener per cambio IVA
        ivaEl.addEventListener('change', calculateLineTotal);
    }
    if (comportamientoEl) {
        comportamientoEl.addEventListener('change', updatePesoUnit);
    }
}

// ===== FUNZIONI CALCOLO =====
function updatePesoUnit() {
    const comportamiento = document.getElementById('edit-comportamiento').value;
    const unitDisplay = document.getElementById('peso-unit-display');
    
    if (comportamiento == '1') {
        unitDisplay.textContent = 'kg';
    } else {
        unitDisplay.textContent = 'pz';
    }
}

function calculateLineTotal() {
    const peso = parseFloat(document.getElementById('edit-peso').value) || 0;
    const precio = parseFloat(document.getElementById('edit-precio').value) || 0;
    const ivaValueRaw = parseInt(document.getElementById('edit-iva').value);
    const ivaValue = (ivaValueRaw !== null && !isNaN(ivaValueRaw)) ? ivaValueRaw : 4;

    // ✅ CORREZIONE IVA 0%: Per IVA 0%, prezzo con IVA = prezzo senza IVA
    if (ivaValue === 0) {
        // IVA 0% - Esente IVA: prezzo rimane invariato
        const total = peso * precio;
        document.getElementById('edit-importe').value = total.toFixed(2);
        console.log(`🧮 IVA 0% - Esente IVA: ${peso} × €${precio.toFixed(2)} = €${total.toFixed(2)} (prezzo invariato)`);
    } else {
        // IVA > 0%: Il prezzo è CON IVA, calcoliamo direttamente peso × prezzo
        const total = peso * precio;
        document.getElementById('edit-importe').value = total.toFixed(2);
        console.log(`🧮 IVA ${ivaValue}%: ${peso} × €${precio.toFixed(2)} = €${total.toFixed(2)} (con IVA)`);
    }
}

function calculateUnitPrice() {
    const peso = parseFloat(document.getElementById('edit-peso').value) || 0;
    const importe = parseFloat(document.getElementById('edit-importe').value) || 0;
    const ivaValueRaw = parseInt(document.getElementById('edit-iva').value);
    const ivaValue = (ivaValueRaw !== null && !isNaN(ivaValueRaw)) ? ivaValueRaw : 4;

    if (peso > 0) {
        // ✅ CORREZIONE IVA 0%: Per IVA 0%, prezzo unitario rimane invariato
        if (ivaValue === 0) {
            // IVA 0% - Esente IVA: prezzo unitario rimane invariato
            const precio = importe / peso;
            document.getElementById('edit-precio').value = precio.toFixed(2);
            console.log(`🧮 IVA 0% - Prezzo unitario: €${importe.toFixed(2)} ÷ ${peso} = €${precio.toFixed(2)} (invariato)`);
        } else {
            // IVA > 0%: L'importo è CON IVA, calcoliamo prezzo unitario direttamente
            const precio = importe / peso;
            document.getElementById('edit-precio').value = precio.toFixed(2);
            console.log(`🧮 IVA ${ivaValue}% - Prezzo unitario: €${importe.toFixed(2)} ÷ ${peso} = €${precio.toFixed(2)} (con IVA)`);
        }
    }
}

function saveLineChanges() {
    const btn = document.getElementById('save-line-changes');
    const originalHTML = btn.innerHTML;
    
    // Mostra loading
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Salvataggio...';
    btn.disabled = true;
    
    // Raccogli i dati del form
    const peso = parseFloat(document.getElementById('edit-peso').value) || 0;
    const precio = parseFloat(document.getElementById('edit-precio').value) || 0;
    const importeWithVAT = parseFloat(document.getElementById('edit-importe').value) || 0;
    const ivaValue = parseInt(document.getElementById('edit-iva').value);
    const finalIvaValue = (ivaValue !== null && !isNaN(ivaValue)) ? ivaValue : 4;

    // ✅ CORREZIONE MAPPATURA IVA: Converti valori frontend in valori backend
    // Frontend: 0=Esente, 4=4%, 10=10%, 22=22%
    // Backend:  4=Esente, 1=4%, 2=10%, 3=22%
    let backendIvaValue = finalIvaValue;
    if (finalIvaValue === 4) backendIvaValue = 1;      // 4% → id_iva = 1
    else if (finalIvaValue === 10) backendIvaValue = 2; // 10% → id_iva = 2
    else if (finalIvaValue === 22) backendIvaValue = 3; // 22% → id_iva = 3
    else if (finalIvaValue === 0) backendIvaValue = 4;  // 0% → id_iva = 4 (Esente IVA)

    const ivaRate = finalIvaValue / 100;

    // ✅ CORREZIONE COMPLETA: Calcolo valori con e senza IVA
    // I valori nel modale sono CON IVA, dobbiamo calcolare entrambi i valori
    const precioWithVAT = precio; // Prezzo unitario CON IVA (dal modale)
    const importeWithVATFinal = importeWithVAT; // Importo totale CON IVA (dal modale)

    // Calcola prezzo SENZA IVA e importo SENZA IVA
    let precioSinIVA = precioWithVAT;
    let importeSinIVA = importeWithVATFinal;

    // Per IVA > 0%, calcola il prezzo senza IVA dividendo per (1 + aliquota IVA)
    if (finalIvaValue > 0) {
        precioSinIVA = precioWithVAT / (1 + ivaRate);
        importeSinIVA = importeWithVATFinal / (1 + ivaRate);
    }
    // Per IVA = 0% (Esente IVA), il prezzo rimane invariato

    // Applica arrotondamento commerciale ai valori senza IVA (massimo 2 decimali)
    const precioSinIVABefore = precioSinIVA;
    const importeSinIVABefore = importeSinIVA;

    precioSinIVA = roundCommercial(precioSinIVA, 2);
    importeSinIVA = roundCommercial(importeSinIVA, 2);

    console.log(`💾 Salvataggio valori con e senza IVA (arrotondati commercialmente):`);
    console.log(`   - Prezzo unitario CON IVA: €${precioWithVAT.toFixed(2)}`);
    console.log(`   - Prezzo unitario SENZA IVA: €${precioSinIVABefore.toFixed(6)} → €${precioSinIVA.toFixed(2)} (arrotondato)`);
    console.log(`   - Importo totale CON IVA: €${importeWithVATFinal.toFixed(2)}`);
    console.log(`   - Importo totale SENZA IVA: €${importeSinIVABefore.toFixed(6)} → €${importeSinIVA.toFixed(2)} (arrotondato)`);
    console.log(`   - IVA: Frontend=${finalIvaValue} → Backend=${backendIvaValue} (${backendIvaValue === 4 ? 'Esente IVA' : (ivaRate * 100).toFixed(0) + '%'})`);
    console.log(`   - Arrotondamento: 0.04→per difetto, 0.05→per eccesso (massimo 2 decimali)`);

    // 🔥 CALCOLO IMPONIBILE SENZA IVA PER DATABASE
    // Questo valore verrà salvato nel campo ImporteSinIVASinDtoL della tabella dat_ticket_linea
    let importeSinIVASinDtoL;

    // Verifica se il cliente ha un listino dedicato per gestire il calcolo corretto
    const hasDedicatedListino = window.hasDedicatedListino || false;
    const ticketId = document.getElementById('edit-ticket-id').value;

    if (hasDedicatedListino) {
        // Per clienti con listino dedicato, salva il valore calcolato senza IVA nel localStorage
        // e usa quel valore come imponibile senza IVA
        const listinoKey = `listino_imponibile_${ticketId}_${document.getElementById('edit-line-id').value}`;

        // Il valore senza IVA è già calcolato in precioSinIVA
        importeSinIVASinDtoL = precioSinIVA * peso;

        // Salva nel localStorage per riferimento futuro
        const listinoData = {
            ticket_id: ticketId,
            line_id: document.getElementById('edit-line-id').value,
            imponibile_sin_iva: importeSinIVASinDtoL,
            peso: peso,
            precio_sin_iva_unitario: precioSinIVA,
            timestamp: new Date().toISOString()
        };

        localStorage.setItem(listinoKey, JSON.stringify(listinoData));
        console.log(`💾 Listino dedicato: salvato imponibile senza IVA €${importeSinIVASinDtoL.toFixed(2)} in localStorage`);
    } else {
        // Per clienti normali, usa il calcolo standard
        importeSinIVASinDtoL = precioSinIVA * peso;
    }

    const formData = {
        ticket_id: document.getElementById('edit-ticket-id').value,
        line_id: document.getElementById('edit-line-id').value,
        id_articulo: document.getElementById('edit-id-articulo').value,
        descripcion: document.getElementById('edit-descripcion').value,
        peso: peso,
        precio: precioWithVAT, // Salva prezzo CON IVA nel database
        precio_sin_iva: precioSinIVA, // ✅ AGGIUNTO: Salva prezzo SENZA IVA nel database
        importe: importeWithVATFinal, // Salva importo totale CON IVA nel database
        ImporteSinIVASinDtoL: importeSinIVASinDtoL, // 🔥 CORRETTO: Campo database corretto
        comportamiento: parseInt(document.getElementById('edit-comportamiento').value) || 0,
        fecha_caducidad: document.getElementById('edit-fecha-caducidad').value || null,
        texto_lote: document.getElementById('edit-texto-lote').value || null,
        iva: backendIvaValue  // Usa valore convertito per backend
    };

    console.log('📊 DATI FORM FINALI:');
    console.log(`   - Peso: ${peso}`);
    console.log(`   - Prezzo con IVA: €${precioWithVAT.toFixed(2)}`);
    console.log(`   - Prezzo senza IVA: €${precioSinIVA.toFixed(2)}`);
    console.log(`   - Importo totale: €${importeWithVATFinal.toFixed(2)} (CON IVA)`);
    console.log(`   - 🔥 IMPONIBILE SENZA IVA (ImporteSinIVASinDtoL): €${importeSinIVASinDtoL.toFixed(2)} (per database)`);
    console.log(`   - IVA: ${finalIvaValue}% (Backend: ${backendIvaValue})`);
    console.log(`   - Listino dedicato: ${hasDedicatedListino ? 'SÌ' : 'NO'}`);
    
    // Validazione base
    if (!formData.descripcion.trim()) {
        showNotification('La descrizione è obbligatoria', 'warning');
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        return;
    }
    
    if (formData.peso <= 0) {
        showNotification('Il peso/quantità deve essere maggiore di zero', 'warning');
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        return;
    }
    
    if (formData.precio <= 0) {
        showNotification('Il prezzo deve essere maggiore di zero', 'warning');
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        return;
    }

    // Mappa dei campi dal form ai campi dell'API
    const fieldMapping = {
        'peso': 'peso_quantita',
        'precio': 'prezzo_unitario',
        'importe': 'prezzo_totale',
        'fecha_caducidad': 'data_scadenza',
        'descripcion': 'descrizione',
        'iva': 'id_iva',
        'comportamiento': 'comportamiento',
        'texto_lote': 'texto_lote',
        'precio_sin_iva': 'precio_sin_iva',
        'ImporteSinIVASinDtoL': 'ImporteSinIVASinDtoL'  // 🔥 CORRETTO: Campo database corretto
    };

    // Prepara le chiamate API per ogni campo modificato
    const apiCalls = [];
    
    // Tutti i campi supportati dall'API
    // Il campo 'importe' deve SEMPRE essere inviato perché contiene il totale calcolato
    const fieldsToUpdate = ['peso', 'precio', 'importe', 'fecha_caducidad', 'descripcion', 'iva', 'comportamiento', 'texto_lote', 'precio_sin_iva', 'ImporteSinIVASinDtoL'];

    console.log('📋 CAMPI DA AGGIORNARE:', fieldsToUpdate);
    
    fieldsToUpdate.forEach(fieldKey => {
        if (formData[fieldKey] !== undefined && formData[fieldKey] !== null) {
            const apiField = fieldMapping[fieldKey] || fieldKey;

            // Logging specifico per campo IVA
            if (fieldKey === 'iva') {
                console.log(`📤 CREAZIONE CHIAMATA API IVA: fieldKey='${fieldKey}', apiField='${apiField}', value='${formData[fieldKey]}'`);
            }

            // Logging specifico per campo importo
            if (fieldKey === 'importe') {
                console.log(`💰 CHIAMATA API IMPORTO: fieldKey='${fieldKey}', apiField='${apiField}', value='${formData[fieldKey]}' (totale con IVA)`);
            }

            console.log(`📤 CAMPO ${fieldKey} → ${apiField}: ${formData[fieldKey]}`);

            apiCalls.push({
                ticket_id: formData.ticket_id,
                line_id: formData.line_id,
                field: apiField,
                value: formData[fieldKey]
            });
        } else {
            console.warn(`⚠️ CAMPO ${fieldKey} NON VALIDO: ${formData[fieldKey]}`);
        }
    });
    
    console.log('📤 Invio chiamate API:', apiCalls);
    
    // Esegui tutte le chiamate API in parallelo
    Promise.all(apiCalls.map(callData => {
        // Logging specifico per chiamata IVA
        if (callData.field === 'id_iva') {
            console.log(`📡 CHIAMATA API IVA IN CORSO: ${JSON.stringify(callData)}`);
        }

        return fetch('/ddt/api/update_ticket_field', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(callData)
        }).then(response => response.json()).then(result => {
            // Logging specifico per risposta IVA
            if (callData.field === 'id_iva') {
                console.log(`📡 RISPOSTA API IVA: ${JSON.stringify(result)}`);
            }
            return result;
        });
    }))
    .then(results => {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        
        // Controlla se tutte le chiamate sono andate a buon fine
        const allSuccess = results.every(result => result.success);
        const errors = results.filter(result => !result.success);
        
        if (allSuccess) {
            showNotification('Linea aggiornata con successo!', 'success');

            // Debug: Log specifico per IVA se presente nei risultati
            const ivaCall = apiCalls.find(call => call.field === 'id_iva');
            if (ivaCall) {
                const ivaResult = results[apiCalls.indexOf(ivaCall)];
                console.log(`🎯 RISULTATO SALVATAGGIO IVA: ${JSON.stringify(ivaResult)}`);
                if (ivaResult.success) {
                    console.log(`✅ IVA salvata correttamente nel database!`);

                    // Verifica che l'IVA sia stata effettivamente salvata nell'articolo e nella linea del ticket
                    setTimeout(() => {
                        console.log(`🔍 Verifica IVA dopo salvataggio...`);

                        // Verifica IVA dell'articolo
                        fetch(`/ddt/api/check_article_iva/${formData.id_articulo}`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    console.log(`📊 IVA articolo ${data.article_id} (${data.descripcion}): ${data.iva_description} (IdIva: ${data.current_iva})`);
                                    if (data.current_iva == ivaCall.value) {
                                        console.log(`🎉 CONFERMA: IVA articolo aggiornata correttamente a ${data.iva_description}!`);
                                    } else {
                                        console.error(`🚨 DISCREPANZA ARTICOLO: IVA richiesta ${ivaCall.value} ma salvata ${data.current_iva}`);
                                    }
                                } else {
                                    console.error(`❌ Errore verifica IVA articolo: ${data.message}`);
                                }
                            })
                            .catch(error => {
                                console.error(`❌ Errore rete verifica IVA articolo: ${error}`);
                            });

                        // Verifica IVA della linea del ticket
                        fetch(`/ddt/api/check_ticket_line_iva/${formData.ticket_id}/${formData.line_id}`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    console.log(`📋 IVA linea ticket ${data.line_id} (${data.descripcion}): ${data.iva_description} (IdIVA: ${data.current_iva}, PorcentajeIVA: ${data.porcentaje_iva})`);
                                    if (data.current_iva == ivaCall.value) {
                                        console.log(`🎉 CONFERMA: IVA linea ticket aggiornata correttamente a ${data.iva_description}!`);
                                    } else {
                                        console.error(`🚨 DISCREPANZA LINEA: IVA richiesta ${ivaCall.value} ma salvata ${data.current_iva}`);
                                    }
                                } else {
                                    console.error(`❌ Errore verifica IVA linea ticket: ${data.message}`);
                                }
                            })
                            .catch(error => {
                                console.error(`❌ Errore rete verifica IVA linea ticket: ${error}`);
                            });
                    }, 1000); // Aspetta 1 secondo per essere sicuro che il DB sia aggiornato

                } else {
                    console.error(`❌ Errore salvataggio IVA: ${ivaResult.message}`);
                }
            }

            // 💾 SALVA LE MODIFICHE IN STORAGE PERSISTENTE
            saveModificationsToStorage(formData, results);

            // Chiudi il modale e rimuovi backdrop
            const modal = bootstrap.Modal.getInstance(document.getElementById('editLineModal'));
            if (modal) {
                modal.hide();
                // Forza la rimozione del backdrop dopo un piccolo delay
                setTimeout(() => {
                    forceRemoveModalBackdrop();
                }, 300);
            }

            // Aggiorna i dati locali senza ricaricare la pagina
            updateLocalTicketData(formData.ticket_id, formData.line_id, formData);

            // Aggiorna il riepilogo se la funzione esiste (compatibilità con tasks.js)
            if (typeof updateSummary === 'function') {
                updateSummary();
            }

            updateTicketDisplayInTable(formData.ticket_id, formData);
            
            // 🕰️ VERIFICA AGGIORNAMENTO CON DELAY
            setTimeout(() => {
                console.log('🔍 Verifica aggiornamento prezzi dopo salvataggio...');
                updateTicketPriceDisplay(formData.ticket_id);
                checkPriceConsistency();

                // 🔥 AGGIUNTO: Aggiorna sempre i totali dopo modifica linea
                setTimeout(updateTotalsBar, 200);
            }, 500);
            
        } else {
            const errorMessages = errors.map(err => err.message || 'Errore sconosciuto').join(', ');
            showNotification(`Errori nel salvataggio: ${errorMessages}`, 'danger');
            console.error('Errori API:', errors);

            // Debug: Controlla se ci sono errori specifici per IVA
            const ivaError = errors.find((err, index) => apiCalls[index] && apiCalls[index].field === 'id_iva');
            if (ivaError) {
                console.error(`🚨 ERRORE SPECIFICO IVA: ${JSON.stringify(ivaError)}`);
                showNotification(`Errore salvataggio IVA: ${ivaError.message}`, 'warning');
            }
        }
    })
    .catch(error => {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        console.error('Errore durante il salvataggio:', error);
        showNotification('Errore di rete durante il salvataggio', 'danger');
    });
}

// ===== FUNZIONI HELPER PER AGGIORNAMENTO DATI =====
function updateLocalTicketData(ticketId, lineId, newData) {
    console.log('🔄 Aggiornamento dati locali ticket:', ticketId, lineId, newData);
    
    // Aggiorna i dati in previewData se esistono
    if (previewData && previewData[ticketId]) {
        const ticketData = previewData[ticketId];
        
        // Trova e aggiorna la linea specifica
        if (ticketData.lines) {
            const lineIndex = ticketData.lines.findIndex(line => line.id_linea_ticket == lineId);
            if (lineIndex !== -1) {
                const line = ticketData.lines[lineIndex];
                
                // Salva i valori originali prima della modifica
                const originalValues = {
                    peso: line.peso,
                    precio: line.precio,
                    precio_sin_iva: line.precio_sin_iva,
                    importe: line.importe,
                    importe_con_iva: line.importe_con_iva,
                    comportamiento: line.comportamiento,
                    fecha_caducidad: line.fecha_caducidad,
                    texto_lote: line.texto_lote
                };

                // Aggiorna i campi modificati
                line.peso = newData.peso;

                // ✅ CORREZIONE COMPLETA: Gestione valori con e senza IVA
                // newData.iva contiene il valore backend (4=Esente, 1=4%, 2=10%, 3=22%), converti in vatRate
                let vatRate = line.vat_rate || line.porcentaje_iva / 100 || 0.04; // Default
                if (newData.iva !== undefined) {
                    // Converti valore backend in vatRate
                    if (newData.iva === 4) vatRate = 0.00;     // Esente IVA (id_iva = 4)
                    else if (newData.iva === 1) vatRate = 0.04; // 4%
                    else if (newData.iva === 2) vatRate = 0.10; // 10%
                    else if (newData.iva === 3) vatRate = 0.22; // 22%
                }

                // Usa i valori calcolati dal form (che ora includono sia con IVA che senza IVA)
                line.precio = parseFloat(newData.precio); // CON IVA
                line.precio_sin_iva = newData.precio_sin_iva ? parseFloat(newData.precio_sin_iva) : parseFloat(newData.precio) / (1 + vatRate); // SENZA IVA
                line.importe_con_iva = parseFloat(newData.importe); // CON IVA
                line.importe = newData.precio_sin_iva ?
                    parseFloat(newData.peso) * parseFloat(newData.precio_sin_iva) : // SENZA IVA (se disponibile)
                    parseFloat(newData.importe) / (1 + vatRate); // SENZA IVA (calcolato)

                // 🔥 NUOVO: Gestione campo ImporteSinIVASinDtoL dal database
                if (newData.ImporteSinIVASinDtoL !== undefined) {
                    line.ImporteSinIVASinDtoL = parseFloat(newData.ImporteSinIVASinDtoL);
                    console.log(`💰 Impostato ImporteSinIVASinDtoL: €${line.ImporteSinIVASinDtoL.toFixed(2)}`);
                } else {
                    // Fallback: calcola se non fornito
                    line.ImporteSinIVASinDtoL = line.importe;
                }

                line.comportamiento = newData.comportamiento;
                line.fecha_caducidad = newData.fecha_caducidad;
                line.texto_lote = newData.texto_lote;

                // ✅ CORREZIONE: I valori sono direttamente CON IVA dal database
                console.log(`💰 Valori aggiornati per linea ${lineId}:`);
                console.log(`   - Prezzo con IVA: €${line.precio} (direttamente dal DB)`);
                console.log(`   - Importo con IVA: €${line.importe_con_iva} (direttamente dal DB)`);
                console.log(`   - IVA utilizzata: ${(vatRate * 100).toFixed(0)}%`);
                
                // Aggiorna IVA se modificata
                if (newData.iva !== undefined) {
                    line.id_iva = newData.iva;  // Salva valore backend (0,1,2,3)
                    line.porcentaje_iva = vatRate * 100;  // Percentuale effettiva (0, 4, 10, 22)
                    // Aggiorna anche il vat_rate per compatibilità
                    line.vat_rate = vatRate;  // Usa il vatRate calcolato sopra

                    console.log(`🧮 IVA aggiornata: id_iva=${newData.iva}, vatRate=${vatRate}, porcentaje=${line.porcentaje_iva}%`);
                }
                
                // Aggiorna anche la descrizione se fornita
                if (newData.descripcion !== undefined) {
                    line.descripcion = newData.descripcion;
                }
                
                // Calcola il nuovo totale del ticket
                ticketData.total = ticketData.lines.reduce((sum, l) => sum + (parseFloat(l.importe) || 0), 0);
                ticketData.ticket_total = ticketData.total;
                
                // 🔄 MARCA LE MODIFICHE COME APPLICATE nello storage
                markModificationsAsApplied(ticketId, lineId, newData);
                
                console.log('✅ Dati locali aggiornati con successo');
                
                // 📨 NOTIFICA IL CAMBIAMENTO per aggiornare altri componenti
                notifyTicketDataChanged(ticketId, lineId, originalValues, newData);
            }
        }
    }
}

function markModificationsAsApplied(ticketId, lineId, newData) {
    if (typeof markModificationAsApplied === 'function') {
        // Mappa i campi ai nomi usati nell'API
        const fieldMapping = {
            'peso': 'peso_quantita',
            'precio': 'prezzo_unitario',
            'precio_sin_iva': 'precio_sin_iva',
            'importe': 'prezzo_totale',
            'ImporteSinIVASinDtoL': 'ImporteSinIVASinDtoL',
            'fecha_caducidad': 'data_scadenza',
            'descripcion': 'descrizione',
            'iva': 'id_iva'
        };
        
        Object.keys(fieldMapping).forEach(fieldKey => {
            if (newData[fieldKey] !== undefined) {
                const apiField = fieldMapping[fieldKey];
                markModificationAsApplied(ticketId, lineId, apiField);
            }
        });
    }
}

function notifyTicketDataChanged(ticketId, lineId, originalValues, newValues) {
    console.log('📨 Notifica cambiamento dati ticket:', ticketId);
    
    // Emetti un evento personalizzato per permettere ad altri componenti di reagire
    const event = new CustomEvent('ticketDataChanged', {
        detail: {
            ticketId: ticketId,
            lineId: lineId,
            originalValues: originalValues,
            newValues: newValues,
            timestamp: Date.now()
        }
    });
    
    document.dispatchEvent(event);
    
    // Aggiorna specificamente la visualizzazione del prezzo nella tabella
    updateTicketPriceDisplay(ticketId);
}

function updateTicketPriceDisplay(ticketId) {
    console.log('💰 Aggiornamento prezzo visualizzato per ticket:', ticketId);
    
    // Trova la riga del ticket nella tabella e aggiorna il prezzo visualizzato
    const ticketRow = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
    console.log('🔍 Riga ticket trovata:', !!ticketRow);
    
    if (ticketRow && previewData[ticketId]) {
        const priceElement = ticketRow.querySelector('.price-value');
        console.log('🔍 Elemento prezzo trovato:', !!priceElement);
        
        if (priceElement) {
            // Ricalcola il totale dal ticket data per essere sicuri
            let newTotal = 0;
            const ticketData = previewData[ticketId];
            
            if (ticketData.lines && Array.isArray(ticketData.lines)) {
                newTotal = ticketData.lines.reduce((sum, line) => {
                    const lineTotal = parseFloat(line.importe) || 0;
                    console.log(`📊 Linea ${line.id_linea_ticket}: €${lineTotal}`);
                    return sum + lineTotal;
                }, 0);
            } else {
                newTotal = ticketData.total || 0;
            }
            
            // Aggiorna anche i dati per consistenza
            ticketData.total = newTotal;
            ticketData.ticket_total = newTotal;
            
            const oldValue = priceElement.textContent;
            const newValue = newTotal.toFixed(2);
            
            console.log(`💰 Aggiornamento prezzo: ${oldValue} → €${newValue}`);
            
            priceElement.textContent = newValue;
            
            // Aggiungi una breve animazione per evidenziare il cambiamento
            if (oldValue !== newValue) {
                priceElement.style.transition = 'all 0.3s ease';
                priceElement.style.color = '#28a745'; // Verde per indicare aggiornamento
                priceElement.style.fontWeight = 'bold';
                priceElement.style.transform = 'scale(1.1)';
                
                // Notifica visiva del cambiamento
                showNotification(`Prezzo aggiornato: €${newValue}`, 'success', 2000);
                
                setTimeout(() => {
                    priceElement.style.color = ''; // Ripristina colore originale
                    priceElement.style.fontWeight = '';
                    priceElement.style.transform = '';
                }, 1000);
            }
        } else {
            console.error('❌ Elemento .price-value non trovato nella riga del ticket');
        }
    } else {
        console.error('❌ Riga ticket o dati preview non trovati:', {
            ticketRow: !!ticketRow,
            previewData: !!previewData[ticketId]
        });
    }
}

function updateTicketDisplayInTable(ticketId, newData) {
    console.log('🔄 Aggiornamento visualizzazione tabella per ticket:', ticketId, newData);
    
    // Usa la funzione migliorata per aggiornare il prezzo
    updateTicketPriceDisplay(ticketId);
    
    // Aggiorna anche il riepilogo generale
    if (typeof updateSummary === 'function') {
        updateSummary();
    }
    
    console.log('✅ Visualizzazione tabella aggiornata');
}

// ===== FUNZIONE PULIZIA BACKDROP =====
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

// Aggiungi event listener per gestire la chiusura delle modali
document.addEventListener('DOMContentLoaded', function() {
    // Event listener per tutte le modali quando vengono nascoste
    document.addEventListener('hidden.bs.modal', function (event) {
        console.log('👁️ Modale nascosta:', event.target.id);
        
        // Delay per assicurarsi che Bootstrap abbia finito
        setTimeout(() => {
            forceRemoveModalBackdrop();
        }, 100);
    });
    
    // Event listener per il click sui pulsanti di chiusura
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-bs-dismiss="modal"]') || 
            e.target.closest('[data-bs-dismiss="modal"]')) {
            console.log('❌ Pulsante chiusura modale cliccato');
            
            setTimeout(() => {
                forceRemoveModalBackdrop();
            }, 300);
        }
    });
    
    // Event listener per il tasto ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            console.log('⌨️ Tasto ESC premuto');
            
            setTimeout(() => {
                forceRemoveModalBackdrop();
            }, 300);
        }
    });
});

// ===== FUNZIONI DI DEBUG E RIPARAZIONE =====
function forceUpdateAllTicketPrices() {
    console.log('🔧 Aggiornamento forzato di tutti i prezzi e quantità dei ticket...');
    
    if (!previewData) {
        console.error('❌ Dati preview non disponibili');
        return;
    }
    
    let updatedCount = 0;
    Object.keys(previewData).forEach(ticketId => {
        try {
            if (typeof updateTicketPriceDetails === 'function') {
                updateTicketPriceDetails(ticketId);
            } else {
                updateTicketPriceDisplay(ticketId);
            }
            updatedCount++;
        } catch (e) {
            console.error(`❌ Errore aggiornamento ticket ${ticketId}:`, e);
        }
    });
    
    console.log(`✅ Aggiornati ${updatedCount} ticket`);
    showNotification(`Aggiornati ${updatedCount} prezzi e quantità ticket`, 'success');
    
    // Aggiorna anche il riepilogo
    if (typeof updateSummary === 'function') {
        updateSummary();
    }
}

// Esponi la funzione globalmente per debugging
window.forceUpdateAllTicketPrices = forceUpdateAllTicketPrices;

// Aggiungi un pulsante nascosto per l'aggiornamento forzato
document.addEventListener('DOMContentLoaded', function() {
    // Crea un pulsante nascosto per l'aggiornamento forzato
    if (!document.getElementById('force-update-prices')) {
        const forceBtn = document.createElement('button');
        forceBtn.id = 'force-update-prices';
        forceBtn.className = 'btn btn-outline-warning btn-sm';
        forceBtn.style.display = 'none';
        forceBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Forza Aggiornamento Prezzi';
        forceBtn.addEventListener('click', forceUpdateAllTicketPrices);
        document.body.appendChild(forceBtn);
        
        console.log('🔧 Pulsante debug aggiunto. Usa window.forceUpdateAllTicketPrices() per aggiornare tutti i prezzi.');
    }
    
    // ⚡ CONTROLLO IMMEDIATO AL CARICAMENTO
    setTimeout(() => {
        console.log('⚡ Primo controllo prezzi dal modals.js...');
        checkPriceConsistency();
    }, 300);
    
    // Avvia controllo automatico ogni 3 secondi (ridotto da 10)
    setInterval(checkPriceConsistency, 3000);
});

function checkPriceConsistency() {
    if (!previewData) return;
    
    let inconsistentCount = 0;
    Object.keys(previewData).forEach(ticketId => {
        const ticketRow = document.querySelector(`tr[data-ticket-id="${ticketId}"]`);
        if (ticketRow) {
            const priceWithVatElement = ticketRow.querySelector('.price-with-vat');
            if (priceWithVatElement && previewData[ticketId]) {
                const displayedPriceWithVat = parseFloat(priceWithVatElement.textContent) || 0;
                
                // Calcola il prezzo con IVA attuale dai dati
                let actualPriceWithVat = 0;
                const ticketData = previewData[ticketId];
                
                if (ticketData.lines && Array.isArray(ticketData.lines)) {
                    actualPriceWithVat = ticketData.lines.reduce((sum, line) => {
                        const peso = parseFloat(line.peso) || 0;
                        const precio = parseFloat(line.precio) || 0;
                        
                        // Calcola IVA per questa linea
                        let ivaRate = 0.04; // Default 4%
                        if (line.porcentaje_iva) {
                            ivaRate = parseInt(line.porcentaje_iva) / 100;
                        } else if (line.iva) {
                            ivaRate = parseInt(line.iva) / 100;
                        } else if (line.id_iva) {
                            switch (parseInt(line.id_iva)) {
                                case 0: ivaRate = 0.00; break; // 0% - Esente IVA
                                case 1: ivaRate = 0.04; break;
                                case 2: ivaRate = 0.10; break;
                                case 3: ivaRate = 0.22; break;
                                default: ivaRate = 0.04; break;
                            }
                        }
                        
                        // Verifica se è un ticket manuale - in tal caso il prezzo è già CON IVA
                        const isManualTicket = ticketData.ticket && (ticketData.ticket.is_manual || ticketData.ticket.id_ticket < 0);
                        let lineTotal;
                        
                        if (isManualTicket) {
                            // Per ticket manuali: il prezzo è già CON IVA
                            lineTotal = peso * precio;
                        } else {
                            // Per ticket normali: il prezzo è senza IVA, quindi applichiamo l'IVA
                            lineTotal = peso * precio * (1 + ivaRate);
                        }
                        
                        return sum + lineTotal;
                    }, 0);
                }
                
                // Controlla se c'è una discrepanza significativa (> 0.01€)
                if (Math.abs(displayedPriceWithVat - actualPriceWithVat) > 0.01) {
                    console.warn(`⚠️ Discrepanza prezzo CON IVA ticket ${ticketId}: visualizzato €${displayedPriceWithVat}, effettivo €${actualPriceWithVat.toFixed(2)}`);
                    inconsistentCount++;
                    
                    // Correggi automaticamente usando la nuova funzione
                    if (typeof updateTicketPriceDetails === 'function') {
                        updateTicketPriceDetails(ticketId);
                    } else {
                        // Fallback alla vecchia funzione se disponibile
                        updateTicketPriceDisplay(ticketId);
                    }
                }
            }
        }
    });
    
    if (inconsistentCount > 0) {
        console.log(`🔧 Corrette ${inconsistentCount} discrepanze nei prezzi CON IVA`);
    }
}

// ===== GESTIONE STORAGE PERSISTENTE MODIFICHE =====
function saveModificationsToStorage(formData, apiResults) {
    console.log('💾 Salvataggio modifiche in storage persistente...', formData);
    
    // Mappa dei campi dal form ai campi dell'API
    const fieldMapping = {
        'peso': 'peso_quantita',
        'precio': 'prezzo_unitario',
        'importe': 'prezzo_totale',
        'fecha_caducidad': 'data_scadenza',
        'descripcion': 'descrizione',
        'iva': 'id_iva',
        'ImporteSinIVASinDtoL': 'ImporteSinIVASinDtoL'  // 🔥 CORRETTO: Campo database corretto
    };

    // Salva ogni modifica riuscita nello storage
    const fieldsToSave = ['peso', 'precio', 'precio_sin_iva', 'importe', 'ImporteSinIVASinDtoL', 'fecha_caducidad', 'descripcion', 'iva'];

    fieldsToSave.forEach(fieldKey => {
        if (formData[fieldKey] !== undefined && formData[fieldKey] !== null) {
            const apiField = fieldMapping[fieldKey] || fieldKey;

            // Recupera il valore originale dai dati preview se possibile
            let originalValue = null;
            try {
                if (previewData && previewData[formData.ticket_id] && previewData[formData.ticket_id].lines) {
                    const line = previewData[formData.ticket_id].lines.find(l => l.id_linea_ticket == formData.line_id);
                    if (line) {
                        switch (fieldKey) {
                            case 'peso': originalValue = line.peso; break;
                            case 'precio': originalValue = line.precio; break;
                            case 'precio_sin_iva': originalValue = line.precio_sin_iva; break;
                            case 'importe': originalValue = line.importe; break;
                            case 'fecha_caducidad': originalValue = line.fecha_caducidad; break;
                            case 'descripcion': originalValue = line.descripcion; break;
                        }
                    }
                }
            } catch (e) {
                console.warn('⚠️ Impossibile recuperare valore originale per', fieldKey, ':', e);
            }
            
            // Salva la modifica nel localStorage
            if (typeof saveTicketModificationToStorage === 'function') {
                saveTicketModificationToStorage(
                    formData.ticket_id,
                    formData.line_id,
                    apiField,
                    formData[fieldKey],
                    originalValue
                );
            } else {
                console.error('❌ Funzione saveTicketModificationToStorage non trovata');
            }
        }
    });
    
    console.log('✅ Modifiche salvate in storage persistente');
}

function getOriginalValueFromPreviewData(ticketId, lineId, field) {
    try {
        if (!previewData || !previewData[ticketId] || !previewData[ticketId].lines) {
            return null;
        }
        
        const line = previewData[ticketId].lines.find(l => l.id_linea_ticket == lineId);
        if (!line) return null;
        
        switch (field) {
            case 'peso_quantita': return line.peso;
            case 'prezzo_unitario': return line.precio;
            case 'prezzo_sin_iva': return line.precio_sin_iva;
            case 'prezzo_totale': return line.importe;
            case 'ImporteSinIVASinDtoL': return line.ImporteSinIVASinDtoL;
            case 'data_scadenza': return line.fecha_caducidad;
            case 'descrizione': return line.descripcion;
            case 'id_iva': return line.id_iva || line.porcentaje_iva;
            default: return null;
        }
    } catch (e) {
        console.warn('⚠️ Errore nel recupero valore originale:', e);
        return null;
    }
}

// ===== FUNZIONI UTILITÀ PER L'UTENTE =====
// Queste funzioni possono essere chiamate dalla console del browser
window.DDTDebugUtils = {
    // Forza l'aggiornamento di tutti i prezzi
    updateAllPrices: forceUpdateAllTicketPrices,
    
    // Mostra i dati di un ticket specifico
    showTicketData: function(ticketId) {
        console.log(`Dati ticket ${ticketId}:`, previewData[ticketId]);
        return previewData[ticketId];
    },
    
    // Controlla la consistenza dei prezzi
    checkPrices: checkPriceConsistency,
    
    // Controllo immediato forzato
    checkNow: function() {
        console.log('⚡ Controllo prezzi forzato dall\'utente...');
        checkPriceConsistency();
        forceUpdateAllTicketPrices();
    },
    
    // Corregge un ticket specifico
    fixTicketPrice: function(ticketId) {
        console.log(`🔧 Correzione prezzi e quantità ticket ${ticketId}...`);
        if (typeof updateTicketPriceDetails === 'function') {
            updateTicketPriceDetails(ticketId);
        } else {
            updateTicketPriceDisplay(ticketId);
        }
    },
    
    // Mostra tutti i dati preview
    showAllData: function() {
        console.log('Tutti i dati preview:', previewData);
        return previewData;
    },
    
    // Reset completo dei dati (ricarica dalla pagina)
    resetData: function() {
        if (confirm('Sei sicuro di voler ricaricare tutti i dati? Le modifiche non salvate andranno perse.')) {
            window.location.reload();
        }
    }
};

console.log('✅ DDT Preview Modals caricato');
console.log('🔧 Utilità debug disponibili in window.DDTDebugUtils');
console.log('  - DDTDebugUtils.updateAllPrices(): Aggiorna tutti i prezzi e quantità');
console.log('  - DDTDebugUtils.checkNow(): ⚡ CONTROLLO IMMEDIATO prezzi CON IVA');
console.log('  - DDTDebugUtils.fixTicketPrice(ID): Corregge prezzi e quantità di un ticket specifico');
console.log('  - DDTDebugUtils.checkPrices(): Controlla consistenza prezzi CON IVA');
console.log('  - DDTDebugUtils.showTicketData(ID): Mostra dati di un ticket');
console.log('  - DDTDebugUtils.showAllData(): Mostra tutti i dati');
console.log('  - DDTDebugUtils.resetData(): Reset completo (ricarica pagina)');

// Mostra esempi di arrotondamento all'avvio
console.log('🧮 Per testare l\'arrotondamento commerciale: window.testRoundingExamples()');
