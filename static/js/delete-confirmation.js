/**
 * DB-LogiX - Delete Confirmation Functionality
 * Standardized delete confirmation system
 */

document.addEventListener('DOMContentLoaded', function() {
    // Delete confirmation modal template
    const modalTemplate = `
    <div class="modal fade delete-modal" id="deleteConfirmationModal" tabindex="-1" aria-labelledby="deleteConfirmationModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="deleteConfirmationModalLabel">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Conferma Eliminazione</span>
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="delete-icon-container">
                        <div class="delete-icon">
                            <i class="fas fa-trash"></i>
                        </div>
                    </div>
                    <div class="delete-warning">
                        <h4 class="delete-warning-title">Sei sicuro di voler eliminare questo elemento?</h4>
                        <p class="delete-warning-text">Stai per eliminare <span class="item-name">questo elemento</span>. Questa azione non può essere annullata.</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-cancel" data-bs-dismiss="modal">
                        <i class="fas fa-times"></i> Annulla
                    </button>
                    <button type="button" class="btn btn-delete" id="confirmDeleteBtn">
                        <i class="fas fa-trash"></i> Elimina
                    </button>
                </div>
            </div>
        </div>
    </div>`;

    // Add modal to document if it doesn't exist
    if (!document.getElementById('deleteConfirmationModal')) {
        document.body.insertAdjacentHTML('beforeend', modalTemplate);
    }

    // Get references to modal elements
    const deleteModal = document.getElementById('deleteConfirmationModal');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const itemNameSpan = deleteModal.querySelector('.item-name');
    
    // Current delete callback function
    let currentDeleteCallback = null;
    let currentItemId = null;
    let currentItemName = null;

    // Initialize Bootstrap modal if available
    let bsModal = null;
    try {
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            bsModal = new bootstrap.Modal(deleteModal, {
                backdrop: 'static',
                keyboard: false
            });
        }
    } catch (error) {
        console.warn('Bootstrap Modal initialization failed:', error);
        bsModal = null;
    }

    /**
     * Show delete confirmation modal
     * @param {Object} options - Configuration options
     * @param {string} options.itemId - ID of the item to delete
     * @param {string} options.itemName - Name of the item to display
     * @param {string} options.itemType - Type of item (e.g., "articolo", "cliente")
     * @param {Function} options.deleteCallback - Function to call when delete is confirmed
     */
    window.showDeleteConfirmation = function(options) {
        // Set item details
        currentItemId = options.itemId;
        currentItemName = options.itemName || 'questo elemento';
        currentDeleteCallback = options.deleteCallback;
        
        // Update modal content
        const modalTitle = deleteModal.querySelector('.modal-title span');
        const warningTitle = deleteModal.querySelector('.delete-warning-title');
        
        modalTitle.textContent = `Conferma Eliminazione ${options.itemType || ''}`;
        warningTitle.textContent = `Sei sicuro di voler eliminare ${options.itemType ? 'questo ' + options.itemType : 'questo elemento'}?`;
        itemNameSpan.textContent = currentItemName;
        
        // Show modal
        try {
            if (bsModal) {
                bsModal.show();
            } else if (typeof $ !== 'undefined' && $(deleteModal).modal) {
                $(deleteModal).modal('show');
            } else {
                console.error('Nessun sistema di modal disponibile');
                // Fallback: conferma nativa del browser
                const confirmed = confirm(`Sei sicuro di voler eliminare ${currentItemName}?`);
                if (confirmed && currentDeleteCallback) {
                    currentDeleteCallback(currentItemId);
                }
            }
        } catch (error) {
            console.error('Errore nell\'apertura del modal:', error);
            // Fallback: conferma nativa del browser
            const confirmed = confirm(`Sei sicuro di voler eliminare ${currentItemName}?`);
            if (confirmed && currentDeleteCallback) {
                currentDeleteCallback(currentItemId);
            }
        }
    };

    // Attach confirm delete event
    confirmDeleteBtn.addEventListener('click', function() {
        if (currentDeleteCallback && typeof currentDeleteCallback === 'function') {
            // Hide modal
            try {
                if (bsModal) {
                    bsModal.hide();
                } else if (typeof $ !== 'undefined' && $(deleteModal).modal) {
                    $(deleteModal).modal('hide');
                }
            } catch (error) {
                console.warn('Errore nella chiusura del modal:', error);
            }
            
            // Execute delete callback
            currentDeleteCallback(currentItemId);
        }
    });

    // Add click handler to all delete buttons with data-delete attribute
    document.addEventListener('click', function(e) {
        const deleteBtn = e.target.closest('[data-delete]');
        if (!deleteBtn) return;
        
        e.preventDefault();
        
        const itemId = deleteBtn.dataset.id || '';
        const itemName = deleteBtn.dataset.name || 'questo elemento';
        const itemType = deleteBtn.dataset.type || '';
        const deleteUrl = deleteBtn.dataset.url || deleteBtn.href;
        
        if (!deleteUrl) {
            console.error('Delete URL not specified');
            return;
        }
        
        showDeleteConfirmation({
            itemId: itemId,
            itemName: itemName,
            itemType: itemType,
            deleteCallback: function(id) {
                // Create and submit a form to the delete URL
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = deleteUrl;
                
                // Add CSRF token if available
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                if (csrfToken) {
                    const csrfInput = document.createElement('input');
                    csrfInput.type = 'hidden';
                    csrfInput.name = 'csrf_token';
                    csrfInput.value = csrfToken;
                    form.appendChild(csrfInput);
                }
                
                // Add item ID if available
                if (id) {
                    const idInput = document.createElement('input');
                    idInput.type = 'hidden';
                    idInput.name = 'id';
                    idInput.value = id;
                    form.appendChild(idInput);
                }
                
                // Submit the form
                document.body.appendChild(form);
                form.submit();
            }
        });
    });
}); 