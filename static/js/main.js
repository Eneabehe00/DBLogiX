/**
 * DBLogiX - Main JavaScript
 * Contains global functions and utilities used across the application
 */

// Execute when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-close alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Initialize Bootstrap tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltips.length > 0) {
        tooltips.forEach(function(tooltip) {
            new bootstrap.Tooltip(tooltip);
        });
    }
    
    // Initialize Bootstrap popovers
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    if (popovers.length > 0) {
        popovers.forEach(function(popover) {
            new bootstrap.Popover(popover);
        });
    }
    
    // Initialize Select2 for all select elements with the select2 class
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            theme: 'bootstrap-5',
            width: '100%'
        });
    }
    
    // Responsive tables - add data-label attributes to make them responsive
    const responsiveTables = document.querySelectorAll('.table-responsive table');
    if (responsiveTables.length > 0) {
        responsiveTables.forEach(function(table) {
            const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
            
            table.querySelectorAll('tbody tr').forEach(function(row) {
                row.querySelectorAll('td').forEach(function(cell, index) {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        });
    }
    
    // Handle clickable table rows globally
    const handleClickableRows = function() {
        const clickableRows = document.querySelectorAll('.clickable-row, .home-table-row');
        clickableRows.forEach(function(row) {
            // Add keyboard accessibility
            if (!row.hasAttribute('tabindex')) {
                row.setAttribute('tabindex', '0');
            }
            if (!row.hasAttribute('role')) {
                row.setAttribute('role', 'button');
            }
            
            // Remove existing event listeners to prevent duplicates
            const newRow = row.cloneNode(true);
            row.parentNode.replaceChild(newRow, row);
            
            // Handle click events
            newRow.addEventListener('click', function(e) {
                // Don't trigger if clicking on buttons, links, or form elements
                if (e.target.closest('button, a, input, select, textarea, .btn')) {
                    return;
                }
                
                e.preventDefault();
                
                const href = this.getAttribute('data-href');
                if (href && href !== '#' && href !== '') {
                    // Add visual feedback
                    this.style.transform = 'scale(0.98)';
                    this.style.transition = 'transform 0.1s ease';
                    
                    // Navigate after brief delay for visual feedback
                    setTimeout(function() {
                        window.location.href = href;
                    }, 100);
                }
            });
            
            // Handle keyboard navigation
            newRow.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
            
            // Add hover effects for better UX
            newRow.addEventListener('mouseenter', function() {
                if (!this.style.backgroundColor || this.style.backgroundColor === '') {
                    this.style.backgroundColor = 'rgba(13, 110, 253, 0.05)';
                }
            });
            
            newRow.addEventListener('mouseleave', function() {
                if (this.style.backgroundColor === 'rgba(13, 110, 253, 0.05)') {
                    this.style.backgroundColor = '';
                }
            });
        });
    };
    
    // Initialize clickable rows
    handleClickableRows();
    
    // Reinitialize clickable rows when content is dynamically loaded
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        const newClickableRows = node.querySelectorAll ? node.querySelectorAll('.clickable-row, .home-table-row') : [];
                        if (newClickableRows.length > 0 || node.classList?.contains('clickable-row') || node.classList?.contains('home-table-row')) {
                            setTimeout(handleClickableRows, 100);
                        }
                    }
                });
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Initialize date pickers if present
    if (typeof $.fn.datepicker !== 'undefined') {
        $('.datepicker').datepicker({
            format: 'dd/mm/yyyy',
            autoclose: true,
            language: 'it'
        });
    }
    
    // Fix layout issues on window resize
    window.addEventListener('resize', function() {
        fixLayoutIssues();
    });
    
    // Call once on page load
    fixLayoutIssues();
    
    /**
     * Fix common layout issues
     */
    function fixLayoutIssues() {
        // Ensure main content has proper width and margin on desktop
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (!sidebar || !mainContent) return;
        
        if (window.innerWidth >= 768) {
            if (sidebar.classList.contains('collapsed')) {
                const collapsedWidth = getComputedStyle(document.documentElement)
                    .getPropertyValue('--sidebar-width-collapsed').trim();
                mainContent.style.width = `calc(100% - ${collapsedWidth})`;
                mainContent.style.marginLeft = collapsedWidth;
            } else {
                const sidebarWidth = getComputedStyle(document.documentElement)
                    .getPropertyValue('--sidebar-width').trim();
                mainContent.style.width = `calc(100% - ${sidebarWidth})`;
                mainContent.style.marginLeft = sidebarWidth;
            }
        } else {
            mainContent.style.width = '100%';
            mainContent.style.marginLeft = '0';
        }
    }
    
    // Handle form validation
    const forms = document.querySelectorAll('.needs-validation');
    if (forms.length > 0) {
        forms.forEach(function(form) {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                form.classList.add('was-validated');
            }, false);
        });
    }
    
    // Handle confirmation dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm'))) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        });
    });
    
    // Handle search form submissions
    const searchForms = document.querySelectorAll('form.search-form');
    searchForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const searchInput = this.querySelector('input[type="search"], input[name="query"]');
            if (searchInput && searchInput.value.trim() === '') {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // Enable CSV exports for tables
    const exportButtons = document.querySelectorAll('.btn-export-csv');
    exportButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const tableId = this.getAttribute('data-table-id');
            const table = document.getElementById(tableId);
            
            if (!table) return;
            
            let csv = [];
            const rows = table.querySelectorAll('tr');
            
            rows.forEach(function(row) {
                let rowData = [];
                const cols = row.querySelectorAll('th, td');
                
                cols.forEach(function(col) {
                    // Clean up the text (remove extra spaces, newlines)
                    let text = col.innerText.replace(/(\r\n|\n|\r)/gm, ' ').replace(/\s+/g, ' ').trim();
                    // Escape double quotes with another double quote
                    text = text.replace(/"/g, '""');
                    // Enclose with double quotes to handle commas and other characters
                    rowData.push('"' + text + '"');
                });
                
                csv.push(rowData.join(','));
            });
            
            // Create and download the CSV file
            const csvContent = 'data:text/csv;charset=utf-8,' + csv.join('\n');
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement('a');
            link.setAttribute('href', encodedUri);
            link.setAttribute('download', 'export_' + new Date().toISOString().slice(0,10) + '.csv');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    });

    // Add CSRF token to AJAX requests
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    }
    
    // Hook into fetch requests to add CSRF token
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        // Only add for POST, PUT, DELETE methods
        if (options.method && ['POST', 'PUT', 'DELETE'].includes(options.method.toUpperCase())) {
            const token = getCsrfToken();
            if (token) {
                if (!options.headers) {
                    options.headers = {};
                }
                
                if (options.headers instanceof Headers) {
                    options.headers.append('X-CSRFToken', token);
                } else {
                    options.headers['X-CSRFToken'] = token;
                }
            }
        }
        
        return originalFetch(url, options);
    };
    
    // Test database connection button
    const testDbButton = document.getElementById('test-db-connection');
    if (testDbButton) {
        testDbButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get form data
            const form = this.closest('form');
            const formData = new FormData(form);
            const data = {
                host: formData.get('host'),
                user: formData.get('user'),
                password: formData.get('password'),
                database: formData.get('database'),
                port: formData.get('port')
            };
            
            // Update button state
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Testing...';
            
            // Send test request
            fetch('/admin/test-db-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                // Show result
                let alertClass = data.success ? 'success' : 'danger';
                let alertMessage = data.message;
                
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${alertClass} alert-dismissible fade show`;
                alertDiv.innerHTML = `
                    ${alertMessage}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                
                const resultContainer = document.getElementById('db-test-result');
                if (resultContainer) {
                    resultContainer.innerHTML = '';
                    resultContainer.appendChild(alertDiv);
                }
                
                // Reset button
                this.disabled = false;
                this.innerHTML = 'Test Connection';
            })
            .catch(error => {
                console.error('Error testing connection:', error);
                
                // Show error
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-danger alert-dismissible fade show';
                alertDiv.innerHTML = `
                    An error occurred during the test. Please try again.
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                
                const resultContainer = document.getElementById('db-test-result');
                if (resultContainer) {
                    resultContainer.innerHTML = '';
                    resultContainer.appendChild(alertDiv);
                }
                
                // Reset button
                this.disabled = false;
                this.innerHTML = 'Test Connection';
            });
        });
    }
    
    // Debug logging for development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('DBLogiX Main: Enhanced table interactions loaded');
        console.log('Features: Clickable rows, responsive tables, accessibility improvements');
    }
}); 