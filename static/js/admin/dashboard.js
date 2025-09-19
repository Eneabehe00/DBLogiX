/**
 * Advanced Dashboard JavaScript - Beautiful Charts with Site Theme
 */

// Global variables for chart instances
let dailyActivityChart = null;
let topProductsChart = null;
let ticketStatusChart = null;
let monthlyTrendsChart = null;
let hourlyActivityChart = null;

// Site color theme
const COLORS = {
    primary: '#2c3e50',
    secondary: '#34495e',
    accent: '#3498db',
    success: '#27ae60',
    warning: '#f39c12',
    danger: '#e74c3c',
    light: '#ecf0f1',
    sidebar: '#203750'
};

// Chart.js default configuration
Chart.defaults.font.family = "'Nunito', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.display = true;
Chart.defaults.plugins.legend.position = 'top';

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all charts
    initializeCharts();
    
    // Make dashboard responsive
    initializeResponsiveFeatures();
    
    // Add interactivity
    initializeInteractivity();
});

/**
 * Initialize all dashboard charts
 */
function initializeCharts() {
    // Get chart data from the template
    const chartsData = getChartsData();
    
    if (!chartsData) {
        console.error('No charts data available');
        return;
    }
    
    // Initialize each chart with delay to prevent layout issues
    setTimeout(() => initializeDailyActivityChart(chartsData.daily_activity), 100);
    setTimeout(() => initializeTopProductsChart(chartsData.top_products), 200);
    setTimeout(() => initializeTicketStatusChart(chartsData.ticket_status), 300);
    setTimeout(() => initializeMonthlyTrendsChart(chartsData.monthly_trends), 400);
    setTimeout(() => initializeHourlyActivityChart(chartsData.hourly_activity), 500);
}

/**
 * Get charts data from template
 */
function getChartsData() {
    try {
        const dataElement = document.getElementById('charts-data');
        if (!dataElement) {
            console.error('Charts data element not found');
            return null;
        }
        return JSON.parse(dataElement.textContent);
    } catch (e) {
        console.error('Error parsing charts data:', e);
        return null;
    }
}

/**
 * Initialize Daily Activity Chart (Line Chart with dual axis)
 */
function initializeDailyActivityChart(data) {
    const ctx = document.getElementById('dailyActivityChart');
    if (!ctx || !data) return;
    
    dailyActivityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Scansioni',
                    data: data.scans,
                    borderColor: COLORS.primary,
                    backgroundColor: COLORS.primary + '20',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: COLORS.primary,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    yAxisID: 'y'
                },
                {
                    label: 'Utenti Attivi',
                    data: data.users,
                    borderColor: COLORS.accent,
                    backgroundColor: COLORS.accent + '20',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: COLORS.accent,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Data',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        color: '#f0f0f0',
                        borderDash: [2, 2]
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Scansioni',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        color: '#f0f0f0',
                        borderDash: [2, 2]
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Utenti Attivi',
                        color: COLORS.accent,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                    beginAtZero: true
                }
            },
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    cornerRadius: 8,
                    displayColors: true,
                    padding: 12
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: { weight: 'bold' }
                    }
                }
            }
        }
    });
}

/**
 * Initialize Top Products Chart (Horizontal Bar Chart)
 */
function initializeTopProductsChart(data) {
    const ctx = document.getElementById('topProductsChart');
    if (!ctx || !data) return;
    
    // Beautiful gradient colors
    const gradientColors = [
        COLORS.primary, COLORS.accent, COLORS.success, COLORS.warning, COLORS.danger,
        COLORS.secondary, '#9b59b6', '#16a085', '#e67e22', '#c0392b'
    ];
    
    topProductsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Vendite',
                data: data.data,
                backgroundColor: gradientColors,
                borderColor: gradientColors,
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Numero Vendite',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        color: '#f0f0f0'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Prodotti',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    cornerRadius: 8,
                    padding: 12
                }
            }
        }
    });
}

/**
 * Initialize Ticket Status Chart (Doughnut Chart)
 */
