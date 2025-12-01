/*
 * Carbon Calculator JavaScript
 */

class CarbonCalculator {
    constructor() {
        this.form = document.getElementById('carbonCalculatorForm');
        this.resultDiv = document.getElementById('carbonResult');
        this.chartCanvas = document.getElementById('carbonChart');
        this.chart = null;
        
        this.emissionFactors = {
            transport: {
                petrol: 0.12,    // kg CO2e per km
                diesel: 0.13,
                hybrid: 0.08,
                electric: 0.05,
                none: 0
            },
            electricity: 0.5,    // kg CO2e per kWh (Kenya average)
            diet: {
                vegetarian: 1000,
                meat_light: 1500,
                meat_medium: 2000,
                meat_heavy: 3000
            },
            waste: 0.5,          // kg CO2e per kg waste
            flights: 0.2,        // kg CO2e per passenger-km (approx)
            public_transport: 0.05
        };
        
        this.initializeEventListeners();
        this.initializeForm();
    }
    
    initializeEventListeners() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            this.form.addEventListener('input', () => this.updateLiveEstimate());
        }
        
        // Add event listeners for dynamic updates
        const inputs = this.form?.querySelectorAll('input, select');
        inputs?.forEach(input => {
            input.addEventListener('change', () => this.updateLiveEstimate());
        });
    }
    
    initializeForm() {
        // Set default values or restore from localStorage
        this.restoreFormData();
        this.updateLiveEstimate();
    }
    
    restoreFormData() {
        // Try to restore form data from localStorage
        try {
            const savedData = localStorage.getItem('carbonCalculatorData');
            if (savedData) {
                const data = JSON.parse(savedData);
                Object.keys(data).forEach(key => {
                    const element = this.form?.querySelector(`[name="${key}"]`);
                    if (element) {
                        if (element.type === 'checkbox' || element.type === 'radio') {
                            element.checked = data[key];
                        } else {
                            element.value = data[key];
                        }
                    }
                });
            }
        } catch (e) {
            console.log('No saved form data found');
        }
    }
    
    saveFormData() {
        const formData = new FormData(this.form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        localStorage.setItem('carbonCalculatorData', JSON.stringify(data));
    }
    
    async handleSubmit(event) {
        event.preventDefault();
        
        // Show loading state
        this.showLoading();
        
        // Calculate emissions
        const emissions = this.calculateEmissions();
        
        // Save form data
        this.saveFormData();
        
        // Show results
        this.displayResults(emissions);
        
        // Generate suggestions
        const suggestions = this.generateSuggestions(emissions);
        this.displaySuggestions(suggestions);
        
        // Update chart
        this.updateChart(emissions);
        
        // Send to server if user is logged in
        if (this.isUserLoggedIn()) {
            await this.saveToServer(emissions);
        }
        
        // Scroll to results
        this.resultDiv?.scrollIntoView({ behavior: 'smooth' });
    }
    
    calculateEmissions() {
        const formData = new FormData(this.form);
        const data = Object.fromEntries(formData.entries());
        
        // Parse numeric values
        const carKm = parseFloat(data.car_km) || 0;
        const publicTransportKm = parseFloat(data.public_transport_km) || 0;
        const electricityKwh = parseFloat(data.electricity_kwh) || 0;
        const wasteKg = parseFloat(data.waste_kg) || 0;
        const flightsHours = parseFloat(data.flights_hours) || 0;
        const householdSize = parseInt(data.household_size) || 1;
        
        // Calculate emissions
        const transportEmissions = this.calculateTransportEmissions(
            data.car_type, carKm, publicTransportKm, flightsHours
        );
        
        const electricityEmissions = this.calculateElectricityEmissions(
            electricityKwh, data.renewable_energy, householdSize
        );
        
        const dietEmissions = this.calculateDietEmissions(data.diet_type);
        const wasteEmissions = this.calculateWasteEmissions(wasteKg);
        
        // Total emissions (per year)
        const totalEmissions = 
            transportEmissions + 
            electricityEmissions + 
            dietEmissions + 
            wasteEmissions;
        
        // Per capita emissions
        const perCapitaEmissions = totalEmissions / householdSize;
        
        return {
            transport: transportEmissions,
            electricity: electricityEmissions,
            diet: dietEmissions,
            waste: wasteEmissions,
            total: totalEmissions,
            perCapita: perCapitaEmissions,
            householdSize: householdSize,
            emissionLevel: this.getEmissionLevel(perCapitaEmissions)
        };
    }
    
    calculateTransportEmissions(carType, carKm, publicTransportKm, flightsHours) {
        // Car emissions (weekly to yearly)
        const carEmissions = carKm * 52 * this.emissionFactors.transport[carType];
        
        // Public transport emissions
        const publicTransportEmissions = publicTransportKm * 52 * this.emissionFactors.public_transport;
        
        // Flight emissions (approx 800 km/h average speed)
        const flightKm = flightsHours * 800;
        const flightEmissions = flightKm * this.emissionFactors.flights;
        
        return carEmissions + publicTransportEmissions + flightEmissions;
    }
    
    calculateElectricityEmissions(electricityKwh, renewableLevel, householdSize) {
        // Adjust for renewable energy
        const renewableFactors = {
            'none': 1.0,
            'some': 0.7,
            'most': 0.3,
            'all': 0.1
        };
        
        const factor = renewableFactors[renewableLevel] || 1.0;
        
        // Monthly to yearly, adjusted for household size (per capita)
        return (electricityKwh * 12 * this.emissionFactors.electricity * factor) / householdSize;
    }
    
    calculateDietEmissions(dietType) {
        return this.emissionFactors.diet[dietType] || this.emissionFactors.diet.meat_medium;
    }
    
    calculateWasteEmissions(wasteKg) {
        // Weekly to yearly
        return wasteKg * 52 * this.emissionFactors.waste;
    }
    
    getEmissionLevel(perCapitaEmissions) {
        if (perCapitaEmissions < 2000) return { level: 'low', label: 'Low', color: 'success' };
        if (perCapitaEmissions < 5000) return { level: 'moderate', label: 'Moderate', color: 'warning' };
        if (perCapitaEmissions < 10000) return { level: 'high', label: 'High', color: 'danger' };
        return { level: 'very_high', label: 'Very High', color: 'danger' };
    }
    
    displayResults(emissions) {
        if (!this.resultDiv) return;
        
        const emissionLevel = emissions.emissionLevel;
        
        this.resultDiv.innerHTML = `
            <div class="carbon-result">
                <h3 class="mb-3">
                    <i class="fas fa-leaf me-2"></i>Your Carbon Footprint Results
                </h3>
                
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="stat-card">
                            <div class="stat-value">${emissions.total.toLocaleString()}</div>
                            <div class="stat-label">Total CO₂e (kg/year)</div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="stat-card">
                            <div class="stat-value">${emissions.perCapita.toLocaleString()}</div>
                            <div class="stat-label">Per Capita CO₂e (kg/year)</div>
                        </div>
                    </div>
                </div>
                
                <div class="alert alert-${emissionLevel.color}">
                    <h5 class="alert-heading">
                        <i class="fas fa-${this.getEmissionIcon(emissionLevel.level)} me-2"></i>
                        ${emissionLevel.label} Emission Level
                    </h5>
                    <p class="mb-0">${this.getEmissionDescription(emissionLevel.level)}</p>
                </div>
                
                <h5 class="mt-4 mb-3">Emission Breakdown</h5>
                <div class="emission-breakdown">
                    ${this.createBreakdownHTML(emissions)}
                </div>
                
                <div id="suggestionsContainer" class="mt-4"></div>
            </div>
        `;
        
        this.resultDiv.style.display = 'block';
    }
    
    createBreakdownHTML(emissions) {
        const categories = [
            { name: 'Transport', value: emissions.transport, color: 'var(--secondary-color)' },
            { name: 'Electricity', value: emissions.electricity, color: 'var(--accent-color)' },
            { name: 'Diet', value: emissions.diet, color: 'var(--primary-color)' },
            { name: 'Waste', value: emissions.waste, color: 'var(--gray-dark)' }
        ];
        
        const total = emissions.total;
        
        return categories.map(category => {
            const percentage = total > 0 ? (category.value / total * 100).toFixed(1) : 0;
            
            return `
                <div class="mb-3">
                    <div class="d-flex justify-content-between mb-1">
                        <span>${category.name}</span>
                        <span>${category.value.toLocaleString()} kg (${percentage}%)</span>
                    </div>
                    <div class="progress" style="height: 20px;">
                        <div class="progress-bar" 
                             role="progressbar" 
                             style="width: ${percentage}%; background-color: ${category.color};"
                             aria-valuenow="${percentage}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    generateSuggestions(emissions) {
        const suggestions = [];
        
        // Transportation suggestions
        if (emissions.transport > 2000) {
            suggestions.push({
                category: 'Transport',
                title: 'Reduce Car Usage',
                description: 'Consider carpooling, using public transport, or cycling for short trips.',
                impact: 'High',
                savings: 'Up to 1000 kg CO₂e/year'
            });
        }
        
        // Electricity suggestions
        if (emissions.electricity > 1500) {
            suggestions.push({
                category: 'Electricity',
                title: 'Switch to Renewable Energy',
                description: 'Install solar panels or switch to a green energy provider.',
                impact: 'Medium',
                savings: 'Up to 750 kg CO₂e/year'
            });
        }
        
        // Diet suggestions
        if (emissions.diet > 2000) {
            suggestions.push({
                category: 'Diet',
                title: 'Reduce Meat Consumption',
                description: 'Try vegetarian meals 2-3 times per week.',
                impact: 'High',
                savings: 'Up to 1000 kg CO₂e/year'
            });
        }
        
        // General suggestions
        suggestions.push({
            category: 'General',
            title: 'Plant Trees',
            description: 'Each tree absorbs about 21 kg of CO₂ per year.',
            impact: 'Low',
            savings: '21 kg CO₂e/year per tree'
        });
        
        return suggestions;
    }
    
    displaySuggestions(suggestions) {
        const container = document.getElementById('suggestionsContainer');
        if (!container) return;
        
        container.innerHTML = `
            <h5 class="mb-3">
                <i class="fas fa-lightbulb me-2"></i>Reduction Suggestions
            </h5>
            <div class="row">
                ${suggestions.map(suggestion => `
                    <div class="col-md-6 mb-3">
                        <div class="card h-100">
                            <div class="card-body">
                                <span class="badge bg-${this.getImpactColor(suggestion.impact)} mb-2">
                                    ${suggestion.category}
                                </span>
                                <h6 class="card-title">${suggestion.title}</h6>
                                <p class="card-text">${suggestion.description}</p>
                                <small class="text-muted">
                                    <i class="fas fa-seedling me-1"></i>
                                    Potential savings: ${suggestion.savings}
                                </small>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    updateChart(emissions) {
        if (!this.chartCanvas) return;
        
        const ctx = this.chartCanvas.getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.chart) {
            this.chart.destroy();
        }
        
        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Transport', 'Electricity', 'Diet', 'Waste'],
                datasets: [{
                    data: [
                        emissions.transport,
                        emissions.electricity,
                        emissions.diet,
                        emissions.waste
                    ],
                    backgroundColor: [
                        'rgba(25, 118, 210, 0.8)',
                        'rgba(255, 152, 0, 0.8)',
                        'rgba(46, 125, 50, 0.8)',
                        'rgba(97, 97, 97, 0.8)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value.toLocaleString()} kg (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    updateLiveEstimate() {
        // Update live estimate as user types
        const emissions = this.calculateEmissions();
        const estimateElement = document.getElementById('liveEstimate');
        
        if (estimateElement) {
            estimateElement.textContent = `${Math.round(emissions.total).toLocaleString()} kg CO₂e/year`;
            
            // Update estimate color based on emission level
            estimateElement.className = `badge bg-${emissions.emissionLevel.color}`;
        }
    }
    
    showLoading() {
        if (this.resultDiv) {
            this.resultDiv.innerHTML = `
                <div class="text-center py-4">
                    <div class="loading-spinner mx-auto mb-3"></div>
                    <p>Calculating your carbon footprint...</p>
                </div>
            `;
            this.resultDiv.style.display = 'block';
        }
    }
    
    async saveToServer(emissions) {
        try {
            const csrfToken = this.getCSRFToken();
            const response = await fetch('/api/carbon-footprints/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(emissions)
            });
            
            if (response.ok) {
                console.log('Carbon footprint saved to server');
            }
        } catch (error) {
            console.error('Error saving to server:', error);
        }
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    isUserLoggedIn() {
        // Check if user is logged in (simplified check)
        return document.body.classList.contains('logged-in');
    }
    
    getEmissionIcon(level) {
        switch(level) {
            case 'low': return 'leaf';
            case 'moderate': return 'exclamation-triangle';
            case 'high': return 'exclamation-circle';
            case 'very_high': return 'fire';
            default: return 'question-circle';
        }
    }
    
    getEmissionDescription(level) {
        switch(level) {
            case 'low': return 'Your carbon footprint is below average. Keep up the good work!';
            case 'moderate': return 'Your carbon footprint is about average. There are opportunities for improvement.';
            case 'high': return 'Your carbon footprint is above average. Consider making changes to reduce your impact.';
            case 'very_high': return 'Your carbon footprint is significantly above average. Immediate action is recommended.';
            default: return '';
        }
    }
    
    getImpactColor(impact) {
        switch(impact.toLowerCase()) {
            case 'high': return 'danger';
            case 'medium': return 'warning';
            case 'low': return 'success';
            default: return 'secondary';
        }
    }
}

// Initialize calculator when page loads
document.addEventListener('DOMContentLoaded', function() {
    const calculator = new CarbonCalculator();
    window.carbonCalculator = calculator;
});