/**
 * Tasks Management JavaScript
 * Centralizes all task-related JavaScript functionality
 */

// Global variables for camera scanning
let codeReader = null;
let scanning = false;

// Wait for jQuery to be loaded before executing any jQuery code
function waitForJQuery(callback) {
    if (typeof $ !== 'undefined' && $.fn && $.fn.jquery) {
        callback();
    } else {
        setTimeout(function() {
            waitForJQuery(callback);
        }, 100);
    }
}

// Initialize when both DOM and jQuery are ready
waitForJQuery(function() {
    $(document).ready(function() {
        // Initialize based on current page
        initializeTasksPage();
    });
});

/**
 * Initialize tasks page functionality based on current page
 */
function initializeTasksPage() {
    const currentPath = window.location.pathname;
    
    // Initialize common functionality
    initializeCommonTasks();
    
    // Page-specific initialization
    if (currentPath.includes('/notifications')) {
        initializeNotifications();
    } else if (currentPath.includes('/scan')) {
        initializeScanPage();
    } else if (currentPath.includes('/task/')) {
        initializeTaskDetail();
    } else if (currentPath.includes('/create')) {
        initializeCreateTask();
    }
}

/**
 * Common task functionality
 */
function initializeCommonTasks() {
    // Update progress bars with animation
    $('.task-progress-fill').each(function() {
        const width = $(this).css('width');
        $(this).css('width', '0').animate({width: width}, 1000);
    });

    // Add tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Auto-refresh functionality for dashboards
    if (window.location.pathname.includes('dashboard')) {
        // Refresh every 30 seconds
        setInterval(function() {
            if (document.visibilityState === 'visible') {
                refreshTaskProgress();
            }
        }, 30000);
    }
}

/**
 * Notifications page functionality
 */
function initializeNotifications() {
    console.log('Initializing notifications page...');
    
    // Tab switching functionality is handled by Bootstrap
    // Additional custom functionality can be added here
}

/**
 * Handle notification click
 */
function handleNotificationClick(notificationId, taskId) {
    // Mark as read and redirect to task detail
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
        console.error('CSRF token not found');
        // Still redirect even if we can't mark as read
        window.location.href = `/tasks/task/${taskId}`;
        return;
    }
    
    $.ajax({
        url: `/tasks/notifications/${notificationId}/read`,
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        data: {
            'csrf_token': csrfToken
        },
        success: function(response) {
            if (response.success) {
                // Redirect to task detail
                window.location.href = `/tasks/task/${taskId}`;
            }
        },
        error: function() {
            // Even if marking as read fails, still redirect
            window.location.href = `/tasks/task/${taskId}`;
        }
    });
}

/**
 * Mark single notification as read
 */
function markAsRead(notificationId) {
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
        console.error('CSRF token not found');
        alert('Errore: Token CSRF non trovato');
        return;
    }
    
    $.ajax({
        url: `/tasks/notifications/${notificationId}/read`,
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        data: {
            'csrf_token': csrfToken
        },
        success: function(response) {
            if (response.success) {
                location.reload();
            }
        },
        error: function(xhr) {
            console.error('Error marking notification as read:', xhr.responseText);
            alert('Errore nel segnare la notifica come letta');
        }
    });
}

/**
 * Mark all notifications as read
 */
function markAllAsRead() {
    if (confirm('Sei sicuro di voler segnare tutte le notifiche come lette?')) {
        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            console.error('CSRF token not found');
            alert('Errore: Token CSRF non trovato');
            return;
        }
        
        $.ajax({
            url: '/tasks/notifications/mark-all-read',
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            data: {
                'csrf_token': csrfToken
            },
            success: function(response) {
                if (response.success) {
                    location.reload();
                } else {
                    alert('Errore nel segnare le notifiche come lette');
                }
            },
            error: function(xhr) {
                console.error('Error marking all notifications as read:', xhr.responseText);
                alert('Errore di connessione');
            }
        });
    }
}

/**
 * Task detail page functionality
 */
function initializeTaskDetail() {
    console.log('Initializing task detail page...');
    
    // Any specific task detail functionality can be added here
}

