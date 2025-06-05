/**
 * Tasks Management JavaScript
 * Centralizes all task-related JavaScript functionality
 */

// Global variables for camera scanning
let codeReader = null;
let scanning = false;

/**
 * Camera Preferences Management
 * Stores and retrieves user's preferred camera choice permanently
 */
const CameraPreferences = {
    // Key for localStorage
    STORAGE_KEY: 'dblogix_camera_preference',
    
    /**
     * Save user's preferred camera deviceId
     */
    savePreferredCamera: function(deviceId, deviceLabel) {
        try {
            const preference = {
                deviceId: deviceId,
                deviceLabel: deviceLabel,
                timestamp: Date.now(),
                userAgent: navigator.userAgent
            };
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(preference));
            console.log('💾 Camera preference saved:', deviceLabel);
        } catch (error) {
            console.error('❌ Error saving camera preference:', error);
        }
    },
    
    /**
     * Get user's preferred camera deviceId
     */
    getPreferredCamera: function() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                const preference = JSON.parse(stored);
                console.log('📖 Loaded camera preference:', preference.deviceLabel);
                return preference;
            }
        } catch (error) {
            console.error('❌ Error loading camera preference:', error);
        }
        return null;
    },
    
    /**
     * Clear saved camera preference
     */
    clearPreference: function() {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
            console.log('🗑️ Camera preference cleared');
        } catch (error) {
            console.error('❌ Error clearing camera preference:', error);
        }
    },
    
    /**
     * Check if a saved camera device still exists in available devices
     */
    isPreferredCameraAvailable: function(videoDevices, preferredDeviceId) {
        return videoDevices.some(device => device.deviceId === preferredDeviceId);
    }
};

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
    
    // Handle clickable cards
    $('.clickable-card').click(function(e) {
        // Prevent click if target is a button or link
        if ($(e.target).is('button') || $(e.target).closest('button').length || 
            $(e.target).is('a') || $(e.target).closest('a').length) {
            return;
        }
        
        const href = $(this).data('href');
        if (href) {
            window.location.href = href;
        }
    });
    
    // Add cursor pointer style to clickable cards
    $('.clickable-card').css('cursor', 'pointer');
    
    // Handle ticket removal buttons
    $('.btn-remove-ticket').click(function(e) {
        e.preventDefault();
        e.stopPropagation(); // Prevent card click
        
        const taskTicketId = $(this).data('task-ticket-id');
        const ticketNumber = $(this).data('ticket-number');
        
        if (confirm(`Sei sicuro di voler rimuovere il ticket #${ticketNumber} dal task?`)) {
            // Create and submit form for ticket removal
            const form = $('<form>', {
                'method': 'POST',
                'action': '/tasks/remove-ticket'
            });
            
            // Add CSRF token
            const csrfToken = getCSRFToken();
            if (csrfToken) {
                form.append($('<input>', {
                    'type': 'hidden',
                    'name': 'csrf_token',
                    'value': csrfToken
                }));
            }
            
            // Add task_ticket_id
            form.append($('<input>', {
                'type': 'hidden',
                'name': 'task_ticket_id',
                'value': taskTicketId
            }));
            
            // Add task_id from current URL
            const taskId = getTaskIdFromUrl();
            if (taskId) {
                form.append($('<input>', {
                    'type': 'hidden',
                    'name': 'task_id',
                    'value': taskId
                }));
            }
            
            // Append form to body and submit
            form.appendTo('body').submit();
        }
    });
    
    // Handle task removal buttons
    $('.btn-remove-task').click(function(e) {
        e.preventDefault();
        e.stopPropagation(); // Prevent card click
        
        const taskId = $(this).data('task-id');
        const taskNumber = $(this).data('task-number');
        
        if (confirm(`Sei sicuro di voler eliminare il task ${taskNumber}? Questa azione è irreversibile.`)) {
            // Create and submit form for task deletion
            const form = $('<form>', {
                'method': 'POST',
                'action': `/tasks/task/${taskId}/delete`
            });
            
            // Add CSRF token
            const csrfToken = getCSRFToken();
            if (csrfToken) {
                form.append($('<input>', {
                    'type': 'hidden',
                    'name': 'csrf_token',
                    'value': csrfToken
                }));
            }
            
            // Append form to body and submit
            form.appendTo('body').submit();
        }
    });
    
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
 * Start camera for QR code scanning - Enhanced Android Support with Camera Switch
 */
