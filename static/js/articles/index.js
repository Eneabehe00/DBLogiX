/**
 * Articles index page functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeLiveSearch();
    initializeResponsiveTables();
    // setupPriceCalculation();
});

/**
 * Initialize the live search functionality
 */
function initializeLiveSearch() {
    // Real-time search functionality
    const liveSearchInput = document.getElementById('liveSearch');
    const clearSearchBtn = document.getElementById('clearSearch');
    const productRows = document.querySelectorAll('.product-row');
    const noResultsMessage = document.createElement('tr');
    
    if (!liveSearchInput) return;
    
    noResultsMessage.innerHTML = '<td colspan="8" class="text-center">Nessun risultato trovato nella ricerca in tempo reale</td>';
    noResultsMessage.style.display = 'none';
    
    if (productRows.length > 0) {
        productRows[0].parentNode.appendChild(noResultsMessage);
    }
    
    // Function to perform real-time search
    function performLiveSearch() {
        const query = liveSearchInput.value.trim().toLowerCase();
        let foundMatch = false;
        
        // Loop through all product rows and filter
        productRows.forEach(row => {
            // Get text of cells directly
            const productId = row.querySelector('td[data-label="ID"]').textContent.toLowerCase();
            const productDescription = row.querySelector('td[data-label="Descrizione"]').textContent.toLowerCase();
            
            // Check if the product matches the search query
            if (query === '' || 
                productDescription.includes(query) || 
                productId.includes(query)) {
                
                row.style.display = '';
                foundMatch = true;
                
                // Highlight matching text in description
                if (query !== '') {
                    const descriptionElement = row.querySelector('td[data-label="Descrizione"]');
                    let html = descriptionElement.textContent;
                    
                    // Reset the content first (remove any previous highlights)
                    descriptionElement.innerHTML = html;
                    
                    if (productDescription.includes(query)) {
                        // Create a highlighted version of the text
                        const regex = new RegExp(escapeRegExp(query), 'gi');
                        html = html.replace(regex, match => `<span class="highlight">${match}</span>`);
                        descriptionElement.innerHTML = html;
                    }
                }
            } else {
                row.style.display = 'none';
            }
        });
        
        // Show or hide "no results" message
        noResultsMessage.style.display = foundMatch ? 'none' : '';
    }
    
    // Utility function to escape special regex characters
    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Function to perform a full database search by redirecting
    function performFullSearch() {
        const query = liveSearchInput.value.trim();
        const currentUrl = window.location.href.split('?')[0];
        
        if (query) {
            window.location.href = `${currentUrl}?query=${encodeURIComponent(query)}`;
        } else {
            window.location.href = currentUrl;
        }
    }
    
    // Add event listeners - ensuring proper attachment
    liveSearchInput.addEventListener('input', performLiveSearch);
    
    // Handle Enter key to perform a full database search
    liveSearchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault(); // Prevent form submission
            performFullSearch();
        }
    });
    
    // Initial search if there's a value
    if (liveSearchInput.value.trim()) {
        performLiveSearch();
    }
    
    // Clear search button
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            liveSearchInput.value = '';
            performLiveSearch();
            liveSearchInput.focus();
        });
    }
    
    // Update pagination links to preserve the search query
    document.querySelectorAll('.pagination .page-link').forEach(link => {
        if (link.href && !link.parentElement.classList.contains('disabled')) {
            const url = new URL(link.href);
            if (liveSearchInput && liveSearchInput.value) {
                url.searchParams.set('query', liveSearchInput.value);
                link.href = url.toString();
            }
        }
    });
}

/**
 * Make tables responsive by adding data-label attributes
 */
function initializeResponsiveTables() {
    // Only apply to screens below 768px
    if (window.innerWidth > 768) return;
    
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
        // Get all headers
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        
        // Add data-label attribute to each cell in the table body
        table.querySelectorAll('tbody tr').forEach(row => {
            // Skip rows that span multiple columns
            if (row.querySelector('td[colspan]')) return;
            
            row.querySelectorAll('td').forEach((cell, index) => {
                if (headers[index]) {
                    cell.setAttribute('data-label', headers[index]);
                }
            });
        });
    });
}