/**
 * Scan page functionality
 */
function initializeScanPage() {
    console.log('Initializing scan page...');
    
    // Focus on manual input
    $('#manual-code').focus();
    
    // Handle manual form submission
    $('#manual-scan-form').on('submit', function(e) {
        e.preventDefault();
        const code = $('#manual-code').val().trim();
        if (code) {
            processScan(code);
        }
    });
    
    // Auto-submit on Enter in manual input
    $('#manual-code').on('keypress', function(e) {
        if (e.which === 13) {
            $('#manual-scan-form').submit();
        }
    });
    
    // Handle camera controls
    $('#start-camera').on('click', startCamera);
    $('#stop-camera').on('click', stopCamera);
    
    // Cleanup on page unload
    $(window).on('beforeunload', function() {
        if (codeReader) {
            codeReader.reset();
        }
    });
}

/**
 * Start camera for QR code scanning
 */
function startCamera() {
    console.log('Tentativo di avvio camera...');
    
    // Check if browser supports camera
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('Browser non supporta getUserMedia');
        showFeedback('Il browser non supporta l\'accesso alla camera', 'error');
        return;
    }
    
    // Show loading
    showFeedback('Avvio camera...', 'info');
    
    // Initialize code reader if not already done
    if (!codeReader) {
        try {
            codeReader = new ZXing.BrowserQRCodeReader();
            console.log('ZXing BrowserQRCodeReader inizializzato');
        } catch (error) {
            console.error('Errore inizializzazione ZXing:', error);
            showFeedback('Errore nell\'inizializzazione del lettore QR', 'error');
            return;
        }
    }
    
    // Get available video devices first
    console.log('Ricerca dispositivi video...');
    codeReader.getVideoInputDevices()
    .then((videoInputDevices) => {
        console.log('Dispositivi video trovati:', videoInputDevices.length);
        
        if (videoInputDevices.length === 0) {
            throw new Error('Nessuna camera disponibile');
        }
        
        // Try to find rear camera (environment facing)
        let selectedDeviceId = null;
        
        // Look for rear camera keywords
        const rearCameraKeywords = ['back', 'rear', 'environment', 'facing back', 'camera2'];
        const rearCamera = videoInputDevices.find(device => {
            const label = device.label.toLowerCase();
            return rearCameraKeywords.some(keyword => label.includes(keyword));
        });
        
        if (rearCamera) {
            selectedDeviceId = rearCamera.deviceId;
            console.log('Camera posteriore trovata:', rearCamera.label);
        } else {
            // If no rear camera found, use the last camera (often the rear one on mobile)
            selectedDeviceId = videoInputDevices[videoInputDevices.length - 1].deviceId;
            console.log('Usando ultima camera disponibile:', videoInputDevices[videoInputDevices.length - 1].label);
        }
        
        // Start camera with selected device
        return codeReader.decodeFromVideoDevice(selectedDeviceId, 'camera-preview', (result, err) => {
            if (result) {
                console.log('QR Code rilevato:', result.text);
                processScan(result.text);
            }
            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.error('Errore scansione:', err);
            }
        });
    })
    .then(() => {
        // Camera started successfully
        scanning = true;
        $('#start-camera').hide();
        $('#stop-camera').show();
        $('#camera-preview').show();
        showFeedback('Camera avviata! Inquadra il QR code', 'success');
        
        console.log('Camera avviata con successo');
    })
    .catch((err) => {
        console.error('Errore camera completo:', err);
        
        // Fallback: try with basic constraints
        if (err.name !== 'NotAllowedError') {
            console.log('Tentativo fallback con vincoli di base...');
            
            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: { ideal: 'environment' }, // Prefer rear camera
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                } 
            })
            .then((stream) => {
                console.log('Stream camera ottenuto con fallback:', stream);
                
                // Show video element and set stream
                const videoElement = document.getElementById('camera-preview');
                videoElement.srcObject = stream;
                videoElement.style.display = 'block';
                
                // Start QR code detection with stream
                codeReader.decodeFromVideoElement('camera-preview', (result, err) => {
                    if (result) {
                        console.log('QR Code rilevato:', result.text);
                        processScan(result.text);
                    }
                    if (err && !(err instanceof ZXing.NotFoundException)) {
                        console.error('Errore scansione:', err);
                    }
                });
                
                scanning = true;
                $('#start-camera').hide();
                $('#stop-camera').show();
                showFeedback('Camera avviata! Inquadra il QR code', 'success');
            })
            .catch((fallbackErr) => {
                console.error('Errore anche con fallback:', fallbackErr);
                handleCameraError(fallbackErr);
            });
        } else {
            handleCameraError(err);
        }
    });
}