function startCamera() {
    console.log('🔍 Tentativo di avvio camera...');
    
    // Hide starting message immediately
    $('#camera-starting').hide();
    
    // Check if browser supports camera
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('Browser non supporta getUserMedia');
        showFeedback('Il browser non supporta l\'accesso alla camera', 'error');
        $('#start-camera').show();
        return;
    }
    
    // Show processing feedback
    showFeedback('🔍 Avvio camera...', 'info');
    
    // Initialize code reader if not already done
    if (!codeReader) {
        try {
            codeReader = new ZXing.BrowserQRCodeReader();
            console.log('✅ ZXing BrowserQRCodeReader inizializzato');
        } catch (error) {
            console.error('❌ Errore inizializzazione ZXing:', error);
            showFeedback('Errore nell\'inizializzazione del lettore QR', 'error');
            $('#start-camera').show();
            return;
        }
    }
    
    // Enhanced mobile detection
    const isMobile = window.innerWidth <= 768;
    const isAndroid = /Android/i.test(navigator.userAgent);
    
    console.log(`📱 Dispositivo: ${isAndroid ? 'Android' : 'Altri'} - Mobile: ${isMobile}`);
    
    // Step 1: Get camera permissions first, then enumerate devices
    console.log('🔍 Richiesta permessi camera...');
    navigator.mediaDevices.getUserMedia({
        video: true,  // Basic permission request
        audio: false
    })
    .then((tempStream) => {
        console.log('✅ Permessi camera ottenuti');
        
        // Stop temporary stream immediately
        tempStream.getTracks().forEach(track => track.stop());
        
        // Now enumerate devices with permission granted
        return navigator.mediaDevices.enumerateDevices();
    })
    .then((devices) => {
        console.log(`📷 Dispositivi totali trovati: ${devices.length}`);
        
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        console.log(`📷 Dispositivi video: ${videoDevices.length}`);
        
        // Log all video devices for debugging
        videoDevices.forEach((device, index) => {
            console.log(`📷 Device ${index}: "${device.label}" (ID: ${device.deviceId.substr(0, 10)}...)`);
        });
        
        if (videoDevices.length === 0) {
            throw new Error('Nessuna camera video disponibile');
        }
        
        // Enhanced device selection strategy
        let selectedDevice = null;
        
        // STEP 1: Check for saved user preference first
        const savedPreference = CameraPreferences.getPreferredCamera();
        if (savedPreference && CameraPreferences.isPreferredCameraAvailable(videoDevices, savedPreference.deviceId)) {
            selectedDevice = videoDevices.find(device => device.deviceId === savedPreference.deviceId);
            if (selectedDevice) {
                console.log('✅ Using saved camera preference:', savedPreference.deviceLabel);
                console.log('🎯 Preferred camera restored from memory');
            }
        }
        
        // STEP 2: If no saved preference or device not available, use platform-specific logic
        if (!selectedDevice) {
            console.log('🔍 No saved preference, using automatic detection...');
            
            if (isAndroid) {
                console.log('📱 Strategia Android: selezione camera posteriore principale 1X...');
                
                // Android Strategy: Look for MAIN rear camera (1X) indicators, exclude ultra-wide and telephoto
                const mainRearKeywords = [
                    'back', 'rear', 'environment', 'facing back', 'main', 'primary',
                    'camera 0', 'camera0', 'camera 1', 'camera1', 'camera2', 'camera 2',
                    'posteriore', 'trasera', 'hinten', 'arrière', '后', '後ろ',
                    'facing: environment'
                ];
                
                // Keywords to EXCLUDE (ultra-wide, telephoto, macro)
                const excludeKeywords = [
                    'ultra', 'wide', 'telephoto', 'zoom', 'macro', 'tele', 'periscope',
                    '0.5x', '0.5', 'ultrawide', 'ultra-wide', '2x', '3x', '5x', '10x',
                    'ultra wide', 'ultra_wide', 'wide angle', 'wide_angle'
                ];
                
                // Strategy 1: Find main rear camera, excluding specialty cameras
                selectedDevice = videoDevices.find(device => {
                    const label = device.label.toLowerCase();
                    
                    // Must have rear camera indicators
                    const hasRearKeyword = mainRearKeywords.some(keyword => label.includes(keyword));
                    
                    // Must NOT have exclude keywords (ultra-wide, telephoto, etc.)
                    const hasExcludeKeyword = excludeKeywords.some(keyword => label.includes(keyword));
                    
                    const isMainRear = hasRearKeyword && !hasExcludeKeyword;
                    
                    console.log(`📷 Checking "${device.label}": rear=${hasRearKeyword}, exclude=${hasExcludeKeyword}, main=${isMainRear}`);
                    return isMainRear;
                });
                
                // Strategy 2: If no specific main rear found, use device enumeration logic for main camera
                if (!selectedDevice && videoDevices.length >= 2) {
                    // On Android, typically:
                    // - Device 0: Usually main rear camera (1X)
                    // - Device 1: Usually front camera
                    // - Device 2+: Usually ultra-wide, telephoto, etc.
                    selectedDevice = videoDevices[0];
                    console.log('📷 Android: Usando prima camera (main rear 1X)');
                }
                
                // Strategy 3: Last resort - use any available device
                if (!selectedDevice) {
                    selectedDevice = videoDevices[0];
                    console.log('📷 Android: Usando camera disponibile');
                }
                
            } else {
                // Non-Android devices (iOS, etc.): Use enhanced approach for main rear camera
                console.log('📱 Strategia iOS/Altri: selezione camera posteriore principale 1X...');
                
                // iOS Strategy: Look for main rear camera, exclude ultra-wide and telephoto
                const mainRearKeywords = ['back', 'rear', 'environment', 'facing back', 'main', 'primary'];
                const excludeKeywords = [
                    'ultra', 'wide', 'telephoto', 'zoom', 'macro', 'tele', 
                    '0.5x', '0.5', 'ultrawide', 'ultra-wide', '2x', '3x', '5x',
                    'ultra wide', 'ultra_wide', 'wide angle'
                ];
                
                // Find main rear camera excluding specialty cameras
                selectedDevice = videoDevices.find(device => {
                    const label = device.label.toLowerCase();
                    const hasRearKeyword = mainRearKeywords.some(keyword => label.includes(keyword));
                    const hasExcludeKeyword = excludeKeywords.some(keyword => label.includes(keyword));
                    const isMainRear = hasRearKeyword && !hasExcludeKeyword;
                    
                    console.log(`📷 iOS Checking "${device.label}": rear=${hasRearKeyword}, exclude=${hasExcludeKeyword}, main=${isMainRear}`);
                    return isMainRear;
                });
                
                // Fallback: use standard logic but prefer non-specialty cameras
                if (!selectedDevice) {
                    // Try to avoid ultra-wide/telephoto cameras
                    const nonSpecialtyDevices = videoDevices.filter(device => {
                        const label = device.label.toLowerCase();
                        return !excludeKeywords.some(keyword => label.includes(keyword));
                    });
                    
                    if (nonSpecialtyDevices.length > 0) {
                        selectedDevice = nonSpecialtyDevices[nonSpecialtyDevices.length - 1]; // Last non-specialty device
                        console.log('📷 iOS: Usando camera non-specialty');
                    } else {
                        selectedDevice = videoDevices[videoDevices.length - 1]; // Fallback to any device
                        console.log('📷 iOS: Fallback camera generica');
                    }
                }
            }
        }
        
        console.log(`🎯 Camera selezionata: "${selectedDevice.label}" (ID: ${selectedDevice.deviceId.substr(0, 10)}...)`);
        
        // Enhanced logging to identify camera type
        const label = selectedDevice.label.toLowerCase();
        let cameraType = 'Unknown';
        if (label.includes('front') || label.includes('user') || label.includes('facing')) {
            cameraType = 'Front/User Camera';
        } else if (label.includes('ultra') || label.includes('wide') || label.includes('0.5')) {
            cameraType = 'Ultra-Wide Camera (⚠️ Non ideale per QR)';
        } else if (label.includes('telephoto') || label.includes('tele') || label.includes('zoom') || label.includes('2x') || label.includes('3x')) {
            cameraType = 'Telephoto Camera (⚠️ Non ideale per QR)';
        } else if (label.includes('macro')) {
            cameraType = 'Macro Camera (⚠️ Non ideale per QR)';
        } else if (label.includes('back') || label.includes('rear') || label.includes('environment') || label.includes('main') || label.includes('primary')) {
            cameraType = '✅ Main Rear Camera (1X) - Ideale per QR';
        }
        
        console.log(`📷 Tipo camera identificato: ${cameraType}`);
        
        // SAVE FIRST-TIME PREFERENCE: If no saved preference existed, save this selection
        if (!savedPreference) {
            CameraPreferences.savePreferredCamera(selectedDevice.deviceId, selectedDevice.label);
            console.log('💾 First-time camera preference saved');
        }
        
        // Store current device for switching (Android only)
        if (isAndroid) {
            window.currentCameraIndex = videoDevices.findIndex(d => d.deviceId === selectedDevice.deviceId);
            window.availableCameras = videoDevices;
            console.log(`📱 Android: Camera index ${window.currentCameraIndex} di ${videoDevices.length}`);
        }
        
        // Start camera with selected device using deviceId constraint
        const constraints = {
            video: {
                deviceId: { exact: selectedDevice.deviceId }, // Use exact deviceId
                width: { ideal: 1920, min: 640 },
                height: { ideal: 1080, min: 480 }
            }
        };
        
        console.log('🎥 Avvio camera con deviceId specifico...');
        return codeReader.decodeFromVideoDevice(selectedDevice.deviceId, 'camera-preview', (result, err) => {
            if (result) {
                console.log('🎯 QR Code rilevato:', result.text);
                
                // Add haptic feedback for successful scan
                if ('vibrate' in navigator) {
                    navigator.vibrate([100, 50, 100]); // Success pattern
                }
                
                processScan(result.text);
            }
            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.error('⚠️ Errore scansione:', err);
            }
        });
    })
    .then(() => {
        // Camera started successfully
        scanning = true;
        
        // Update UI
        $('#start-camera').hide();
        $('#stop-camera').show();
        $('#camera-preview').show();
        
        // Show switch camera button only for Android with multiple cameras
        if (isAndroid && window.availableCameras && window.availableCameras.length > 1) {
            $('#switch-camera').show();
            console.log('📱 Tasto switch camera abilitato per Android');
        }
        
        // Mobile-specific UI updates
        if (isMobile) {
            // Add mobile-specific styles
            const video = document.getElementById('camera-preview');
            if (video) {
                video.style.borderRadius = '15px';
                video.style.width = '100%';
                video.style.height = 'auto';
                video.style.maxHeight = '60vh';
                video.style.objectFit = 'cover';
            }
        }
        
        showFeedback('📱 Camera avviata! Inquadra il QR code', 'success');
        
        // Trigger custom event for mobile optimizations
        $(document).trigger('cameraStarted');
        
        console.log('✅ Camera avviata con successo');
    })
    .catch((err) => {
        console.error('❌ Errore camera completo:', err);
        handleCameraError(err);
    });
}

