/**
 * Price Calculator for Articles
 * Handles automatic VAT calculation for articles
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Price Calculator: Inizializzazione...');
    
    // Get form elements with multiple possible IDs
    const priceWithoutVat = document.getElementById('precio_sin_iva') || 
                           document.getElementById('PrecioSinIva') || 
                           document.getElementById('PrecioSinIVA');
    
    const priceWithVat = document.getElementById('precio_con_iva') || 
                        document.getElementById('PrecioConIva') || 
                        document.getElementById('PrecioConIVA');
    
    const vatSelect = document.getElementById('id_iva') || 
                     document.getElementById('IdIva') || 
                     document.getElementById('IdIVA') ||
                     document.getElementById('IDIva');
    
    console.log('🔍 Elementi trovati:', {
        priceWithoutVat: priceWithoutVat ? priceWithoutVat.id : 'NON TROVATO',
        priceWithVat: priceWithVat ? priceWithVat.id : 'NON TROVATO',
        vatSelect: vatSelect ? vatSelect.id : 'NON TROVATO'
    });
    
    // Detect input type to determine format
    const isNumberInput = priceWithoutVat && priceWithoutVat.type === 'number';
    console.log('🔍 Tipo di input rilevato:', isNumberInput ? 'NUMBER (usa punto)' : 'TEXT (usa virgola)');
    
    // Se non trovati con gli ID, prova con i nomi
    if (!priceWithoutVat || !priceWithVat || !vatSelect) {
        console.log('🔍 Ricerca per nome...');
        const allInputs = document.querySelectorAll('input, select');
        allInputs.forEach(input => {
            console.log(`Campo trovato: ${input.name || input.id} (${input.type})`);
        });
    }
    
    // Check if elements exist
    if (!priceWithoutVat || !priceWithVat || !vatSelect) {
        console.error('❌ Elementi mancanti per il calcolo IVA:', {
            priceWithoutVat: !!priceWithoutVat,
            priceWithVat: !!priceWithVat,
            vatSelect: !!vatSelect
        });
        return;
    }
    
    console.log('✅ Tutti gli elementi trovati, inizializzazione calcolo IVA...');
    
    // Flag to prevent infinite loops during calculations
    let isCalculating = false;
    
    /**
     * Get current VAT rate from select (extract from text like "4%" or "22%")
     */
    function getCurrentVatRate() {
        const selectedOption = vatSelect.options[vatSelect.selectedIndex];
        console.log('🔍 Opzione IVA selezionata:', {
            value: selectedOption?.value,
            text: selectedOption?.text,
            index: vatSelect.selectedIndex
        });
        
        if (!selectedOption || selectedOption.value === '' || selectedOption.value === '0') {
            console.log('⚠️ Nessuna IVA selezionata');
            return 0;
        }
        
        const vatText = selectedOption.text || '';
        
        // Extract percentage from text like "4%" or "IVA 22%"
        const match = vatText.match(/(\d+(?:\.\d+)?)\s*%/);
        if (match) {
            const rate = parseFloat(match[1]) / 100;
            console.log(`✅ IVA estratta dal testo: ${match[1]}% = ${rate}`);
            return rate;
        }
        
        // Fallback: try to map by option value (IdIVA)
        const vatId = parseInt(selectedOption.value);
        let rate = 0;
        switch(vatId) {
            case 1: rate = 0.04; break;  // 4%
            case 2: rate = 0.10; break;  // 10%
            case 3: rate = 0.22; break;  // 22%
            default: rate = 0; break;
        }
        
        console.log(`✅ IVA mappata da ID ${vatId}: ${Math.round(rate * 100)}% = ${rate}`);
        return rate;
    }
    
    /**
     * Format price for input field (dot for number inputs, comma for text inputs)
     */
    function formatPriceForInput(price) {
        const formatted = parseFloat(price).toFixed(2);
        return isNumberInput ? formatted : formatted.replace('.', ',');
    }
    
    /**
     * Format price for display (always with comma - Italian format)
     */
    function formatPriceForDisplay(price) {
        const formatted = parseFloat(price).toFixed(2).replace('.', ',');
        console.log(`💰 Formatazione display: ${price} → €${formatted}`);
        return formatted;
    }
    
    /**
     * Parse price from input (handle both comma and dot)
     */
    function parsePrice(priceStr) {
        if (!priceStr || (typeof priceStr !== 'string' && typeof priceStr !== 'number')) {
            console.log('⚠️ Prezzo non valido:', priceStr);
            return NaN;
        }
        
        const strValue = String(priceStr);
        const parsed = parseFloat(strValue.replace(',', '.'));
        console.log(`🔢 Parsing prezzo: "${strValue}" → ${parsed}`);
        return parsed;
    }
    
    /**
     * Calculate price with VAT from price without VAT
     */
    function calculatePriceWithVat() {
        if (isCalculating) {
            console.log('🔄 Calcolo già in corso, skip...');
            return;
        }
        
        console.log('➕ Calcolo prezzo CON IVA...');
        
        const priceWithoutVatValue = parsePrice(priceWithoutVat.value);
        const vatRate = getCurrentVatRate();
        
        console.log('📊 Dati per calcolo:', {
            prezzoSenzaIva: priceWithoutVatValue,
            aliquotaIva: vatRate,
            valoreInput: priceWithoutVat.value
        });
        
        if (isNaN(priceWithoutVatValue) || priceWithoutVatValue <= 0) {
            console.log('❌ Prezzo senza IVA non valido');
            priceWithVat.value = '';
            removeVatDisplay();
            return;
        }
        
        isCalculating = true;
        const priceWithVatValue = priceWithoutVatValue * (1 + vatRate);
        priceWithVat.value = formatPriceForInput(priceWithVatValue);
        isCalculating = false;
        
        console.log(`✅ Calcolato: ${priceWithoutVatValue} × (1 + ${vatRate}) = ${priceWithVatValue}`);
        console.log(`📝 Scritto nel campo (${isNumberInput ? 'number' : 'text'}): ${priceWithVat.value}`);
        
        // Add visual feedback
        priceWithVat.classList.add('auto-calculated');
        setTimeout(() => {
            priceWithVat.classList.remove('auto-calculated');
        }, 1000);
        
        // Update VAT display
        displayVatAmount();
    }
    
    /**
     * Calculate price without VAT from price with VAT
     */
    function calculatePriceWithoutVat() {
        if (isCalculating) {
            console.log('🔄 Calcolo già in corso, skip...');
            return;
        }
        
        console.log('➖ Calcolo prezzo SENZA IVA...');
        
        const priceWithVatValue = parsePrice(priceWithVat.value);
        const vatRate = getCurrentVatRate();
        
        console.log('📊 Dati per calcolo:', {
            prezzoConIva: priceWithVatValue,
            aliquotaIva: vatRate,
            valoreInput: priceWithVat.value
        });
        
        if (isNaN(priceWithVatValue) || priceWithVatValue <= 0) {
            console.log('❌ Prezzo con IVA non valido');
            priceWithoutVat.value = '';
            removeVatDisplay();
            return;
        }
        
        if (vatRate === 0) {
            console.log('⚠️ IVA = 0%, copiando il valore');
            isCalculating = true;
            priceWithoutVat.value = formatPriceForInput(priceWithVatValue);
            isCalculating = false;
            displayVatDisplay(priceWithVatValue, priceWithVatValue, 0);
            return;
        }
        
        isCalculating = true;
        const priceWithoutVatValue = priceWithVatValue / (1 + vatRate);
        priceWithoutVat.value = formatPriceForInput(priceWithoutVatValue);
        isCalculating = false;
        
        console.log(`✅ Calcolato: ${priceWithVatValue} ÷ (1 + ${vatRate}) = ${priceWithoutVatValue}`);
        console.log(`📝 Scritto nel campo (${isNumberInput ? 'number' : 'text'}): ${priceWithoutVat.value}`);
        
        // Add visual feedback
        priceWithoutVat.classList.add('auto-calculated');
        setTimeout(() => {
            priceWithoutVat.classList.remove('auto-calculated');
        }, 1000);
        
        // Update VAT display
        displayVatAmount();
    }
    
    /**
     * Recalculate both prices when VAT changes
     */
    function recalculateOnVatChange() {
        console.log('🔄 Ricalcolo a seguito cambio IVA...');
        const priceWithoutVatValue = parsePrice(priceWithoutVat.value);
        const priceWithVatValue = parsePrice(priceWithVat.value);
        
        // Prioritize price without VAT if both fields have values
        if (!isNaN(priceWithoutVatValue) && priceWithoutVatValue > 0) {
            console.log('📊 Ricalcolo basato su prezzo senza IVA');
            calculatePriceWithVat();
        } else if (!isNaN(priceWithVatValue) && priceWithVatValue > 0) {
            console.log('📊 Ricalcolo basato su prezzo con IVA');
            calculatePriceWithoutVat();
        } else {
            console.log('📊 Nessun prezzo valido per ricalcolo');
            removeVatDisplay();
        }
    }
    
    /**
     * Display current VAT amount breakdown
     */
    function displayVatAmount() {
        const priceWithoutVatValue = parsePrice(priceWithoutVat.value);
        const priceWithVatValue = parsePrice(priceWithVat.value);
        
        if (isNaN(priceWithoutVatValue) || isNaN(priceWithVatValue)) {
            removeVatDisplay();
            return;
        }
        
        const vatAmount = priceWithVatValue - priceWithoutVatValue;
        const vatRate = getCurrentVatRate();
        
        displayVatDisplay(priceWithoutVatValue, priceWithVatValue, vatAmount, vatRate);
    }
    
    /**
     * Show VAT calculation breakdown
     */
    function displayVatDisplay(basePrice, totalPrice, vatAmount, vatRate = null) {
        removeVatDisplay();
        
        if (basePrice <= 0 || totalPrice <= 0) return;
        
        const vatDisplay = document.createElement('div');
        vatDisplay.className = 'vat-amount-display alert alert-info mt-2';
        
        const vatPercentage = vatRate ? Math.round(vatRate * 100) : Math.round(((vatAmount / basePrice) * 100));
        
        vatDisplay.innerHTML = `
            <div class="row text-center">
                <div class="col-4">
                    <strong>Base Imponibile</strong><br>
                    <span class="h6">€${formatPriceForDisplay(basePrice)}</span>
                </div>
                <div class="col-4">
                    <strong>IVA ${vatPercentage}%</strong><br>
                    <span class="h6 text-primary">€${formatPriceForDisplay(vatAmount)}</span>
                </div>
                <div class="col-4">
                    <strong>Totale</strong><br>
                    <span class="h6 text-success">€${formatPriceForDisplay(totalPrice)}</span>
                </div>
            </div>
        `;
        
        // Insert after the price with VAT field
        priceWithVat.parentNode.appendChild(vatDisplay);
        console.log('📊 Display IVA aggiornato');
    }
    
    /**
     * Remove VAT display
     */
    function removeVatDisplay() {
        const existingVatDisplay = document.querySelector('.vat-amount-display');
        if (existingVatDisplay) {
            existingVatDisplay.remove();
        }
    }
    
    /**
     * Add helpful info text below price fields
     */
    function updateInfoText() {
        const vatRate = getCurrentVatRate();
        
        // Remove existing info texts
        const existingInfos = document.querySelectorAll('.price-field-info');
        existingInfos.forEach(info => info.remove());
        
        if (vatRate === 0) {
            return;
        }
        
        const vatPercentage = Math.round(vatRate * 100);
        
        // Add info for price without VAT
        const infoWithoutVat = document.createElement('small');
        infoWithoutVat.className = 'price-field-info text-muted d-block mt-1';
        infoWithoutVat.innerHTML = `<i class="fas fa-calculator me-1"></i>Inserisci il prezzo base, l'IVA al ${vatPercentage}% verrà calcolata automaticamente`;
        priceWithoutVat.parentNode.appendChild(infoWithoutVat);
        
        // Add info for price with VAT
        const infoWithVat = document.createElement('small');
        infoWithVat.className = 'price-field-info text-muted d-block mt-1';
        infoWithVat.innerHTML = `<i class="fas fa-calculator me-1"></i>Inserisci il prezzo finale, il prezzo base verrà calcolato automaticamente`;
        priceWithVat.parentNode.appendChild(infoWithVat);
        
        console.log(`📝 Info text aggiornato per IVA ${vatPercentage}%`);
    }
    
    // Event listeners
    priceWithoutVat.addEventListener('input', function(e) {
        console.log('📝 Input prezzo senza IVA:', e.target.value);
        calculatePriceWithVat();
    });
    
    priceWithoutVat.addEventListener('blur', function(e) {
        console.log('👁️ Blur prezzo senza IVA');
        // Only format if it's a text input (number inputs handle their own formatting)
        if (!isNumberInput) {
            const value = parsePrice(e.target.value);
            if (!isNaN(value) && value > 0) {
                e.target.value = formatPriceForInput(value);
                console.log('📝 Valore formattato:', e.target.value);
            }
        }
    });
    
    priceWithVat.addEventListener('input', function(e) {
        console.log('📝 Input prezzo con IVA:', e.target.value);
        calculatePriceWithoutVat();
    });
    
    priceWithVat.addEventListener('blur', function(e) {
        console.log('👁️ Blur prezzo con IVA');
        // Only format if it's a text input (number inputs handle their own formatting)
        if (!isNumberInput) {
            const value = parsePrice(e.target.value);
            if (!isNaN(value) && value > 0) {
                e.target.value = formatPriceForInput(value);
                console.log('📝 Valore formattato:', e.target.value);
            }
        }
    });
    
    vatSelect.addEventListener('change', function() {
        console.log('🔄 Cambio IVA:', this.value, this.options[this.selectedIndex].text);
        recalculateOnVatChange();
        updateInfoText();
    });
    
    // Initialize on page load
    console.log('🚀 Inizializzazione completata');
    updateInfoText();
    
    // If both fields already have values, update the display
    const initialPriceWithoutVat = parsePrice(priceWithoutVat.value);
    const initialPriceWithVat = parsePrice(priceWithVat.value);
    if (!isNaN(initialPriceWithoutVat) && !isNaN(initialPriceWithVat)) {
        console.log('📊 Valori iniziali trovati, aggiorno display');
        displayVatAmount();
    }
    
    // Test function for debugging
    window.testVatCalculator = function() {
        console.log('🧪 Test calcolo IVA:');
        console.log('Elementi:', {
            priceWithoutVat: priceWithoutVat?.id,
            priceWithVat: priceWithVat?.id,
            vatSelect: vatSelect?.id,
            inputType: priceWithoutVat?.type
        });
        console.log('Valori attuali:', {
            senzaIva: priceWithoutVat?.value,
            conIva: priceWithVat?.value,
            iva: vatSelect?.value,
            ivaText: vatSelect?.options[vatSelect?.selectedIndex]?.text
        });
    };
    
    // Add some visual styling for auto-calculated fields
    const style = document.createElement('style');
    style.textContent = `
        .auto-calculated {
            background-color: #e8f5e8 !important;
            border-color: #28a745 !important;
            transition: all 0.3s ease;
        }
        
        .price-field-info {
            font-size: 0.8em;
        }
        
        .vat-amount-display {
            border: 1px solid #bee5eb;
            background-color: #d1ecf1;
            border-radius: 0.375rem;
            font-size: 0.9em;
        }
        
        .vat-amount-display .h6 {
            margin-bottom: 0;
            font-weight: 600;
        }
    `;
    document.head.appendChild(style);
    
    console.log('✅ Price Calculator completamente inizializzato!');
    console.log('💡 Usa testVatCalculator() nella console per debug');
    
}); 