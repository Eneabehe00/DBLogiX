/**
 * Dashboard admin chart and data handling
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeActivityChart();
    
    // Make the dashboard cards responsive
    initializeResponsiveCards();
});

/**
 * Initialize the activity chart
 */
function initializeActivityChart() {
    // Get the canvas element
    const chartCanvas = document.getElementById('activityChart');
    
    if (!chartCanvas) return;
    
    const ctx = chartCanvas.getContext('2d');
    
    // Get the data element
    const activityDataElement = document.querySelector('[data-activity]');
    let activityData;
    
    try {
        // Try to get data from the data attribute if available
        if (activityDataElement) {
            activityData = JSON.parse(activityDataElement.dataset.activity);
        } else {
            // Fall back to the template-rendered JSON
            // This is inserted by the server via template variable
            activityData = JSON.parse(document.getElementById('activity-data-json').textContent);
        }
    } catch (e) {
        console.error('Error parsing activity data:', e);
        return;
    }
    
    // Create the chart
    const myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: activityData.labels,
            datasets: [{
                label: 'Numero di Scansioni',
                data: activityData.data,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true,
                pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
    
    // Add resize handler for better responsiveness
    window.addEventListener('resize', function() {
        myChart.resize();
    });
}

/**
 * Make dashboard cards responsive
 */
function initializeResponsiveCards() {
    // Check if we're on a mobile device
    if (window.innerWidth < 768) {
        // Remove border-end classes on mobile for better stacking
        document.querySelectorAll('.border-end').forEach(function(el) {
            el.classList.remove('border-end');
            el.classList.add('border-bottom');
        });
    }
    
    // Ensure equal height cards in the same row on desktop
    if (window.innerWidth >= 768) {
        const cardRows = document.querySelectorAll('.row');
        
        cardRows.forEach(function(row) {
            const cards = row.querySelectorAll('.card');
            let maxHeight = 0;
            
            // Find the tallest card
            cards.forEach(function(card) {
                const height = card.offsetHeight;
                if (height > maxHeight) {
                    maxHeight = height;
                }
            });
            
            // Set all cards to the same height
            cards.forEach(function(card) {
                card.style.height = maxHeight + 'px';
            });
        });
    }
} 