/**
 * Switch camera function - Android only with Permanent Preference Storage and Main Camera Priority
 */
function switchCamera() {
    if (!window.availableCameras || window.availableCameras.length <= 1) {
        console.log('📷 Nessuna camera alternativa disponibile');
        return;
    }
    
    console.log('🔄 Switch camera...');
    
    // Stop current camera
    if (codeReader) {
        codeReader.reset();
    }
    
    // Enhanced switching logic: prioritize main cameras over specialty cameras
    const currentCamera = window.availableCameras[window.currentCameraIndex];
    const excludeKeywords = [
        'ultra', 'wide', 'telephoto', 'zoom', 'macro', 'tele', 'periscope',
        '0.5x', '0.5', 'ultrawide', 'ultra-wide', '2x', '3x', '5x', '10x',
        'ultra wide', 'ultra_wide', 'wide angle', 'wide_angle'
    ];
    
    // Find next suitable camera (prefer main cameras)
    let nextCameraIndex = (window.currentCameraIndex + 1) % window.availableCameras.length;
    let attempts = 0;
    
    // Try to find a non-specialty camera first
    while (attempts < window.availableCameras.length) {
        const candidateCamera = window.availableCameras[nextCameraIndex];
        const label = candidateCamera.label.toLowerCase();
        const isSpecialtyCamera = excludeKeywords.some(keyword => label.includes(keyword));
        
        console.log(`🔄 Evaluating camera ${nextCameraIndex}: "${candidateCamera.label}" (specialty: ${isSpecialtyCamera})`);
        
        // If we find a non-specialty camera, use it
        if (!isSpecialtyCamera) {
            break;
        }
        
        // Move to next camera
        nextCameraIndex = (nextCameraIndex + 1) % window.availableCameras.length;
        attempts++;
        
        // If we've cycled through all cameras and they're all specialty, just use the next one
        if (attempts >= window.availableCameras.length) {
            nextCameraIndex = (window.currentCameraIndex + 1) % window.availableCameras.length;
            console.log('📷 All cameras are specialty cameras, using next available');
            break;
        }
    }
    
    window.currentCameraIndex = nextCameraIndex;
    const nextCamera = window.availableCameras[window.currentCameraIndex];
    
    console.log(`🔄 Passaggio a camera: "${nextCamera.label}" (${window.currentCameraIndex + 1}/${window.availableCameras.length})`);
    
    // Enhanced camera type detection for feedback
    const label = nextCamera.label.toLowerCase();
    let cameraTypeDisplay = 'Camera';
    if (label.includes('front') || label.includes('user')) {
        cameraTypeDisplay = 'Frontale';
    } else if (label.includes('ultra') || label.includes('wide') || label.includes('0.5')) {
        cameraTypeDisplay = 'Ultra-Wide (⚠️ Non ideale)';
    } else if (label.includes('telephoto') || label.includes('tele') || label.includes('zoom') || label.includes('2x') || label.includes('3x')) {
        cameraTypeDisplay = 'Telephoto (⚠️ Non ideale)';
    } else if (label.includes('macro')) {
        cameraTypeDisplay = 'Macro (⚠️ Non ideale)';
    } else {
        cameraTypeDisplay = 'Posteriore (1X)';
    }
    
    // Show switching feedback
    showFeedback(`🔄 Cambio camera: ${cameraTypeDisplay}`, 'info');
    
    // SAVE USER PREFERENCE PERMANENTLY
    CameraPreferences.savePreferredCamera(nextCamera.deviceId, nextCamera.label);
    console.log('💾 New camera preference saved permanently');
    
    // Start camera with new device
    codeReader.decodeFromVideoDevice(nextCamera.deviceId, 'camera-preview', (result, err) => {
        if (result) {
            console.log('🎯 QR Code rilevato:', result.text);
            
            // Add haptic feedback for successful scan
            if ('vibrate' in navigator) {
                navigator.vibrate([100, 50, 100]);
            }
            
            processScan(result.text);
        }
        if (err && !(err instanceof ZXing.NotFoundException)) {
            console.error('⚠️ Errore scansione:', err);
        }
    })
    .then(() => {
        console.log('✅ Camera switch completato');
        showFeedback(`📱 Camera ${cameraTypeDisplay} attivata e salvata come predefinita!`, 'success');
    })
    .catch((err) => {
        console.error('❌ Errore switch camera:', err);
        showFeedback('Errore nel cambio camera', 'error');
    });
}