/**
 * Handle camera errors with user-friendly messages
 */
function handleCameraError(err) {
    console.error('Errore camera:', err);
    
    if (err.name === 'NotAllowedError') {
        showFeedback('Permesso camera negato. Abilita l\'accesso alla camera nelle impostazioni del browser.', 'error');
    } else if (err.name === 'NotFoundError') {
        showFeedback('Nessuna camera trovata sul dispositivo', 'error');
    } else if (err.name === 'NotReadableError') {
        showFeedback('Camera già in uso da un\'altra applicazione', 'error');
    } else if (err.name === 'OverconstrainedError') {
        showFeedback('Camera non supporta le impostazioni richieste. Prova con un altro dispositivo.', 'error');
    } else {
        showFeedback('Errore nell\'accesso alla camera: ' + (err.message || 'Errore sconosciuto'), 'error');
    }
}

/**
 * Stop camera scanning
 */
function stopCamera() {
    if (codeReader) {
        codeReader.reset();
        scanning = false;
        $('#camera-preview').hide();
        $('#start-camera').show();
        $('#stop-camera').hide();
        showFeedback('Camera fermata', 'info');
    }
}

/**
 * Process scanned code
 */
function processScan(code) {
    if (!code) return;
    
    // Clear manual input
    $('#manual-code').val('');
    
    // Show processing feedback
    showFeedback('Elaborazione...', 'info');
    
    // Get task ticket ID from URL or data attribute
    const taskTicketId = getTaskTicketId();
    
    if (!taskTicketId) {
        showFeedback('Errore: ID ticket non trovato', 'error');
        return;
    }
    
    // Get CSRF token
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
        showFeedback('Errore: Token CSRF non trovato', 'error');
        return;
    }
    
    // Send scan to server using the new API
    $.ajax({
        url: '/tasks/api/scan',
        method: 'POST',
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': csrfToken
        },
        data: JSON.stringify({
            'task_ticket_id': taskTicketId,
            'scanned_code': code,
            'csrf_token': csrfToken
        }),
        success: function(response) {
            if (response.success) {
                showFeedback(response.message, 'success');
                
                // Handle different completion scenarios
                setTimeout(function() {
                    if (response.task_completed) {
                        // Task completed - redirect to user dashboard
                        showFeedback('🎉 Task completato! Ritorno alla dashboard...', 'success');
                        setTimeout(function() {
                            window.location.href = '/tasks/user';
                        }, 2000);
                    } else if (response.ticket_completed && response.next_ticket_id) {
                        // Current ticket completed, move to next ticket
                        showFeedback('Ticket completato! Passaggio al prossimo...', 'success');
                        setTimeout(function() {
                            window.location.href = `/tasks/ticket/${response.next_ticket_id}/scan`;
                        }, 1500);
                    } else {
                        // Product scanned successfully, reload to show next product
                        window.location.reload();
                    }
                }, 1500);
            } else {
                showFeedback(response.message || 'Errore nella scansione', 'error');
                
                // Focus back on manual input for retry
                setTimeout(function() {
                    $('#manual-code').focus();
                }, 2000);
            }
        },
        error: function(xhr, status, error) {
            console.error('Scan error:', xhr.responseText, error);
            
            let errorMessage = 'Errore di connessione';
            if (xhr.status === 400) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.message || response.error || 'Errore 400 - Richiesta non valida';
                } catch (e) {
                    errorMessage = 'Errore 400 - Richiesta non valida';
                }
            } else if (xhr.status === 403) {
                errorMessage = 'Errore 403 - Token CSRF non valido';
            } else if (xhr.status === 500) {
                errorMessage = 'Errore 500 - Errore interno del server';
            }
            
            showFeedback(errorMessage, 'error');
            
            // Focus back on manual input for retry
            setTimeout(function() {
                $('#manual-code').focus();
            }, 2000);
        }
    });
}

