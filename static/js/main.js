/**
 * DBLogiX - Main JavaScript
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
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(function(tooltip) {
        new bootstrap.Tooltip(tooltip);
    });
    
    // Initialize popovers
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(function(popover) {
        new bootstrap.Popover(popover);
    });
    
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
}); 