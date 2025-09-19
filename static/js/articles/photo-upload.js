/**
 * Photo Upload and Camera Capture Functionality
 */
(function() {
    'use strict';
    
    // Wait for DOM to be ready
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }
    
    ready(function() {
        console.log('Photo upload script loaded');
        
        // DOM Elements
        const capturePhotoBtn = document.getElementById('capture-photo');
        const uploadPhotoInput = document.getElementById('upload-photo-input');
        const cameraContainer = document.getElementById('camera-container');
        const cameraPreview = document.getElementById('camera-preview');
        const takePhotoBtn = document.getElementById('take-photo');
        const cancelPhotoBtn = document.getElementById('cancel-photo');
        const photoCanvas = document.getElementById('photo-canvas');
        const productPhoto = document.getElementById('product-photo');
        const photoPlaceholder = document.getElementById('photo-placeholder');
        const hiddenPhotoUrl = document.getElementById('photo-url');
        
        console.log('Photo elements found:', {
            capturePhotoBtn: !!capturePhotoBtn,
            uploadPhotoInput: !!uploadPhotoInput,
            cameraContainer: !!cameraContainer,
            productPhoto: !!productPhoto,
            photoPlaceholder: !!photoPlaceholder
        });
        
        // Return early if essential elements are missing
        if (!capturePhotoBtn || !uploadPhotoInput || !productPhoto) {
            console.log('Missing essential photo elements');
            return;
        }
        
        let stream = null;
        let articleId = null;
        
        // Get article ID from URL if editing
        const urlMatch = window.location.pathname.match(/\/articles\/edit\/(\d+)/);
        if (urlMatch) {
            articleId = urlMatch[1];
            console.log('Article ID for editing:', articleId);
        } else {
            console.log('Creating new article - no ID yet');
        }
        
        // Initialize camera when Capture Photo button is clicked
        capturePhotoBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Capture photo button clicked');
            
            // Check if camera is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert('Il tuo browser non supporta l\'accesso alla fotocamera. Aggiorna il browser o utilizza un altro dispositivo.');
                return;
            }
            
            // Reset and show camera interface
            if (cameraContainer) {
                cameraContainer.style.display = 'block';
                console.log('Camera container shown');
            }
            
            // Access camera
            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            })
            .then(function(mediaStream) {
                console.log('Camera access granted');
                stream = mediaStream;
                if (cameraPreview) {
                    cameraPreview.srcObject = mediaStream;
                    cameraPreview.play();
                }
            })
            .catch(function(error) {
                console.error('Errore accesso fotocamera:', error);
                alert('Impossibile accedere alla fotocamera: ' + error.message);
                if (cameraContainer) {
                    cameraContainer.style.display = 'none';
                }
            });
        });
        
        // Take photo when capture button is clicked
        if (takePhotoBtn) {
            takePhotoBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Take photo button clicked');
                
                if (!stream) {
                    console.error('No camera stream available');
                    return;
                }
                
                if (!photoCanvas || !cameraPreview) {
                    console.error('Missing canvas or preview elements');
                    return;
                }
                
                // Set canvas dimensions
                photoCanvas.width = cameraPreview.videoWidth;
                photoCanvas.height = cameraPreview.videoHeight;
                console.log('Canvas dimensions:', photoCanvas.width, 'x', photoCanvas.height);
                
                // Draw video frame to canvas
                const ctx = photoCanvas.getContext('2d');
                ctx.drawImage(cameraPreview, 0, 0, photoCanvas.width, photoCanvas.height);
                
                // Convert canvas to blob and upload
                photoCanvas.toBlob(function(blob) {
                    console.log('Photo captured, blob size:', blob.size);
                    uploadPhotoBlob(blob);
                    
                    // Stop camera stream
                    stopCameraStream();
                    if (cameraContainer) {
                        cameraContainer.style.display = 'none';
                    }
                }, 'image/jpeg', 0.9);
            });
        }
        
        // Close camera when cancel button is clicked
        if (cancelPhotoBtn) {
            cancelPhotoBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Cancel photo button clicked');
                stopCameraStream();
                if (cameraContainer) {
                    cameraContainer.style.display = 'none';
                }
            });
        }
        
        // Handle file selection
        uploadPhotoInput.addEventListener('change', function(e) {
            console.log('File input changed');
            
            if (!this.files || !this.files[0]) {
                console.log('No file selected');
                return;
            }
            
            const file = this.files[0];
            console.log('File selected:', file.name, file.type, file.size);
            
            // Check file type
            if (!file.type.match('image.*')) {
                alert('Per favore seleziona un\'immagine.');
                return;
            }
            
            // Create form data and upload
            uploadPhotoBlob(file);
        });
        
        // Function to upload photo blob
        function uploadPhotoBlob(blob) {
            console.log('Starting photo upload...');
            
            // Create form data
            const formData = new FormData();
            formData.append('photo', blob);
            
            // Determine upload URL based on whether we're creating or editing
            let uploadUrl;
            if (articleId) {
                // Editing existing article
                uploadUrl = `/articles/upload_photo/${articleId}`;
                console.log('Upload URL for editing:', uploadUrl);
            } else {
                // Creating new article - store blob for later upload
                console.log('Storing photo for new article creation');
                const reader = new FileReader();
                reader.onload = function(e) {
                    console.log('Photo converted to data URL');
                    // Show photo preview
                    productPhoto.src = e.target.result;
                    productPhoto.style.display = 'block';
                    if (photoPlaceholder) {
                        photoPlaceholder.style.display = 'none';
                    }
                    
                    // Store data URL in hidden field for form submission
                    if (hiddenPhotoUrl) {
                        hiddenPhotoUrl.value = e.target.result;
                    }
                };
                reader.readAsDataURL(blob);
                return;
            }
            
            // Upload to server
            console.log('Uploading to server...');
            fetch(uploadUrl, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Upload response:', data);
                if (data.success) {
                    // Update photo preview
                    const timestamp = new Date().getTime();
                    productPhoto.src = data.path + '?t=' + timestamp;
                    productPhoto.style.display = 'block';
                    if (photoPlaceholder) {
                        photoPlaceholder.style.display = 'none';
                    }
                    
                    // Store photo URL
                    if (hiddenPhotoUrl) {
                        hiddenPhotoUrl.value = data.path;
                    }
                    console.log('Photo uploaded successfully');
                } else {
                    console.error('Upload failed:', data.message);
                    alert('Errore durante il caricamento della foto: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Upload error:', error);
                alert('Errore durante il caricamento della foto: ' + error.message);
            });
        }
        
        // Function to stop camera stream
        function stopCameraStream() {
            if (stream) {
                console.log('Stopping camera stream');
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }
        }
    });
})(); 