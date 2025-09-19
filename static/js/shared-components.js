/**
 * DBLogiX - Shared Components JavaScript
 * Funzionalità unificate per ricerca e statistiche
 */

class UnifiedSearch {
    constructor(options = {}) {
        this.options = {
            searchInputSelector: '.unified-search-input',
            searchFormSelector: '#unifiedSearchForm',
            clearBtnSelector: '.search-clear-btn',
            filterToggleSelector: '.filter-toggle',
            advancedFiltersSelector: '.advanced-filters',
            debounceTime: 800,
            minSearchLength: 2,
            ...options
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initializeFilters();
        this.updateUI();
    }
    
    bindEvents() {
        // Ricerca con debounce
        const searchInput = document.querySelector(this.options.searchInputSelector);
        if (searchInput) {
            let timeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                const value = e.target.value.trim();
                
                if (value.length >= this.options.minSearchLength || value.length === 0) {
                    timeout = setTimeout(() => {
                        this.performSearch(value);
                    }, this.options.debounceTime);
                }
            });
            
            // Enter key per ricerca immediata
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    clearTimeout(timeout);
                    this.performSearch(e.target.value.trim());
                }
            });
        }
        
        // Clear search
        const clearBtn = document.querySelector(this.options.clearBtnSelector);
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearSearch();
            });
        }
        
        // Toggle filtri avanzati
        const filterToggle = document.querySelector(this.options.filterToggleSelector);
        if (filterToggle) {
            filterToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleAdvancedFilters();
            });
        }
        
        // Scorciatoie da tastiera
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                const searchInput = document.querySelector(this.options.searchInputSelector);
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
        });
    }
    
    performSearch(query) {
        const form = document.querySelector(this.options.searchFormSelector);
        if (form) {
            const searchInput = form.querySelector('input[name="search"], input[name="query"]');
            if (searchInput) {
                searchInput.value = query;
                this.showLoading(true);
                form.submit();
            }
        }
    }
    
    clearSearch() {
        const currentUrl = new URL(window.location.href);
        const paramsToRemove = ['search', 'query', 'q'];
        
        paramsToRemove.forEach(param => {
            currentUrl.searchParams.delete(param);
        });
        
        window.location.href = currentUrl.toString();
    }
    
    toggleAdvancedFilters() {
        const filtersSection = document.querySelector(this.options.advancedFiltersSelector);
        const toggle = document.querySelector(this.options.filterToggleSelector);
        
        if (filtersSection && toggle) {
            const isVisible = filtersSection.classList.contains('show');
            
            if (isVisible) {
                filtersSection.classList.remove('show');
                toggle.innerHTML = '<i class="fas fa-chevron-down"></i> Filtri avanzati';
            } else {
                filtersSection.classList.add('show');
                toggle.innerHTML = '<i class="fas fa-chevron-up"></i> Nascondi filtri';
            }
        }
    }
    
    initializeFilters() {
        // Auto-submit per filtri data
        const dateInputs = document.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            input.addEventListener('change', () => {
                this.addLoadingEffect(input);
                this.applyDateFilters();
            });
        });
        
        // Auto-submit per select
        const selectInputs = document.querySelectorAll('.advanced-filters select');
        selectInputs.forEach(select => {
            select.addEventListener('change', () => {
                this.addLoadingEffect(select);
                this.applyFilters();
            });
        });
        
        // Aggiungi effetti visuali ai form controls
        this.enhanceFormControls();
        
        // Inizializza animazioni per filtri attivi
        this.animateActiveFilters();
    }
    
    enhanceFormControls() {
        // Effetti di focus semplici sui form controls
        const formControls = document.querySelectorAll('.form-control');
        formControls.forEach(control => {
            control.addEventListener('focus', (e) => {
                e.target.closest('.filter-group, .form-group')?.classList.add('focused');
            });
            
            control.addEventListener('blur', (e) => {
                e.target.closest('.filter-group, .form-group')?.classList.remove('focused');
            });
        });
    }
    
    addLoadingEffect(element) {
        element.classList.add('loading');
        setTimeout(() => {
            element.classList.remove('loading');
        }, 800);
    }
    
    animateActiveFilters() {
        const filterBadges = document.querySelectorAll('.filter-badge');
        filterBadges.forEach((badge, index) => {
            badge.style.animation = `slideInUp 0.4s ease ${index * 0.1}s both`;
        });
    }
    
    applyDateFilters() {
        const startDate = document.getElementById('startDate')?.value;
        const endDate = document.getElementById('endDate')?.value;
        
        if (startDate || endDate) {
            const currentUrl = new URL(window.location.href);
            
            if (startDate) {
                currentUrl.searchParams.set('start_date', startDate);
                currentUrl.searchParams.set('date_from', startDate);
            } else {
                currentUrl.searchParams.delete('start_date');
                currentUrl.searchParams.delete('date_from');
            }
            
            if (endDate) {
                currentUrl.searchParams.set('end_date', endDate);
                currentUrl.searchParams.set('date_to', endDate);
            } else {
                currentUrl.searchParams.delete('end_date');
                currentUrl.searchParams.delete('date_to');
            }
            
            window.location.href = currentUrl.toString();
        }
    }
    
    applyFilters() {
        const form = document.querySelector(this.options.searchFormSelector);
        if (form) {
            this.showLoading(true);
            form.submit();
        }
    }
    
    showLoading(show) {
        const searchSection = document.querySelector('.unified-search-section');
        if (searchSection) {
            if (show) {
                searchSection.classList.add('loading');
            } else {
                searchSection.classList.remove('loading');
            }
        }
    }
    
    updateUI() {
        // Aggiorna contatori
        this.updateVisibleCount();
        
        // Evidenzia ricerca attiva
        this.highlightActiveSearch();
    }
    
    updateVisibleCount() {
        const visibleCountEl = document.getElementById('visibleCount');
        if (visibleCountEl) {
            const visibleItems = document.querySelectorAll('.table tbody tr:not(.hidden), .task-card:not(.hidden), .client-card:not(.hidden)').length;
            visibleCountEl.textContent = visibleItems;
        }
    }
    
    highlightActiveSearch() {
        const searchInput = document.querySelector(this.options.searchInputSelector);
        if (searchInput && searchInput.value.trim()) {
            searchInput.classList.add('search-active');
        }
    }
}

