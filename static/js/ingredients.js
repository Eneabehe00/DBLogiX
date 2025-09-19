/* Ingredients JavaScript - DB-LogiX
------------------------------------- */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Ingredients module loaded');
    
    // Initialize Ingredients features
    initializeIngredientCards();
    initializeSearch();
    initializeForms();
    initializeTooltips();
    initializeAnimations();
    
    // Auto-submit forms on filter changes
    initializeAutoSubmit();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
});

/**
 * Initialize ingredient cards with hover effects and click handlers
 */
function initializeIngredientCards() {
    const ingredientCards = document.querySelectorAll('.ingredient-card');
    
    ingredientCards.forEach((card, index) => {
        // Add staggered animation delay
        card.style.animationDelay = `${index * 0.05}s`;
        
        // Add click handler for card navigation
        const viewLink = card.querySelector('.dropdown-item[href*="view"]');
        if (viewLink) {
            card.addEventListener('click', function(e) {
                // Don't navigate if clicking on dropdown or buttons
                if (e.target.closest('.dropdown') || 
                    e.target.closest('button') || 
                    e.target.closest('form')) {
                    return;
                }
                window.location.href = viewLink.href;
            });
            
            // Add pointer cursor
            card.style.cursor = 'pointer';
        }
        
        // Add ripple effect on click
        card.addEventListener('click', function(e) {
            createRippleEffect(this, e);
        });
    });
}

/**
 * Create ripple effect on element click
 */