/**
 * Show feedback message
 */
function showFeedback(message, type) {
    const feedback = $('#scan-feedback');
    const content = $('#feedback-content');
    
    if (feedback.length === 0 || content.length === 0) {
        // Fallback to alert if feedback elements don't exist
        alert(message);
        return;
    }
    
    const icon = type === 'success' ? 'check' : type === 'error' ? 'times' : 'spinner fa-spin';
    content.html(`<i class="fas fa-${icon}"></i> ${message}`);
    feedback.removeClass('success error info').addClass(type).fadeIn();
    
    if (type !== 'info') {
        setTimeout(function() {
            feedback.fadeOut();
        }, 2000);
    }
}

/**
 * Create task page functionality
 */
function initializeCreateTask() {
    console.log('Initializing create task page...');
    
    // Ticket selection functionality
    $('.ticket-checkbox').on('change', function() {
        updateTicketSelection($(this));
        updateSummary();
    });
    
    // Click on ticket card to toggle selection
    $('.ticket-card-minimal').on('click', function(e) {
        // Don't trigger if clicking directly on checkbox or label
        if (e.target.type === 'checkbox' || e.target.tagName === 'LABEL') {
            return;
        }
        
        const checkbox = $(this).find('.ticket-checkbox');
        checkbox.prop('checked', !checkbox.prop('checked')).trigger('change');
    });
    
    // Select all tickets
    $('#selectAllBtn').on('click', function() {
        $('.ticket-checkbox').prop('checked', true);
        $('.ticket-card-minimal').addClass('selected');
        updateSummary();
    });
    
    // Deselect all tickets
    $('#deselectAllBtn').on('click', function() {
        $('.ticket-checkbox').prop('checked', false);
        $('.ticket-card-minimal').removeClass('selected');
        updateSummary();
    });
    
    // Form submission validation
    $('#createTaskForm').on('submit', function(e) {
        const selectedCount = $('.ticket-checkbox:checked').length;
        
        if (selectedCount === 0) {
            e.preventDefault();
            alert('Seleziona almeno un ticket per creare il task!');
            return false;
        }

        const title = $('#title').val().trim();
        if (!title) {
            e.preventDefault();
            alert('Inserisci un titolo per il task!');
            $('#title').focus();
            return false;
        }

        // Show loading state
        showLoading('#createTaskBtn', 'Creazione in corso...');
        showLoading('#createButtonMain', 'Creazione in corso...');
    });
    
    // Initial summary update
    updateSummary();
}

/**
 * Update ticket selection visual state
 */
function updateTicketSelection(checkbox) {
    const ticketCard = checkbox.closest('.ticket-card-minimal');
    const isChecked = checkbox.prop('checked');
    
    if (isChecked) {
        ticketCard.addClass('selected');
    } else {
        ticketCard.removeClass('selected');
    }
}

/**
 * Update selected tickets summary
 */
function updateSummary() {
    const selectedTickets = $('.ticket-checkbox:checked');
    const selectedCount = selectedTickets.length;
    let totalLines = 0;
    let totalProducts = 0;

    selectedTickets.each(function() {
        const ticketCard = $(this).closest('.ticket-card-minimal');
        
        // Count lines from badge
        const linesText = ticketCard.find('.badge.bg-info').text();
        const lines = parseInt(linesText.split(' ')[0]) || 0;
        totalLines += lines;
        
        // For products, use the same number as lines since each line is a product
        totalProducts += lines;
    });

    // Update counters
    $('#selectedCount').text(selectedCount + ' selezionati');
    $('#summaryTicketCount').text(selectedCount);
    $('#summaryLineCount').text(totalLines);
    $('#summaryProductCount').text(totalProducts);

    // Show/hide summary and enable/disable buttons
    if (selectedCount > 0) {
        $('#selectedSummary').slideDown();
        $('#createTaskBtn, #createButtonMain').prop('disabled', false);
        $('#createButtonContainer').hide();
    } else {
        $('#selectedSummary').slideUp();
        $('#createTaskBtn, #createButtonMain').prop('disabled', true);
        $('#createButtonContainer').show();
    }
}