function initializeTicketStatusChart(data) {
    const ctx = document.getElementById('ticketStatusChart');
    if (!ctx || !data) return;
    
    ticketStatusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: data.colors,
                borderColor: '#ffffff',
                borderWidth: 4,
                hoverOffset: 8,
                hoverBorderWidth: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: { weight: 'bold' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize Monthly Trends Chart (Area Chart)
 */
function initializeMonthlyTrendsChart(data) {
    const ctx = document.getElementById('monthlyTrendsChart');
    if (!ctx || !data) return;
    
    monthlyTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Ticket Mensili',
                data: data.data,
                borderColor: COLORS.success,
                backgroundColor: COLORS.success + '30',
                borderWidth: 4,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: COLORS.success,
                pointBorderColor: '#ffffff',
                pointBorderWidth: 3,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Mese/Anno',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        color: '#f0f0f0',
                        borderDash: [2, 2]
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Numero Ticket',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        color: '#f0f0f0',
                        borderDash: [2, 2]
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    cornerRadius: 8,
                    padding: 12
                }
            }
        }
    });
}

/**
 * Initialize Hourly Activity Chart (Bar Chart)
 */
function initializeHourlyActivityChart(data) {
    const ctx = document.getElementById('hourlyActivityChart');
    if (!ctx || !data) return;
    
    hourlyActivityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Attività Oraria',
                data: data.data,
                backgroundColor: COLORS.accent + '80',
                borderColor: COLORS.accent,
                borderWidth: 2,
                borderRadius: 6,
                borderSkipped: false,
                hoverBackgroundColor: COLORS.accent,
                hoverBorderColor: COLORS.accent,
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Ora',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        color: '#f0f0f0'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Numero Attività',
                        color: COLORS.primary,
                        font: { weight: 'bold' }
                    },
                    grid: {
                        color: '#f0f0f0',
                        borderDash: [2, 2]
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    cornerRadius: 8,
                    padding: 12
                }
            }
        }
    });
}

/**
 * Initialize responsive features
 */
function initializeResponsiveFeatures() {
    // Handle window resize with throttling to prevent infinite loops
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            // Resize all charts
            if (dailyActivityChart) dailyActivityChart.resize();
            if (topProductsChart) topProductsChart.resize();
            if (ticketStatusChart) ticketStatusChart.resize();
            if (monthlyTrendsChart) monthlyTrendsChart.resize();
            if (hourlyActivityChart) hourlyActivityChart.resize();
        }, 250); // Throttle to 250ms
    });
}

/**
 * Initialize interactive features
 */
function initializeInteractivity() {
    // Add hover effects to stat cards
    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Add click events for chart interactions
    addChartClickHandlers();
}

/**
 * Add click handlers for charts
 */
function addChartClickHandlers() {
    // Top products chart click handler
    if (topProductsChart) {
        topProductsChart.options.onClick = function(event, elements) {
            if (elements.length > 0) {
                const elementIndex = elements[0].index;
                const label = this.data.labels[elementIndex];
                const value = this.data.datasets[0].data[elementIndex];
                
                console.log(`Clicked on product: ${label} with ${value} sales`);
                // You could show a modal with detailed product information here
            }
        };
    }
}

/**
 * Utility function to format numbers
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/**
 * Utility function to format currency
 */
function formatCurrency(num) {
    return '€' + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/**
 * Refresh all charts (can be called from outside)
 */
function refreshCharts() {
    // Destroy existing charts
    if (dailyActivityChart) {
        dailyActivityChart.destroy();
        dailyActivityChart = null;
    }
    if (topProductsChart) {
        topProductsChart.destroy();
        topProductsChart = null;
    }
    if (ticketStatusChart) {
        ticketStatusChart.destroy();
        ticketStatusChart = null;
    }
    if (monthlyTrendsChart) {
        monthlyTrendsChart.destroy();
        monthlyTrendsChart = null;
    }
    if (hourlyActivityChart) {
        hourlyActivityChart.destroy();
        hourlyActivityChart = null;
    }
    
    // Reinitialize charts after a small delay
    setTimeout(() => {
        initializeCharts();
    }, 100);
}

// Export functions for external use
window.dashboardCharts = {
    refresh: refreshCharts,
    formatNumber: formatNumber,
    formatCurrency: formatCurrency
}; 