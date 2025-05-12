/**
 * Debug script for DDT functionality
 */
$(document).ready(function() {
    console.log('Debug script loaded');
    
    // Debug client and form info
    var clientId = $('#ddtForm input[name="cliente_id"]').val();
    var empresaId = $('#ddtForm input[name="id_empresa"]').val();
    console.log('Client ID:', clientId);
    console.log('Empresa ID:', empresaId);
    
    // Check CSRF token
    console.log('CSRF Token exists:', $('#ddtForm input[name="csrf_token"]').length > 0);
    if ($('#ddtForm input[name="csrf_token"]').length > 0) {
        console.log('CSRF Token value:', $('#ddtForm input[name="csrf_token"]').val());
    }
    
    // Log form details
    console.log('Form action:', $('#ddtForm').attr('action'));
    console.log('Form method:', $('#ddtForm').attr('method'));
    
    // Add global AJAX error handler
    $(document).ajaxError(function(event, jqXHR, ajaxSettings, thrownError) {
        console.error('AJAX Error:', thrownError);
        console.error('Status:', jqXHR.status);
        console.error('Response Text:', jqXHR.responseText);
        console.error('URL:', ajaxSettings.url);
    });

    // Override form submission to check data
    $('#ddtForm').submit(function(e) {
        var ticketsData = $('#selectedTickets').val();
        console.log('Form submitted with tickets data:', ticketsData);
        
        // Check if data is valid JSON
        try {
            var ticketsObj = JSON.parse(ticketsData);
            console.log('Valid JSON data with', ticketsObj.length, 'tickets');
        } catch (error) {
            console.error('Invalid JSON data:', error);
            alert('Errore nei dati del form. Controlla la console per i dettagli.');
            e.preventDefault();
            return false;
        }
        
        // If the tickets array is empty, prevent submission
        if (!ticketsObj || ticketsObj.length === 0) {
            console.error('No tickets selected');
            alert('Seleziona almeno un ticket per creare il DDT.');
            e.preventDefault();
            return false;
        }
        
        // Log all form data
        var formData = new FormData(this);
        for (var pair of formData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }
        
        return true;
    });
}); 