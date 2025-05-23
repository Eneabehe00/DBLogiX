/**
 * Responsive behavior management for DB-LogiX application
 */
document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            content.classList.toggle('sidebar-active');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        const isMobile = window.innerWidth < 768;
        
        if (isMobile && sidebar.classList.contains('active') && 
            !sidebar.contains(event.target) && 
            event.target !== mobileMenuToggle) {
            sidebar.classList.remove('active');
            content.classList.remove('sidebar-active');
        }
    });
    
    // Submenu toggle for sidebar
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    
    submenuToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const parent = this.parentElement;
            
            // If it's already open and we're on mobile, just close it
            if (parent.classList.contains('open') && window.innerWidth < 768) {
                parent.classList.remove('open');
                return;
            }
            
            // Close all other open submenus on mobile
            if (window.innerWidth < 768) {
                document.querySelectorAll('.sidebar-submenu.open').forEach(function(item) {
                    if (item !== parent) {
                        item.classList.remove('open');
                    }
                });
            }
            
            // Toggle the clicked submenu
            parent.classList.toggle('open');
        });
    });
    
    // Make tables responsive
    const tables = document.querySelectorAll('table');
    
    tables.forEach(function(table) {
        // Skip tables that are already in a responsive container
        if (!table.parentElement.classList.contains('table-responsive')) {
            // Add data-label attributes to table cells for responsive view
            const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
            
            table.querySelectorAll('tbody tr').forEach(function(row) {
                const cells = row.querySelectorAll('td');
                cells.forEach(function(cell, index) {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        }
    });
    
    // Adjust charts on window resize for responsiveness
    window.addEventListener('resize', function() {
        if (typeof Chart !== 'undefined' && Chart.instances) {
            for (let id in Chart.instances) {
                Chart.instances[id].resize();
            }
        }
    });
    
    // Handle modals on small screens
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(function(modal) {
        modal.addEventListener('shown.bs.modal', function() {
            if (window.innerWidth < 576) {
                modal.querySelector('.modal-dialog').classList.add('modal-dialog-scrollable');
            }
        });
    });
}); 