// Automatic price calculation function for create/edit forms
// DISABLED: replaced with new price-calculator.js
/*
function setupPriceCalculation() {
    console.log('Setting up price calculation...');
    
    const precioSinIva = document.getElementById('precio_sin_iva');
    const precioConIva = document.getElementById('precio_con_iva');
    const ivaSelect = document.getElementById('id_iva');
    
    console.log('Price elements found:', {
        precioSinIva: !!precioSinIva,
        precioConIva: !!precioConIva,
        ivaSelect: !!ivaSelect
    });
    
    if (!precioSinIva || !precioConIva || !ivaSelect) {
        console.log('Missing price calculation elements');
        return;
    }
    
    // Function to get the VAT percentage from the selected option
    function getVatPercentage() {
        const selectedOption = ivaSelect.options[ivaSelect.selectedIndex];
        const vatText = selectedOption.text || '';
        console.log('VAT text:', vatText);
        
        // Try different extraction methods
        let percentValue = 0;
        
        // Method 1: Extract from text like "22%" or "IVA 22%"
        const match = vatText.match(/(\d+(?:\.\d+)?)\s*%/);
        if (match) {
            percentValue = parseFloat(match[1]);
        } else {
            // Method 2: Try value attribute
            const optionValue = selectedOption.value;
            if (optionValue && !isNaN(optionValue)) {
                // If value is a direct percentage
                percentValue = parseFloat(optionValue);
            }
        }
        
        console.log('Extracted VAT percentage:', percentValue);
        return isNaN(percentValue) ? 0 : percentValue / 100;
    }
    
    // Calculate price with VAT from price without VAT
    function calculatePriceWithVat() {
        console.log('Calculating price with VAT...');
        
        if (!precioSinIva.value.trim()) {
            precioConIva.value = '';
            return;
        }
        
        const price = parseFloat(precioSinIva.value.replace(',', '.'));
        console.log('Price without VAT:', price);
        
        if (isNaN(price)) {
            precioConIva.value = '';
            return;
        }
        
        const vatPercentage = getVatPercentage();
        const priceWithVat = price * (1 + vatPercentage);
        console.log('Calculated price with VAT:', priceWithVat);
        
        precioConIva.value = priceWithVat.toFixed(2).replace('.', ',');
    }
    
    // Calculate price without VAT from price with VAT
    function calculatePriceWithoutVat() {
        console.log('Calculating price without VAT...');
        
        if (!precioConIva.value.trim()) {
            precioSinIva.value = '';
            return;
        }
        
        const priceWithVat = parseFloat(precioConIva.value.replace(',', '.'));
        console.log('Price with VAT:', priceWithVat);
        
        if (isNaN(priceWithVat)) {
            precioSinIva.value = '';
            return;
        }
        
        const vatPercentage = getVatPercentage();
        const price = priceWithVat / (1 + vatPercentage);
        console.log('Calculated price without VAT:', price);
        
        precioSinIva.value = price.toFixed(2).replace('.', ',');
    }
    
    // Add event listeners
    precioSinIva.addEventListener('input', function() {
        console.log('Price without VAT input changed');
        calculatePriceWithVat();
    });
    
    precioConIva.addEventListener('input', function() {
        console.log('Price with VAT input changed');
        calculatePriceWithoutVat();
    });
    
    ivaSelect.addEventListener('change', function() {
        console.log('VAT selection changed');
        // Recalculate based on which field has a value
        if (precioSinIva.value.trim()) {
            calculatePriceWithVat();
        } else if (precioConIva.value.trim()) {
            calculatePriceWithoutVat();
        }
    });
    
    console.log('Price calculation setup complete');
}
*/ 