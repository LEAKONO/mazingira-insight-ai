/*
 * Chart.js integration for climate data visualization
 */

class ClimateCharts {
    constructor() {
        this.charts = {};
        this.colors = {
            temperature: 'rgba(255, 99, 132, 0.8)',
            rainfall: 'rgba(54, 162, 235, 0.8)',
            humidity: 'rgba(75, 192, 192, 0.8)',
            airQuality: 'rgba(255, 206, 86, 0.8)',
            prediction: 'rgba(153, 102, 255, 0.8)'
        };
    }
    
    initializeAllCharts() {
        // Temperature chart
        const tempCtx = document.getElementById('temperatureChart');
        if (tempCtx) {
            this.createTemperatureChart(tempCtx);
        }
        
        // Rainfall chart
        const rainCtx = document.getElementById('rainfallChart');
        if (rainCtx) {
            this.createRainfallChart(rainCtx);
        }
        
        // Humidity chart
        const humidityCtx = document.getElementById('humidityChart');
        if (humidityCtx) {
            this.createHumidityChart(humidityCtx);
        }
        
        // Carbon emissions chart
        const carbonCtx = document.getElementById('carbonChart');
        if (carbonCtx) {
            this.createCarbonChart(carbonCtx);
        }
        
        // AQI chart
        const aqiCtx = document.getElementById('aqiChart');
        if (aqiCtx) {
            this.createAQIChart(aqiCtx);
        }
    }
    
    createTemperatureChart(ctx) {
        // Sample data - in production, this would come from API
        const data = {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
            datasets: [{
                label: 'Average Temperature (°C)',
                data: [22.5, 23.1, 22.8, 21.9, 21.2, 20.5, 20.1],
                borderColor: this.colors.temperature,
                backgroundColor: this.colors.temperature.replace('0.8', '0.2'),
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }, {
                label: 'Predicted',
                data: [null, null, null, null, null, null, 20.1, 20.3, 20.5, 20.8, 21.0],
                borderColor: this.colors.prediction,
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false
            }]
        };
        
        this.charts.temperature = new Chart(ctx, {
            type: 'line',
            data: data,
            options: this.getTemperatureOptions()
        });
    }
    
    createRainfallChart(ctx) {
        const data = {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
            datasets: [{
                label: 'Rainfall (mm)',
                data: [50, 45, 80, 120, 150, 100, 70],
                backgroundColor: this.colors.rainfall,
                borderColor: this.colors.rainfall.replace('0.8', '1'),
                borderWidth: 1
            }]
        };
        
        this.charts.rainfall = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: this.getRainfallOptions()
        });
    }
    
    createHumidityChart(ctx) {
        const data = {
            labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
            datasets: [{
                label: 'Humidity (%)',
                data: [85, 90, 75, 60, 55, 70],
                borderColor: this.colors.humidity,
                backgroundColor: this.colors.humidity.replace('0.8', '0.1'),
                borderWidth: 2,
                fill: true
            }]
        };
        
        this.charts.humidity = new Chart(ctx, {
            type: 'line',
            data: data,
            options: this.getHumidityOptions()
        });
    }
    
    createCarbonChart(ctx) {
        const data = {
            labels: ['Transport', 'Electricity', 'Diet', 'Waste'],
            datasets: [{
                label: 'CO₂ Emissions (kg/year)',
                data: [1200, 1800, 2000, 300],
                backgroundColor: [
                    this.colors.temperature,
                    this.colors.rainfall,
                    this.colors.humidity,
                    this.colors.airQuality
                ],
                borderWidth: 1
            }]
        };
        
        this.charts.carbon = new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: this.getCarbonOptions()
        });
    }
    
    createAQIChart(ctx) {
        const data = {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Air Quality Index',
                data: [45, 50, 60, 55, 70, 65, 50],
                borderColor: this.colors.airQuality,
                backgroundColor: this.colors.airQuality.replace('0.8', '0.2'),
                borderWidth: 2,
                fill: true
            }]
        };
        
        this.charts.aqi = new Chart(ctx, {
            type: 'line',
            data: data,
            options: this.getAQIOptions()
        });
    }
    
    getTemperatureOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Temperature Trend'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y}°C`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Temperature (°C)'
                    }
                }
            }
        };
    }
    
    getRainfallOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Monthly Rainfall'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Rainfall (mm)'
                    }
                }
            }
        };
    }
    
    getHumidityOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Daily Humidity Pattern'
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Humidity (%)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        };
    }
    
    getCarbonOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Carbon Footprint Breakdown'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} kg (${percentage}%)`;
                        }
                    }
                }
            }
        };
    }
    
    getAQIOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Air Quality Index'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'AQI'
                    }
                }
            }
        };
    }
    
    updateChartData(chartId, newData) {
        if (this.charts[chartId]) {
            this.charts[chartId].data = newData;
            this.charts[chartId].update();
        }
    }
    
    loadDataFromAPI(endpoint, chartId) {
        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                this.processAPIData(data, chartId);
            })
            .catch(error => {
                console.error('Error loading chart data:', error);
            });
    }
    
    processAPIData(data, chartId) {
        // Process API data based on chart type
        switch(chartId) {
            case 'temperature':
                this.processTemperatureData(data);
                break;
            case 'rainfall':
                this.processRainfallData(data);
                break;
            // Add more cases as needed
        }
    }
    
    processTemperatureData(data) {
        // Extract labels and data from API response
        const labels = data.map(item => {
            return new Date(item.timestamp).toLocaleDateString();
        });
        
        const temperatures = data.map(item => item.temperature);
        
        // Update chart
        if (this.charts.temperature) {
            this.charts.temperature.data.labels = labels;
            this.charts.temperature.data.datasets[0].data = temperatures;
            this.charts.temperature.update();
        }
    }
    
    processRainfallData(data) {
        // Similar processing for rainfall data
    }
    
    // Add prediction line to existing chart
    addPredictions(chartId, predictions) {
        const chart = this.charts[chartId];
        if (!chart) return;
        
        // Add prediction dataset
        chart.data.datasets.push({
            label: 'Prediction',
            data: predictions,
            borderColor: this.colors.prediction,
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0
        });
        
        chart.update();
    }
}

// Initialize charts when page loads
document.addEventListener('DOMContentLoaded', function() {
    const climateCharts = new ClimateCharts();
    climateCharts.initializeAllCharts();
    
    // Make charts available globally for dynamic updates
    window.climateCharts = climateCharts;
    
    // Load real data if available
    if (typeof chartData !== 'undefined') {
        climateCharts.processAPIData(chartData.temperature, 'temperature');
    }
    
    // Set up auto-refresh for real-time data
    setInterval(() => {
        climateCharts.loadDataFromAPI('/api/climate-data/latest/', 'temperature');
    }, 300000); // Refresh every 5 minutes
});