/**
 * Handle camera errors with user-friendly messages - Mobile Optimized
 */
function handleCameraError(err) {
    console.error('❌ Errore camera:', err);
    
    // Hide starting message if visible
    $('#camera-starting').hide();
    
    // Add error haptic feedback
    if ('vibrate' in navigator) {
        navigator.vibrate([200, 100, 200, 100, 200]); // Error pattern
    }
    
    let errorMessage = '';
    let errorIcon = 'fas fa-exclamation-triangle';
    
    if (err.name === 'NotAllowedError') {
        errorMessage = '📷 Permesso camera negato\n\nPer utilizzare la scansione:\n1. Tocca l\'icona del lucchetto nella barra degli indirizzi\n2. Consenti l\'accesso alla camera\n3. Ricarica la pagina';
        errorIcon = 'fas fa-lock';
    } else if (err.name === 'NotFoundError') {
        errorMessage = '📱 Nessuna camera trovata\n\nAssicurati che il dispositivo abbia una camera funzionante e riprova.';
        errorIcon = 'fas fa-camera-slash';
    } else if (err.name === 'NotReadableError') {
        errorMessage = '📷 Camera in uso\n\nLa camera è già utilizzata da un\'altra app. Chiudi le altre applicazioni che potrebbero usare la camera e riprova.';
        errorIcon = 'fas fa-ban';
    } else if (err.name === 'OverconstrainedError') {
        errorMessage = '⚙️ Camera non compatibile\n\nLe impostazioni richieste non sono supportate da questo dispositivo. Prova con un altro dispositivo.';
        errorIcon = 'fas fa-cog';
    } else {
        errorMessage = `🔧 Errore tecnico\n\n${err.message || 'Errore sconosciuto'}\n\nProva a ricaricare la pagina o usa un altro browser.`;
        errorIcon = 'fas fa-tools';
    }
    
    // Show enhanced error feedback
    if (window.showMobileFeedback) {
        showMobileFeedback(errorMessage, 'error', errorIcon);
    } else {
        showFeedback(errorMessage, 'error');
    }
    
    // Show manual start button as fallback
    $('#start-camera').show();
    $('#stop-camera').hide();
    $('#switch-camera').hide();
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
 * Process scanned code - Mobile Enhanced
 */
function processScan(code) {
    if (!code) return;
    
    // Clear manual input if exists
    $('#manual-code').val('');
    
    // Add light haptic feedback for scan initiation
    if ('vibrate' in navigator) {
        navigator.vibrate(50);
    }
    
    // Show enhanced processing feedback
    if (window.showMobileFeedback) {
        showMobileFeedback('🔍 Elaborazione codice...', 'info', 'fas fa-qrcode');
    } else {
        showFeedback('Elaborazione...', 'info');
    }
    
    // Get task ticket ID from URL or data attribute
    const taskTicketId = getTaskTicketId();
    
    if (!taskTicketId) {
        const errorMsg = '❌ Errore di configurazione\n\nID ticket non trovato. Ricarica la pagina e riprova.';
        if (window.showMobileFeedback) {
            showMobileFeedback(errorMsg, 'error', 'fas fa-exclamation-triangle');
        } else {
            showFeedback('Errore: ID ticket non trovato', 'error');
        }
        return;
    }
    
    // Get CSRF token
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
        const errorMsg = '🔒 Errore di sicurezza\n\nToken di sicurezza non trovato. Ricarica la pagina e riprova.';
        if (window.showMobileFeedback) {
            showMobileFeedback(errorMsg, 'error', 'fas fa-shield-alt');
        } else {
            showFeedback('Errore: Token CSRF non trovato', 'error');
        }
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
                // Success haptic feedback
                if ('vibrate' in navigator) {
                    navigator.vibrate([100, 50, 100]); // Success pattern
                }
                
                if (window.showMobileFeedback) {
                    showMobileFeedback(`✅ ${response.message}`, 'success', 'fas fa-check-circle');
                } else {
                    showFeedback(response.message, 'success');
                }
                
                // Handle different completion scenarios
                setTimeout(function() {
                    if (response.task_completed) {
                        // Task completed - redirect to user dashboard
                        const completionMsg = '🎉 Task completato!\n\nTutti i ticket sono stati elaborati. Ritorno alla dashboard...';
                        if (window.showMobileFeedback) {
                            showMobileFeedback(completionMsg, 'success', 'fas fa-trophy');
                        } else {
                            showFeedback('🎉 Task completato! Ritorno alla dashboard...', 'success');
                        }
                        
                        setTimeout(function() {
                            window.location.href = '/tasks/user';
                        }, 2500);
                    } else if (response.ticket_completed && response.next_ticket_id) {
                        // Current ticket completed, move to next ticket
                        const nextMsg = '🎯 Ticket completato!\n\nPassaggio automatico al prossimo ticket...';
                        if (window.showMobileFeedback) {
                            showMobileFeedback(nextMsg, 'success', 'fas fa-arrow-right');
                        } else {
                            showFeedback('Ticket completato! Passaggio al prossimo...', 'success');
                        }
                        
                        setTimeout(function() {
                            window.location.href = `/tasks/ticket/${response.next_ticket_id}/scan`;
                        }, 2000);
                    } else {
                        // Product scanned successfully, reload to show next product
                        const nextProductMsg = '✅ Prodotto scansionato!\n\nCaricamento prossimo prodotto...';
                        if (window.showMobileFeedback) {
                            showMobileFeedback(nextProductMsg, 'success', 'fas fa-box-open');
                        }
                        
                        setTimeout(function() {
                            window.location.reload();
                        }, 1500);
                    }
                }, 1500);
            } else {
                // Error haptic feedback
                if ('vibrate' in navigator) {
                    navigator.vibrate([200, 100, 200]); // Error pattern
                }
                
                const errorMsg = `❌ Errore di scansione\n\n${response.message || 'Errore nella scansione'}\n\nRiprova con un altro QR code.`;
                if (window.showMobileFeedback) {
                    showMobileFeedback(errorMsg, 'error', 'fas fa-times-circle');
                } else {
                    showFeedback(response.message || 'Errore nella scansione', 'error');
                }
                
                // Don't focus manual input on mobile as it might interfere with camera
                if (window.innerWidth > 768) {
                    setTimeout(function() {
                        $('#manual-code').focus();
                    }, 2000);
                }
            }
        },
        error: function(xhr, status, error) {
            console.error('❌ Scan error:', xhr.responseText, error);
            
            // Error haptic feedback
            if ('vibrate' in navigator) {
                navigator.vibrate([200, 100, 200, 100, 200]); // Strong error pattern
            }
            
            let errorMessage = '🔧 Errore di connessione\n\nVerifica la connessione internet e riprova.';
            let errorIcon = 'fas fa-wifi';
            
            if (xhr.status === 400) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = `📋 Richiesta non valida\n\n${response.message || response.error || 'Formato del QR code non riconosciuto'}\n\nRiprova con un QR code valido.`;
                    errorIcon = 'fas fa-qrcode';
                } catch (e) {
                    errorMessage = '📋 Richiesta non valida\n\nFormato del QR code non riconosciuto. Riprova con un QR code valido.';
                    errorIcon = 'fas fa-qrcode';
                }
            } else if (xhr.status === 403) {
                errorMessage = '🔒 Errore di autorizzazione\n\nLa sessione è scaduta. Ricarica la pagina e riprova.';
                errorIcon = 'fas fa-lock';
            } else if (xhr.status === 500) {
                errorMessage = '🚨 Errore del server\n\nProblema temporaneo del sistema. Riprova tra qualche secondo.';
                errorIcon = 'fas fa-server';
            } else if (xhr.status === 0) {
                errorMessage = '📶 Connessione persa\n\nVerifica la connessione internet e riprova.';
                errorIcon = 'fas fa-signal';
            }
            
            if (window.showMobileFeedback) {
                showMobileFeedback(errorMessage, 'error', errorIcon);
            } else {
                showFeedback(errorMessage, 'error');
            }
            
            // Don't focus manual input on mobile
            if (window.innerWidth > 768) {
                setTimeout(function() {
                    $('#manual-code').focus();
                }, 2000);
            }
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
    
    // Initialize deadline validation
    initializeDeadlineValidation();
    
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
        
        // Don't trigger if ticket is disabled
        if ($(this).hasClass('disabled')) {
            e.preventDefault();
            return;
        }
        
        const checkbox = $(this).find('.ticket-checkbox');
        // Only toggle if checkbox is not disabled
        if (!checkbox.prop('disabled')) {
            checkbox.prop('checked', !checkbox.prop('checked')).trigger('change');
        }
    });
    
    // Select all tickets
    $('#selectAllBtn').on('click', function() {
        $('.ticket-checkbox:not(:disabled)').prop('checked', true);
        $('.ticket-card-minimal:not(.disabled)').addClass('selected');
        updateSummary();
    });
    
    // Deselect all tickets
    $('#deselectAllBtn').on('click', function() {
        $('.ticket-checkbox:not(:disabled)').prop('checked', false);
        $('.ticket-card-minimal:not(.disabled)').removeClass('selected');
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

        // Validate deadline
        if (!validateDeadline()) {
            e.preventDefault();
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
 * Initialize deadline validation with immediate ticket blocking
 */
function initializeDeadlineValidation() {
    const deadlineInput = $('#deadline');
    
    // Set minimum date to today
    const today = new Date();
    const todayString = today.toISOString().slice(0, 16);
    deadlineInput.attr('min', todayString);
    
    // Add validation on change
    deadlineInput.on('change', function() {
        validateDeadline();
        // Validate and disable problematic tickets when deadline changes
        validateAndDisableProblematicTickets();
    });
    
    // Initial validation on page load if deadline is already set
    if (deadlineInput.val()) {
        validateAndDisableProblematicTickets();
    }
}

/**
 * Validate deadline is not in the past
 */
function validateDeadline() {
    const deadlineInput = $('#deadline');
    const deadlineValue = deadlineInput.val();
    
    if (!deadlineValue) {
        // Deadline is optional
        deadlineInput.removeClass('is-invalid');
        $('#deadline-feedback').remove();
        return true;
    }
    
    const selectedDate = new Date(deadlineValue);
    const now = new Date();
    
    // Fix: Compare only dates, not datetime, so today's date is allowed
    const selectedDateOnly = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate());
    const todayOnly = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    // Check if selected date is in the past
    if (selectedDateOnly < todayOnly) {
        deadlineInput.addClass('is-invalid');
        
        // Remove existing feedback
        $('#deadline-feedback').remove();
        
        // Add error feedback
        deadlineInput.after('<div id="deadline-feedback" class="invalid-feedback">La data di scadenza non può essere nel passato.</div>');
        
        return false;
    } else {
        deadlineInput.removeClass('is-invalid');
        $('#deadline-feedback').remove();
        return true;
    }
}

/**
 * Update ticket selection visual state and validate expiry dates
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
 * Validate and disable tickets with problematic expiry dates
 */
function validateAndDisableProblematicTickets() {
    const deadlineInput = $('#deadline');
    const deadlineValue = deadlineInput.val();
    
    // Reset all tickets to enabled state first and clean up tooltips
    $('.ticket-card-minimal').each(function() {
        const ticketCard = $(this);
        
        // Remove classes
        ticketCard.removeClass('disabled has-expiry-conflict');
        
        // Enable checkbox
        ticketCard.find('.ticket-checkbox').prop('disabled', false);
        
        // Clean up any existing tooltips
        if (typeof bootstrap !== 'undefined') {
            const existingTooltip = bootstrap.Tooltip.getInstance(ticketCard[0]);
            if (existingTooltip) {
                existingTooltip.dispose();
            }
        }
        
        // Remove tooltip attributes
        ticketCard.removeAttr('title');
        ticketCard.removeAttr('data-bs-toggle');
        ticketCard.removeAttr('data-bs-placement');
        ticketCard.removeAttr('data-bs-original-title');
    });
    
    // If no deadline is set, all tickets are valid
    if (!deadlineValue) {
        updateSummary();
        return;
    }
    
    const taskDeadline = new Date(deadlineValue);
    const taskDeadlineDate = new Date(taskDeadline.getFullYear(), taskDeadline.getMonth(), taskDeadline.getDate());
    
    // Check each ticket
    $('.ticket-card-minimal').each(function() {
        const ticketCard = $(this);
        const checkbox = ticketCard.find('.ticket-checkbox');
        
        // Check all product expiry dates in this ticket
        const expiryElements = ticketCard.find('.product-expiry-compact');
        let hasConflict = false;
        let conflictProducts = [];
        
        expiryElements.each(function() {
            const expiryText = $(this).data('expiry');
            
            if (expiryText) {
                const [day, month, year] = expiryText.split('/');
                const expiryDate = new Date(year, month - 1, day); // month is 0-indexed
                
                if (expiryDate > taskDeadlineDate) {
                    hasConflict = true;
                    const productName = $(this).closest('.product-row').find('.product-name-compact').text().trim();
                    conflictProducts.push({
                        name: productName,
                        expiry: expiryText
                    });
                }
            }
        });
        
        if (hasConflict) {
            // Disable the ticket completely
            ticketCard.addClass('disabled has-expiry-conflict');
            checkbox.prop('disabled', true);
            checkbox.prop('checked', false);
            ticketCard.removeClass('selected');
            
            // Add tooltip to show why it's disabled
            const tooltipText = `Ticket disabilitato: contiene prodotti con scadenza superiore alla deadline del task:\n${conflictProducts.slice(0, 3).map(p => `• ${p.name} (scade ${p.expiry})`).join('\n')}${conflictProducts.length > 3 ? `\n... e altri ${conflictProducts.length - 3} prodotti` : ''}`;
            
            ticketCard.attr('title', tooltipText);
            ticketCard.attr('data-bs-toggle', 'tooltip');
            ticketCard.attr('data-bs-placement', 'top');
            
            // Initialize new tooltip
            if (typeof bootstrap !== 'undefined') {
                new bootstrap.Tooltip(ticketCard[0]);
            }
        }
        // Note: No need for else clause here since we already cleaned up everything at the start
    });
    
    // Update summary after validation
    updateSummary();
}

/**
 * Update selected tickets summary
 */
function updateSummary() {
    const selectedTickets = $('.ticket-checkbox:checked');
    const selectedCount = selectedTickets.length;
    const disabledCount = $('.ticket-card-minimal.disabled').length;
    const totalTickets = $('.ticket-card-minimal').length;
    const availableTickets = totalTickets - disabledCount;
    
    let totalLines = 0;
    let totalProducts = 0;

    selectedTickets.each(function() {
        const ticketCard = $(this).closest('.ticket-card-minimal');
        
        // Count lines from badge - look for the compact version
        const linesText = ticketCard.find('.ticket-lines-count').text();
        const lines = parseInt(linesText.split(' ')[0]) || 0;
        totalLines += lines;
        
        // For products, use the same number as lines since each line is a product
        totalProducts += lines;
    });

    // Update counters with more detailed info
    const counterText = `${selectedCount} selezionati${disabledCount > 0 ? ` (${disabledCount} disabilitati)` : ''}`;
    $('#selectedCount').text(counterText);
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
    switchCamera,
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
    handleCameraError,
    CameraPreferences
}; 