/**
 * Refresh task progress (for auto-refresh functionality)
 */
function refreshTaskProgress() {
    const taskId = getTaskIdFromUrl();
    if (!taskId) return;
    
    $.ajax({
        url: `/tasks/api/tasks/${taskId}/progress`,
        method: 'GET',
        success: function(data) {
            // Update progress bars and counters
            updateTaskProgressDisplay(data);
        },
        error: function() {
            console.log('Failed to refresh task progress');
        }
    });
}

/**
 * Update task progress display
 */
function updateTaskProgressDisplay(data) {
    // Update progress percentage
    $('.task-progress-fill').css('width', data.progress_percentage + '%');
    
    // Update counters
    $('.completed-tickets-count').text(data.completed_tickets);
    $('.total-tickets-count').text(data.total_tickets);
    
    // Update status badge if needed
    if (data.status) {
        $('.task-status-badge').removeClass().addClass(`task-status-badge task-status-${data.status}`);
    }
}

/**
 * Utility functions
 */

/**
 * Get task ticket ID from URL or data attributes
 */
function getTaskTicketId() {
    // Try to get from URL
    const urlParts = window.location.pathname.split('/');
    const ticketIndex = urlParts.indexOf('ticket');
    if (ticketIndex !== -1 && urlParts[ticketIndex + 1]) {
        return urlParts[ticketIndex + 1];
    }
    
    // Try to get from data attribute
    const taskTicketId = $('[data-task-ticket-id]').data('task-ticket-id');
    if (taskTicketId) {
        return taskTicketId;
    }
    
    return null;
}

/**
 * Get task ID from URL
 */
function getTaskIdFromUrl() {
    const urlParts = window.location.pathname.split('/');
    const taskIndex = urlParts.indexOf('task');
    if (taskIndex !== -1 && urlParts[taskIndex + 1]) {
        return urlParts[taskIndex + 1];
    }
    return null;
}

/**
 * Get CSRF token
 */
function getCSRFToken() {
    // Try global token first
    if (typeof window.csrfToken !== 'undefined') {
        return window.csrfToken;
    }
    
    // Fallback to searching in the DOM (if jQuery is available)
    if (typeof $ !== 'undefined') {
        return $('meta[name=csrf-token]').attr('content') || $('input[name=csrf_token]').val();
    }
    
    // Final fallback - search directly in the DOM
    const metaToken = document.querySelector('meta[name=csrf-token]');
    if (metaToken) {
        return metaToken.getAttribute('content');
    }
    
    const inputToken = document.querySelector('input[name=csrf_token]');
    if (inputToken) {
        return inputToken.value;
    }
    
    console.error('CSRF token not found');
    return null;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('it-IT', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Show loading state
 */
function showLoading(element) {
    if (typeof element === 'string') {
        element = $(element);
    }
    element.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Caricamento...');
}

/**
 * Hide loading state
 */
function hideLoading(element, originalText) {
    if (typeof element === 'string') {
        element = $(element);
    }
    element.prop('disabled', false).html(originalText);
}

// Export functions for global access
window.TasksJS = {
    handleNotificationClick,
    markAsRead,
    markAllAsRead,
    startCamera,
    stopCamera,
    processScan,
    showFeedback,
    updateTicketSelection,
    updateSummary,
    refreshTaskProgress,
    getTaskTicketId,
    getTaskIdFromUrl,
    getCSRFToken,
    formatDate,
    showLoading,
    hideLoading,
    handleCameraError
}; 