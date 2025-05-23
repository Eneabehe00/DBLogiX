/**
 * DDT (Documento Di Trasporto) JavaScript functionality
 */

// Initialize select2 for client search
function initClientSearch() {
    $('#clientSearch').select2({
        placeholder: 'Cerca cliente per nome...',
        allowClear: true,
        minimumInputLength: 3,
        ajax: {
            url: '/ddt/api/clients/search',
            dataType: 'json',
            delay: 250,
            data: function(params) {
                return {
                    term: params.term
                };
            },
            processResults: function(data) {
                return {
                    results: data
                };
            },
            cache: true
        }
    });
    
    // Update form fields when a client is selected
    $('#clientSearch').on('select2:select', function(e) {
        var data = e.params.data;
        
        // Update form fields
        $('#cliente_id').val(data.id);
        $('#cliente_nome').val(data.nombre);
        
        // Update client details card
        $('#clientName').text(data.nombre);
        $('#clientAddress').text(data.direccion || 'Indirizzo non disponibile');
        $('#clientVAT').text('P.IVA/CF: ' + (data.dni || 'Non disponibile'));
        
        // Show client details and enable submit button
        $('#clientDetails').removeClass('d-none');
        $('#submitBtn').prop('disabled', false);
    });
    
    // Clear form fields when select is cleared
    $('#clientSearch').on('select2:clear', function() {
        $('#cliente_id').val('');
        $('#cliente_nome').val('');
        $('#clientDetails').addClass('d-none');
        $('#submitBtn').prop('disabled', true);
    });
}

// Initialize ticket selection functionality
function initTicketSelection() {
    // Select all checkbox functionality
    $('#selectAll').change(function() {
        $('.ticket-check').prop('checked', $(this).prop('checked'));
        updateCreateButton();
    });
    
    // Update create button state when individual checkboxes change
    $('.ticket-check').change(function() {
        updateCreateButton();
    });
    
    // Create DDT button click handler
    $('#createDDT').click(function() {
        // Collect selected tickets
        const selectedTickets = [];
        $('.ticket-check:checked').each(function() {
            const $this = $(this);
            selectedTickets.push({
                id_ticket: $this.data('ticket'),
                id_empresa: $this.data('empresa'),
                id_tienda: $this.data('tienda'),
                id_balanza_maestra: $this.data('balanza-maestra'),
                id_balanza_esclava: $this.data('balanza-esclava'),
                tipo_venta: $this.data('tipo-venta')
            });
        });
        
        // Ensure we have tickets selected
        if (selectedTickets.length === 0) {
            alert('Seleziona almeno un ticket per creare il DDT.');
            return;
        }
        
        // Update form and submit
        $('#selectedTickets').val(JSON.stringify(selectedTickets));
        
        // For debugging
        console.log('Submitting tickets:', selectedTickets);
        console.log('Form data:', $('#selectedTickets').val());
        
        $('#ddtForm').submit();
    });
    
    // View ticket details
    $('.view-ticket').click(function() {
        const ticketId = $(this).data('ticket');
        const empresaId = $(this).data('empresa');
        
        // Show loader, hide details and errors
        $('#ticketLoader').removeClass('d-none');
        $('#ticketDetails').addClass('d-none');
        $('#ticketError').addClass('d-none');
        
        // Make an AJAX call to get ticket details
        $.ajax({
            url: '/ddt/ticket_details/' + ticketId + '/' + empresaId,
            method: 'GET',
            timeout: 30000, // Increased timeout to 30 seconds
            success: function(response) {
                $('#ticketLoader').addClass('d-none');
                
                if (response.success) {
                    $('#ticketDetails').removeClass('d-none');
                    $('#ticketId').text(response.ticket.id);
                    $('#ticketDate').text(response.ticket.date);
                    
                    // Clear and populate ticket items
                    $('#ticketItems').empty();
                    
                    response.items.forEach(item => {
                        $('#ticketItems').append(`
                            <tr>
                                <td>${item.id}</td>
                                <td>${item.description}</td>
                                <td>${item.quantity}</td>
                                <td>${item.price}</td>
                            </tr>
                        `);
                    });
                } else {
                    // Show error
                    $('#ticketError').removeClass('d-none').text(response.error || 'Errore durante il caricamento dei dettagli del ticket.');
                    console.error('Errore risposta server:', response);
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $('#ticketLoader').addClass('d-none');
                $('#ticketError').removeClass('d-none').text('Errore di connessione al server. Riprova più tardi.');
                console.error('Errore AJAX:', textStatus, errorThrown);
                console.error('Stato risposta:', jqXHR.status);
                console.error('Dettagli risposta:', jqXHR.responseText);
            }
        });
    });
}

// Helper function to update create button state
function updateCreateButton() {
    const selectedCount = $('.ticket-check:checked').length;
    $('#createDDT').prop('disabled', selectedCount === 0);
    if (selectedCount > 0) {
        $('#createDDT').html(`<i class="fas fa-file-invoice"></i> Crea DDT (${selectedCount})`);
    } else {
        $('#createDDT').html('<i class="fas fa-file-invoice"></i> Crea DDT');
    }
}

// Initialize when the document is ready
$(document).ready(function() {
    // Check which page we're on and initialize the appropriate functionality
    if ($('#clientSearch').length) {
        initClientSearch();
    }
    
    if ($('.ticket-check').length) {
        initTicketSelection();
    }
}); 