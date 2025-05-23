/**
 * DBLogiX - Home Page JavaScript
 * Adds interactive functionality to the home page
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(function(tooltip) {
        new bootstrap.Tooltip(tooltip);
    });
    
    // Add hover effects to stat cards
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Add click handler for quick action items
    const quickActions = document.querySelectorAll('.quick-action-item');
    quickActions.forEach(function(action) {
        action.addEventListener('click', function(e) {
            // Add a ripple effect when clicked
            const ripple = document.createElement('div');
            ripple.classList.add('ripple-effect');
            
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            
            this.appendChild(ripple);
            
            // Remove the ripple after animation completes
            setTimeout(function() {
                ripple.remove();
            }, 600);
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
    
    // Add animation to empty states
    const emptyStates = document.querySelectorAll('.empty-state');
    emptyStates.forEach(function(state) {
        state.style.opacity = '0';
        state.style.transform = 'translateY(20px)';
        
        setTimeout(function() {
            state.style.transition = 'all 0.5s ease';
            state.style.opacity = '1';
            state.style.transform = 'translateY(0)';
        }, 100);
    });
    
    // Add CSS for ripple effect
    const style = document.createElement('style');
    style.textContent = `
        .ripple-effect {
            position: absolute;
            background-color: rgba(255, 255, 255, 0.7);
            border-radius: 50%;
            width: 100px;
            height: 100px;
            margin-top: -50px;
            margin-left: -50px;
            transform: scale(0);
            animation: ripple 0.6s linear;
            pointer-events: none;
        }
        
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        .quick-action-item {
            position: relative;
            overflow: hidden;
        }
    `;
    document.head.appendChild(style);
}); 