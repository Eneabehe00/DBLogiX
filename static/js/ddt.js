/**
 * DDT.js - Funzioni essenziali per la gestione DDT
 * Versione ripulita - Le funzioni di editing sono ora in ddt_ticket_editor.js
 */

// Initialize select2 for client search
function initClientSearch() {
    $('#clientSearch').select2({
        placeholder: 'Cerca cliente per nome...',
        allowClear: true,
        minimumInputLength: 2,
        ajax: {
            url: '/clients/api/search',
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    q: params.term,
                    page: params.page
                };
            },
            processResults: function (data, params) {
                params.page = params.page || 1;
                return {
                    results: data.results,
                    pagination: {
                        more: (params.page * 10) < data.total_count
                    }
                };
            },
            cache: true
        },
        templateResult: function(result) {
            if (result.loading) {
                return result.text;
            }
            return $('<span>' + result.text + '</span>');
        },
        templateSelection: function(selection) {
            return selection.text;
        }
    });
}

// Carica prezzi modificati (legacy)
function loadModifiedPrices() {
    fetch('/ddt/api/get_modified_prices')
    .then(response => response.json())
    .then(data => {
        if (data.success && data.modified_prices) {
            Object.entries(data.modified_prices).forEach(([ticketId, price]) => {
                const priceElement = $(`.editable-price[data-ticket-id="${ticketId}"] .price-value`);
                if (priceElement.length) {
                    priceElement.text(parseFloat(price).toFixed(2));
                    priceElement.parent().addClass('price-modified');
                }
            });
            updateTotals();
        }
    })
    .catch(error => {
        console.error('Errore caricamento prezzi modificati:', error);
    });
}

// Inizializzazione prezzi (legacy - mantenuto per compatibilità)
function initPriceEditing() {
    loadModifiedPrices();
    console.log('🔄 Sistema prezzi legacy caricato - Editor moderno disponibile in DDT Ticket Editor');
}

// Aggiorna totali
function updateTotals() {
    let totalAmount = 0;
    
    $('.price-value').each(function() {
        const priceText = $(this).text().replace(/[€\s]/g, '');
        const price = parseFloat(priceText) || 0;
        totalAmount += price;
    });
    
    $('#total-amount').text(`€ ${totalAmount.toFixed(2)}`);
}

// Funzione per mostrare notifiche (legacy)
function showNotification(message, type = 'info') {
    const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-danger' : 'alert-info';
    
    const notification = $(`
        <div class="alert ${alertClass} alert-dismissible fade show notification-toast" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `);
    
    $('body').append(notification);
    
    setTimeout(() => {
        notification.alert('close');
    }, 3000);
}

// Initialize when document is ready
$(document).ready(function() {
    // Check which page we're on and initialize the appropriate functionality
    if ($('#clientSearch').length) {
        initClientSearch();
    }
    
    if ($('.editable-price').length) {
        initPriceEditing();
    }
    
    console.log('✅ DDT.js inizializzato (versione ripulita)');
});
