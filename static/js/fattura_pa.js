/**
 * Fatture PA JavaScript Functions
 * Handles filtering, searching, viewing and managing electronic invoices
 */

(function() {
    'use strict';

    // DOM Elements
    let searchInput, clientFilter, dateFromFilter, dateToFilter, clearFiltersBtn;
    let activeFilters, filterBadges, invoicesTable, invoiceCount;
    
    // Data
    let allInvoices = [];
    let filteredInvoices = [];

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeElements();
        initializeEventListeners();
        loadInitialData();
        setupRowClickHandlers();
        calculateStatistics();
        loadClientNamesFromXML();
    });

    function initializeElements() {
        // Filter elements
        searchInput = document.getElementById('searchInput');
        clientFilter = document.getElementById('clientFilter');
        dateFromFilter = document.getElementById('dateFromFilter');
        dateToFilter = document.getElementById('dateToFilter');
        clearFiltersBtn = document.getElementById('clearFilters');
        
        // Display elements
        activeFilters = document.getElementById('activeFilters');
        filterBadges = document.getElementById('filterBadges');
        invoicesTable = document.getElementById('invoicesTable');
        invoiceCount = document.getElementById('invoiceCount');
    }

    function initializeEventListeners() {
        // Search and filter events
        if (searchInput) {
            searchInput.addEventListener('input', debounce(applyFilters, 300));
        }
        
        if (clientFilter) {
            clientFilter.addEventListener('change', applyFilters);
        }
        
        if (dateFromFilter) {
            dateFromFilter.addEventListener('change', applyFilters);
        }
        
        if (dateToFilter) {
            dateToFilter.addEventListener('change', applyFilters);
        }
        
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', clearAllFilters);
        }
    }

    function loadInitialData() {
        // Extract invoice data from table rows
        if (invoicesTable) {
            const rows = invoicesTable.querySelectorAll('tbody tr.invoice-row');
            allInvoices = Array.from(rows).map(row => {
                const cells = row.querySelectorAll('td');
                return {
                    element: row,
                    filename: row.dataset.filename,
                    number: cells[0]?.textContent?.trim() || '',
                    date: cells[1]?.textContent?.trim() || '',
                    client: cells[2]?.textContent?.trim() || '',
                    fileDisplay: cells[3]?.textContent?.trim() || '',
                    size: cells[4]?.textContent?.trim() || ''
                };
            });
            
            filteredInvoices = [...allInvoices];
        }
    }

    function loadClientNamesFromXML() {
        // Load client names for each invoice from XML
        allInvoices.forEach(invoice => {
            fetch(`/fattura_pa/details/${invoice.filename}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.data.client_name) {
                        // Update the client cell in the table
                        const clientCell = invoice.element.cells[2];
                        clientCell.innerHTML = `<span>${data.data.client_name}</span>`;
                        
                        // Update our data
                        invoice.client = data.data.client_name;
                        
                        // Update client filter options
                        updateClientFilterOptions();
                    }
                })
                .catch(error => {
                    console.log(`Could not load client name for ${invoice.filename}`);
                });
        });
    }

    function updateClientFilterOptions() {
        if (!clientFilter) return;
        
        // Get unique client names
        const clients = new Set();
        allInvoices.forEach(invoice => {
            if (invoice.client && invoice.client !== 'Caricamento...' && invoice.client.trim() !== '') {
                clients.add(invoice.client);
            }
        });
        
        // Clear existing options (except the first one)
        while (clientFilter.children.length > 1) {
            clientFilter.removeChild(clientFilter.lastChild);
        }
        
        // Add client options
        clients.forEach(client => {
            const option = document.createElement('option');
            option.value = client;
            option.textContent = client;
            clientFilter.appendChild(option);
        });
    }

    function setupRowClickHandlers() {
        if (invoicesTable) {
            const rows = invoicesTable.querySelectorAll('tbody tr.invoice-row');
            rows.forEach(row => {
                row.addEventListener('click', function() {
                    const filename = this.dataset.filename;
                    if (filename) {
                        // Navigate to detail page
                        window.location.href = `/fattura_pa/detail/${filename}`;
                    }
                });
            });
        }
    }

    function applyFilters() {
        const searchTerm = searchInput?.value?.toLowerCase() || '';
        const selectedClient = clientFilter?.value || '';
        const dateFrom = dateFromFilter?.value || '';
        const dateTo = dateToFilter?.value || '';
        
        filteredInvoices = allInvoices.filter(invoice => {
            // Search filter
            if (searchTerm) {
                const searchableText = `${invoice.number} ${invoice.client} ${invoice.fileDisplay} ${invoice.filename}`.toLowerCase();
                if (!searchableText.includes(searchTerm)) {
                    return false;
                }
            }
            
            // Client filter
            if (selectedClient) {
                if (invoice.client !== selectedClient) {
                    return false;
                }
            }
            
            // Date filters
            if (dateFrom || dateTo) {
                const invoiceDate = parseDateFromString(invoice.date);
                if (invoiceDate) {
                    if (dateFrom) {
                        const fromDate = new Date(dateFrom);
                        if (invoiceDate < fromDate) {
                            return false;
                        }
                    }
                    
                    if (dateTo) {
                        const toDate = new Date(dateTo);
                        toDate.setHours(23, 59, 59, 999); // End of day
                        if (invoiceDate > toDate) {
                            return false;
                        }
                    }
                }
            }
            
            return true;
        });
        
        updateTableDisplay();
        updateFilterBadges();
        updateStatistics();
    }

    function updateTableDisplay() {
        if (!invoicesTable) return;
        
        const tbody = invoicesTable.querySelector('tbody');
        if (!tbody) return;
        
        // Hide all rows first
        allInvoices.forEach(invoice => {
            invoice.element.style.display = 'none';
        });
        
        // Show filtered rows
        filteredInvoices.forEach(invoice => {
            invoice.element.style.display = '';
        });
        
        // Update count
        if (invoiceCount) {
            invoiceCount.textContent = `${filteredInvoices.length} fatture`;
        }
        
        // Show empty state if no results
        showEmptyState(filteredInvoices.length === 0);
    }

    function updateFilterBadges() {
        if (!filterBadges) return;
        
        filterBadges.innerHTML = '';
        let hasActiveFilters = false;
        
        // Search badge
        const searchTerm = searchInput?.value || '';
        if (searchTerm) {
            addFilterBadge('Ricerca', searchTerm, () => {
                searchInput.value = '';
                applyFilters();
            });
            hasActiveFilters = true;
        }
        
        // Client badge
        const selectedClient = clientFilter?.value || '';
        if (selectedClient) {
            addFilterBadge('Cliente', selectedClient, () => {
                clientFilter.value = '';
                applyFilters();
            });
            hasActiveFilters = true;
        }
        
        // Date badges
        const dateFrom = dateFromFilter?.value || '';
        const dateTo = dateToFilter?.value || '';
        if (dateFrom) {
            addFilterBadge('Da', formatDate(dateFrom), () => {
                dateFromFilter.value = '';
                applyFilters();
            });
            hasActiveFilters = true;
        }
        
        if (dateTo) {
            addFilterBadge('A', formatDate(dateTo), () => {
                dateToFilter.value = '';
                applyFilters();
            });
            hasActiveFilters = true;
        }
        
        // Show/hide active filters section
        if (activeFilters) {
            activeFilters.style.display = hasActiveFilters ? 'block' : 'none';
        }
    }

    function addFilterBadge(label, value, removeCallback) {
        const badge = document.createElement('span');
        badge.className = 'badge bg-primary me-2 mb-2';
        badge.innerHTML = `
            ${label}: ${value}
            <i class="fas fa-times ms-2" style="cursor: pointer;"></i>
        `;
        
        const removeIcon = badge.querySelector('.fa-times');
        removeIcon.addEventListener('click', removeCallback);
        
        filterBadges.appendChild(badge);
    }

    function clearAllFilters() {
        if (searchInput) searchInput.value = '';
        if (clientFilter) clientFilter.value = '';
        if (dateFromFilter) dateFromFilter.value = '';
        if (dateToFilter) dateToFilter.value = '';
        
        applyFilters();
    }

    function showEmptyState(show) {
        if (invoicesTable) {
            const tbody = invoicesTable.querySelector('tbody');
            if (show && filteredInvoices.length === 0 && allInvoices.length > 0) {
                // Show "no results found" message
                if (!tbody.querySelector('.no-results-row')) {
                    const row = document.createElement('tr');
                    row.className = 'no-results-row';
                    row.innerHTML = `
                        <td colspan="5" class="text-center py-4">
                            <i class="fas fa-search fa-2x text-muted mb-2"></i>
                            <div class="text-muted">Nessuna fattura trovata con i filtri applicati</div>
                        </td>
                    `;
                    tbody.appendChild(row);
                }
            } else {
                // Remove "no results" message
                const noResultsRow = tbody.querySelector('.no-results-row');
                if (noResultsRow) {
                    noResultsRow.remove();
                }
            }
        }
    }

    function calculateStatistics() {
        // Calculate monthly count
        const currentMonth = new Date().getMonth();
        const currentYear = new Date().getFullYear();
        
        let monthlyCount = 0;
        allInvoices.forEach(invoice => {
            const invoiceDate = parseDateFromString(invoice.date);
            if (invoiceDate && 
                invoiceDate.getMonth() === currentMonth && 
                invoiceDate.getFullYear() === currentYear) {
                monthlyCount++;
            }
        });
        
        const monthlyCountElement = document.getElementById('monthlyCount');
        if (monthlyCountElement) {
            monthlyCountElement.textContent = monthlyCount;
        }
    }

    function updateStatistics() {
        // Update filtered count in stats if needed
        // This could be extended to show filtered statistics
    }

    // Utility Functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function parseDateFromString(dateString) {
        if (!dateString) return null;
        
        // Try to parse DD/MM/YYYY format
        const dateComponents = dateString.split('/');
        if (dateComponents.length === 3) {
            const day = parseInt(dateComponents[0]);
            const month = parseInt(dateComponents[1]) - 1; // Month is 0-based
            const year = parseInt(dateComponents[2]);
            return new Date(year, month, day);
        }
        
        return null;
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('it-IT');
    }

    function showAlert(type, message) {
        // Create and show a Bootstrap alert
        const alertContainer = document.querySelector('.flash-container') || document.body;
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        alertContainer.insertBefore(alert, alertContainer.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

})(); 