function createRippleEffect(element, event) {
    const ripple = document.createElement('div');
    ripple.className = 'click-ripple';
    element.appendChild(ripple);
    
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    
    // Add CSS for ripple animation
    if (!document.querySelector('#ripple-styles')) {
        const style = document.createElement('style');
        style.id = 'ripple-styles';
        style.textContent = `
            .click-ripple {
                position: absolute;
                border-radius: 50%;
                background: rgba(46, 204, 113, 0.3);
                pointer-events: none;
                animation: ripple-animation 0.6s ease-out;
                z-index: 1;
            }
            
            @keyframes ripple-animation {
                0% {
                    transform: scale(0);
                    opacity: 1;
                }
                100% {
                    transform: scale(1);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

/**
 * Initialize search functionality
 */
function initializeSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    const clearSearchBtn = document.querySelector('.search-clear-btn');
    
    if (searchInput) {
        let searchTimeout;
        
        // Enhanced search with debouncing
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const searchTerm = this.value.toLowerCase().trim();
            
            // Auto-submit after 800ms of no typing
            if (searchTerm.length >= 2) {
                searchTimeout = setTimeout(() => {
                    this.form.submit();
                }, 800);
            }
        });
        
        // Handle Enter key for immediate search
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                clearTimeout(searchTimeout);
                this.form.submit();
            }
        });
        
        // Focus search on Ctrl+F
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }
    
    // Clear search functionality
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            const form = this.closest('form');
            const inputs = form.querySelectorAll('input[type="text"], select');
            inputs.forEach(input => {
                if (input.type === 'text') {
                    input.value = '';
                } else if (input.tagName === 'SELECT') {
                    input.selectedIndex = 0;
                }
            });
            form.submit();
        });
    }
}

/**
 * Initialize form enhancements
 */
function initializeForms() {
    // Form validation enhancements
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Add loading state on submit
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Caricamento...';
                submitBtn.disabled = true;
                
                // Re-enable after 5 seconds as fallback
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 5000);
            }
        });
        
        // Enhanced form field focus effects
        const formControls = form.querySelectorAll('.form-control, .form-select');
        formControls.forEach(control => {
            control.addEventListener('focus', function() {
                this.parentElement.classList.add('form-group-focused');
            });
            
            control.addEventListener('blur', function() {
                this.parentElement.classList.remove('form-group-focused');
            });
        });
    });
    
    // Price field formatting
    const priceFields = document.querySelectorAll('input[type="number"][step="0.01"]');
    priceFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (this.value) {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });
}

/**
 * Initialize tooltips
 */
function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => 
        new bootstrap.Tooltip(tooltipTriggerEl)
    );
    
    // Add custom tooltips for ingredient cards
    const ingredientCards = document.querySelectorAll('.ingredient-card');
    ingredientCards.forEach(card => {
        const name = card.querySelector('.ingredient-name')?.textContent;
        if (name) {
            card.setAttribute('title', `Clicca per visualizzare i dettagli di ${name}`);
            new bootstrap.Tooltip(card);
        }
    });
}

/**
 * Initialize animations and lazy loading
 */
function initializeAnimations() {
    // Intersection Observer for card animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const cardObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('card-visible');
                cardObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe all ingredient cards
    const ingredientCards = document.querySelectorAll('.ingredient-card');
    ingredientCards.forEach(card => {
        cardObserver.observe(card);
    });
    
    // Smooth scroll to top button
    let scrollToTopBtn = document.querySelector('#scrollToTop');
    if (!scrollToTopBtn) {
        scrollToTopBtn = document.createElement('button');
        scrollToTopBtn.id = 'scrollToTop';
        scrollToTopBtn.className = 'btn btn-success scroll-to-top d-none';
        scrollToTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
        scrollToTopBtn.setAttribute('title', 'Torna in cima');
        document.body.appendChild(scrollToTopBtn);
        
        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .scroll-to-top {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 15px rgba(46, 204, 113, 0.3);
                transition: all 0.3s ease;
                border: none;
                background-color: var(--ingredient-green, #2ecc71);
            }
            
            .scroll-to-top:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(46, 204, 113, 0.4);
                background-color: #27ae60;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Show/hide scroll to top button
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollToTopBtn.classList.remove('d-none');
        } else {
            scrollToTopBtn.classList.add('d-none');
        }
    });
    
    // Scroll to top functionality
    scrollToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

/**
 * Initialize auto-submit for filters
 */
function initializeAutoSubmit() {
    // Auto-submit on category change
    const categorySelect = document.querySelector('select[name="categoria"]');
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            this.form.submit();
        });
    }
    
    // Auto-submit on sort change
    const sortSelect = document.querySelector('select[name="sort"]');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            this.form.submit();
        });
    }
    
    // Auto-submit on fornitore change
    const fornitoreSelect = document.querySelector('select[name="fornitore"]');
    if (fornitoreSelect) {
        fornitoreSelect.addEventListener('change', function() {
            this.form.submit();
        });
    }
}

/**
 * Initialize keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Alt + N: New ingredient
        if (e.altKey && e.key === 'n') {
            e.preventDefault();
            const newBtn = document.querySelector('a[href*="new"]');
            if (newBtn) {
                window.location.href = newBtn.href;
            }
        }
        
        // Alt + H: Go to ingredients home
        if (e.altKey && e.key === 'h') {
            e.preventDefault();
            const homeBtn = document.querySelector('a[href*="ingredients.index"]');
            if (homeBtn) {
                window.location.href = homeBtn.href;
            }
        }
        
        // Escape: Clear active modals or reset forms
        if (e.key === 'Escape') {
            const activeModal = document.querySelector('.modal.show');
            if (activeModal) {
                const modalInstance = bootstrap.Modal.getInstance(activeModal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            }
        }
    });
}

/**
 * Utility function to show success message
 */
function showSuccessMessage(message) {
    const alertContainer = document.createElement('div');
    alertContainer.className = 'alert alert-success alert-dismissible fade show';
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid') || document.body;
    container.insertBefore(alertContainer, container.firstChild);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertContainer.remove();
    }, 5000);
}

/**
 * Utility function to show error message
 */
function showErrorMessage(message) {
    const alertContainer = document.createElement('div');
    alertContainer.className = 'alert alert-danger alert-dismissible fade show';
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid') || document.body;
    container.insertBefore(alertContainer, container.firstChild);
    
    // Auto-hide after 7 seconds for errors
    setTimeout(() => {
        alertContainer.remove();
    }, 7000);
}

/**
 * Form field validation helpers
 */
function validateIngredientForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

/**
 * Export functions for global use
 */
window.IngredientsModule = {
    showSuccessMessage,
    showErrorMessage,
    validateIngredientForm,
    createRippleEffect
};

console.log('✅ Ingredients JavaScript module initialized');