// Utility functions
const UnifiedUtils = {
    // Formattazione numeri
    formatNumber: (num) => {
        return new Intl.NumberFormat('it-IT').format(num);
    },
    
    // Formattazione valuta
    formatCurrency: (amount) => {
        return new Intl.NumberFormat('it-IT', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount);
    },
    
    // Animazione contatori
    animateCounter: (element, finalValue, duration = 1000) => {
        const startValue = 0;
        const startTime = performance.now();
        
        const updateCounter = (currentTime) => {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            
            const currentValue = Math.floor(progress * finalValue);
            element.textContent = UnifiedUtils.formatNumber(currentValue);
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = UnifiedUtils.formatNumber(finalValue);
            }
        };
        
        requestAnimationFrame(updateCounter);
    },
    
    // Debounce function
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Toast notifications
    showToast: (message, type = 'info') => {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-info-circle"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
};

// Auto-initialize quando il DOM è pronto
document.addEventListener('DOMContentLoaded', function() {
    // Inizializza la ricerca unificata se presente
    if (document.querySelector('.unified-search-section')) {
        window.unifiedSearch = new UnifiedSearch();
    }
    
    // Anima i contatori delle statistiche
    const statNumbers = document.querySelectorAll('.stat-number');
    statNumbers.forEach(stat => {
        const value = parseInt(stat.textContent);
        if (!isNaN(value) && value > 0) {
            UnifiedUtils.animateCounter(stat, value, 800);
        }
    });
    
    // Aggiunge effetti hover alle card
    const statCards = document.querySelectorAll('.unified-stat-card');
    statCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
});

// Esporta per uso globale
window.UnifiedSearch = UnifiedSearch;
window.UnifiedUtils = UnifiedUtils; 