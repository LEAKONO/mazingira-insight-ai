// static/js/climate-charts.js - UPDATED VERSION
// This file is now ONLY for non-dashboard pages

const ClimateCharts = {
    initializeAllCharts: function() {
        console.log('Climate charts initializing...');
        
        if (window.location.pathname === '/' || 
            window.location.pathname === '/dashboard/' || 
            window.location.pathname === '/dashboard') {
            console.log('Skipping climate-charts initialization on dashboard page');
            return;
        }
        
        console.log('Initializing charts for non-dashboard pages...');
        
        this.initializeTemperatureChart();
        
        this.initializeWindChart();
        
        console.log('Climate charts initialized for non-dashboard pages');
    },
    
    initializeTemperatureChart: function() {
        const ctx = document.getElementById('temperatureChart');
        if (!ctx) {
            console.log('No temperature chart canvas found (might be on dashboard)');
            return;
        }
        
        if (document.querySelector('.dashboard-indicator') || 
            document.title.includes('Dashboard')) {
            console.log('Skipping temperature chart - this is dashboard');
            return;
        }
        
        console.log('Creating temperature chart for non-dashboard page');
        
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const avgTemperatures = [23.5, 24.1, 23.8, 22.9, 22.2, 21.5, 20.8, 21.1, 22.0, 22.8, 23.2, 23.4];
        
        try {
            if (ctx.chart) {
                ctx.chart.destroy();
            }
            
            ctx.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: months,
                    datasets: [{
                        label: 'Sample Temperature (°C)',
                        data: avgTemperatures,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Sample Temperature Pattern',
                            font: {
                                size: 16,
                                weight: 'bold'
                            }
                        }
                    }
                }
            });
            
            console.log('Temperature chart created for non-dashboard page');
        } catch (error) {
            console.error('Error creating temperature chart:', error);
        }
    },
    
    initializeWindChart: function() {
        const ctx = document.getElementById('windChart');
        if (!ctx) {
            console.log('No wind chart canvas found (might be on dashboard)');
            return;
        }
        
        if (document.querySelector('.dashboard-indicator') || 
            document.title.includes('Dashboard')) {
            console.log('Skipping wind chart - this is dashboard');
            return;
        }
        
        console.log('Creating wind chart for non-dashboard page');
        
        const regions = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret'];
        const windSpeeds = [3.2, 4.5, 2.8, 3.1, 2.9];
        
        try {
            if (ctx.chart) {
                ctx.chart.destroy();
            }
            
            ctx.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: regions,
                    datasets: [{
                        label: 'Sample Wind Speed (m/s)',
                        data: windSpeeds,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Sample Wind Comparison',
                            font: {
                                size: 16,
                                weight: 'bold'
                            }
                        }
                    }
                }
            });
            
            console.log('Wind chart created for non-dashboard page');
        } catch (error) {
            console.error('Error creating wind chart:', error);
        }
    }
};

window.climateCharts = ClimateCharts;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, checking if we should initialize climate charts...');
    
    const isDashboard = window.location.pathname === '/' || 
                       window.location.pathname === '/dashboard/' || 
                       window.location.pathname === '/dashboard' ||
                       document.title.includes('Dashboard');
    
    if (!isDashboard) {
        console.log('Not on dashboard, initializing climate charts...');
        if (window.climateCharts && typeof window.climateCharts.initializeAllCharts === 'function') {
            window.climateCharts.initializeAllCharts();
        }
    } else {
        console.log('On dashboard page - climate charts will be handled by dashboard-specific code');
    }
});