/**
 * DBLogiX - Home Page JavaScript
 * Essential functionality for the home page without animations
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(function(tooltip) {
        new bootstrap.Tooltip(tooltip);
    });
    
    // Simple hover effects for stat cards
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Simple click handler for quick action items
    const quickActions = document.querySelectorAll('.quick-action-item');
    quickActions.forEach(function(action) {
        action.addEventListener('click', function(e) {
            // Add simple loading state
            const icon = this.querySelector('i');
            const originalClass = icon.className;
            icon.className = 'fas fa-spinner fa-spin';
            
            // Restore icon after short delay
            setTimeout(function() {
                icon.className = originalClass;
            }, 1000);
        });
    });
    
    // Make tables responsive by adding data-label attributes
    const tables = document.querySelectorAll('.table');
    tables.forEach(function(table) {
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        
        table.querySelectorAll('tbody tr').forEach(function(row) {
            row.querySelectorAll('td').forEach(function(cell, index) {
                if (headers[index]) {
                    cell.setAttribute('data-label', headers[index]);
                }
            });
        });
    });
    
    // Enhanced loading states for buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(function(button) {
        button.addEventListener('click', function() {
            // Don't add loading state to buttons that have data-no-loading attribute
            if (this.hasAttribute('data-no-loading')) return;
            
            const icon = this.querySelector('i');
            if (icon && !icon.classList.contains('fa-spinner')) {
                const originalClass = icon.className;
                icon.className = 'fas fa-spinner fa-spin me-1';
                
                // Restore after timeout
                setTimeout(function() {
                    icon.className = originalClass;
                }, 2000);
            }
        });
    });
    
    // Console log for debugging
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('DBLogiX Home: Simplified functionality loaded');
    }
}); 