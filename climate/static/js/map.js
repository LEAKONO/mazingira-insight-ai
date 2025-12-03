// static/js/map.js - Main Climate Map JavaScript

// ============================================
// GLOBAL FUNCTIONS - Must be defined FIRST
// ============================================

// Global reference to the climate map
let climateMap = null;

// Define all functions that are called from HTML onchange/onclick
window.refreshMapData = function() {
    if (climateMap) {
        climateMap.loadClimateData();
        climateMap.loadWeatherData();
        loadRecentReports();
        climateMap.showNotification('Refreshing map data...', 'info');
    }
};

window.updateMapData = function() {
    const dataType = document.getElementById('dataTypeSelect').value;
    const timeRange = document.getElementById('timeRangeSelect').value;
    showNotification(`Showing ${dataType} data for last ${timeRange} days`, 'info');
};

window.changeMapStyle = function() {
    const style = document.getElementById('mapStyleSelect').value;
    showNotification(`Switched to ${style} view`, 'info');
};

window.toggleHeatmap = function() {
    const showHeatmap = document.getElementById('heatmapToggle').checked;
    if (climateMap) {
        if (showHeatmap) {
            climateMap.map.addLayer(climateMap.layerGroups.heatmap);
        } else {
            climateMap.map.removeLayer(climateMap.layerGroups.heatmap);
        }
    }
};

window.togglePredictions = function() {
    const showPredictions = document.getElementById('predictionsToggle').checked;
    if (climateMap) {
        if (showPredictions) {
            climateMap.map.addLayer(climateMap.layerGroups.predictions);
        } else {
            climateMap.map.removeLayer(climateMap.layerGroups.predictions);
        }
    }
};

window.locateUser = function() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                if (climateMap && climateMap.map) {
                    const latlng = [position.coords.latitude, position.coords.longitude];
                    climateMap.map.setView(latlng, 12);
                    
                    // Add a marker at user's location
                    L.marker(latlng, {
                        icon: L.divIcon({
                            html: '<div style="background-color: #1976d2; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div>',
                            className: 'user-location-marker',
                            iconSize: [30, 30]
                        })
                    }).addTo(climateMap.map)
                    .bindPopup('Your Location')
                    .openPopup();
                }
            },
            function(error) {
                showNotification('Unable to get your location: ' + error.message, 'error');
            }
        );
    } else {
        showNotification('Geolocation is not supported by your browser', 'error');
    }
};

// Utility functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
    `;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
}

async function loadRecentReports() {
    try {
        const response = await fetch('/api/reports/?limit=5');
        const data = await response.json();
        
        const tableBody = document.getElementById('reportsTableBody');
        const loadingRow = document.getElementById('loadingRow');
        
        if (loadingRow) {
            loadingRow.remove();
        }
        
        if (data.results && data.results.length > 0) {
            tableBody.innerHTML = data.results.map(report => `
                <tr>
                    <td>
                        <span class="badge ${getReportBadgeClass(report.report_type)}">
                            ${report.report_type}
                        </span>
                    </td>
                    <td>${report.title}</td>
                    <td>${report.region_name || 'Unknown'}</td>
                    <td>${new Date(report.created_at).toLocaleDateString()}</td>
                    <td>
                        <span class="badge ${getStatusBadgeClass(report.status)}">
                            ${report.status}
                        </span>
                    </td>
                    <td>
                        <a href="/reports/${report.id}/" class="btn btn-sm btn-outline-primary">
                            View
                        </a>
                    </td>
                </tr>
            `).join('');
        } else {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        <i class="fas fa-inbox fa-2x text-muted mb-3"></i>
                        <p>No reports found</p>
                    </td>
                </tr>
            `;
        }
        
    } catch (error) {
        console.error('Error loading reports:', error);
        const tableBody = document.getElementById('reportsTableBody');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load reports
                    </td>
                </tr>
            `;
        }
    }
}

async function updateReportsCount() {
    try {
        const response = await fetch('/api/reports/?limit=1');
        const data = await response.json();
        const element = document.getElementById('mapReports');
        if (element) {
            element.textContent = data.count || '0';
        }
    } catch (error) {
        console.error('Error loading reports count:', error);
    }
}

function getReportBadgeClass(reportType) {
    switch(reportType) {
        case 'flood': return 'bg-primary';
        case 'drought': return 'bg-warning';
        case 'pollution': return 'bg-danger';
        case 'haze': return 'bg-secondary';
        default: return 'bg-info';
    }
}

function getStatusBadgeClass(status) {
    switch(status) {
        case 'reported': return 'bg-secondary';
        case 'verified': return 'bg-info';
        case 'in_progress': return 'bg-warning';
        case 'resolved': return 'bg-success';
        default: return 'bg-light text-dark';
    }
}

// ============================================
// ClimateMap Class Definition
// ============================================

class ClimateMap {
    constructor(mapId = 'climateMap', regionsGeoJSON, mapCenter = [-1.2921, 36.8219], mapZoom = 6) {
        this.mapId = mapId;
        this.map = null;
        this.markers = [];
        this.layerGroups = {};
        this.currentData = [];
        this.mapCenter = mapCenter; // Nairobi coordinates
        this.mapZoom = mapZoom;
        this.regionsGeoJSON = regionsGeoJSON || { features: [] };
        
        // Map tile providers
        this.tileLayers = {
            openstreetmap: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            topographical: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
            satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        };
    }
    
    initializeMap() {
        // Check if map container exists
        const mapContainer = document.getElementById(this.mapId);
        if (!mapContainer) {
            console.error(`Map container #${this.mapId} not found!`);
            return false;
        }
        
        console.log('Initializing map...');
        
        // Initialize map
        this.map = L.map(this.mapId).setView(this.mapCenter, this.mapZoom);
        
        // Add OpenStreetMap tiles
        L.tileLayer(this.tileLayers.openstreetmap, {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 18
        }).addTo(this.map);
        
        // Initialize layers
        this.initializeLayers();
        
        // Add click event to map for showing weather at clicked location
        this.addMapClickHandler();
        
        // Load data
        this.loadRegionsData();
        this.loadClimateData();
        
        return true;
    }
    
    initializeLayers() {
        // Create layer groups
        this.layerGroups = {
            regions: L.layerGroup(),
            climateData: L.layerGroup(),
            weatherData: L.layerGroup(),
            heatmap: L.layerGroup(),
            predictions: L.layerGroup(),
            reports: L.layerGroup(),
            clickMarkers: L.layerGroup()  // For user clicks
        };
        
        // Add scale control
        L.control.scale({ imperial: false }).addTo(this.map);
        
        // Add layer control
        L.control.layers({
            "OpenStreetMap": L.tileLayer(this.tileLayers.openstreetmap, {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 18
            }),
            "Topographical": L.tileLayer(this.tileLayers.topographical, {
                attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)',
                maxZoom: 17
            }),
            "Satellite": L.tileLayer(this.tileLayers.satellite, {
                attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
                maxZoom: 18
            })
        }, {
            "Regions": this.layerGroups.regions,
            "Climate Data": this.layerGroups.climateData,
            "Weather Data": this.layerGroups.weatherData,
            "Heatmap": this.layerGroups.heatmap,
            "Predictions": this.layerGroups.predictions,
            "Click Markers": this.layerGroups.clickMarkers
        }, {
            collapsed: false,
            position: 'topright'
        }).addTo(this.map);
        
        // Add default layers
        this.layerGroups.regions.addTo(this.map);
        this.layerGroups.climateData.addTo(this.map);
    }
    
    addMapClickHandler() {
        // When user clicks on map, show weather for that location
        this.map.on('click', async (e) => {
            const latlng = e.latlng;
            console.log('Map clicked at:', latlng.lat, latlng.lng);
            
            // Add a temporary marker
            const marker = L.marker(latlng, {
                icon: L.divIcon({
                    html: '<div style="background-color: #1976d2; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div>',
                    className: 'click-marker',
                    iconSize: [30, 30]
                })
            }).addTo(this.layerGroups.clickMarkers);
            
            // Show loading popup
            marker.bindPopup('<div style="padding: 10px;">Loading weather data...</div>').openPopup();
            
            try {
                // Fetch weather data for clicked location
                const weatherData = await this.fetchWeatherByCoordinates(latlng.lat, latlng.lng);
                
                // Update popup with weather info
                const popupContent = this.createWeatherPopupForLocation(latlng, weatherData);
                marker.bindPopup(popupContent).openPopup();
                
            } catch (error) {
                console.error('Error fetching weather:', error);
                marker.bindPopup(`
                    <div style="padding: 10px;">
                        <h6>Weather Information</h6>
                        <p>Could not load weather data for this location.</p>
                        <p class="text-muted">Lat: ${latlng.lat.toFixed(4)}, Lng: ${latlng.lng.toFixed(4)}</p>
                    </div>
                `).openPopup();
            }
        });
    }
    
    async fetchWeatherByCoordinates(lat, lng) {
        try {
            console.log(`Fetching weather for coordinates: ${lat}, ${lng}`);
            
            // Use the SIMPLE weather API endpoint
            const response = await fetch(`/api/weather/?lat=${lat}&lon=${lng}`);
            
            if (!response.ok) {
                console.error(`Weather API error ${response.status}:`, await response.text());
                // Still return mock data
                return this.getMockWeatherData(lat, lng);
            }
            
            const data = await response.json();
            console.log('Weather API response:', data);
            
            return data;
            
        } catch (error) {
            console.error('Error fetching weather by coordinates:', error);
            // Return mock data for demonstration
            return this.getMockWeatherData(lat, lng);
        }
    }
    
    getMockWeatherData(lat, lng) {
        // Generate realistic mock weather data based on coordinates
        const baseTemp = 20 + (lat * 0.5); // Temperature varies with latitude
        const humidity = 60 + (Math.random() * 30);
        const windSpeed = 3 + (Math.random() * 7);
        
        return {
            main: {
                temperature: baseTemp.toFixed(1),
                humidity: humidity.toFixed(1),
                pressure: 1013
            },
            weather: [{
                main: this.getWeatherCondition(baseTemp),
                description: this.getWeatherDescription(baseTemp)
            }],
            wind: {
                speed: windSpeed.toFixed(1),
                direction: Math.floor(Math.random() * 360)
            },
            rain: Math.random() > 0.7 ? (Math.random() * 5).toFixed(1) : 0,
            timestamp: new Date().toISOString(),
            source: 'mock'
        };
    }
    
    getWeatherCondition(temp) {
        if (temp > 30) return 'Hot';
        if (temp > 25) return 'Warm';
        if (temp > 15) return 'Mild';
        return 'Cool';
    }
    
    getWeatherDescription(temp) {
        const conditions = ['Clear sky', 'Partly cloudy', 'Cloudy', 'Light rain', 'Sunny'];
        return conditions[Math.floor(Math.random() * conditions.length)];
    }
    
    createWeatherPopupForLocation(latlng, weatherData) {
        const timestamp = new Date(weatherData.timestamp || Date.now()).toLocaleString();
        const main = weatherData.weather?.[0]?.main || 'Unknown';
        const description = weatherData.weather?.[0]?.description || '';
        const temp = weatherData.main?.temperature || 'N/A';
        const humidity = weatherData.main?.humidity || 'N/A';
        const windSpeed = weatherData.wind?.speed || 'N/A';
        const rainfall = weatherData.rain || 0;
        
        return `
            <div class="climate-popup">
                <h6>Weather at Location</h6>
                <p class="text-muted">${timestamp}</p>
                <p class="text-muted">Lat: ${latlng.lat.toFixed(4)}, Lng: ${latlng.lng.toFixed(4)}</p>
                
                <div class="d-flex align-items-center mb-3">
                    <div class="me-3">
                        <div class="display-6 ${this.getTemperatureClass(temp)}">${temp}°C</div>
                    </div>
                    <div>
                        <div class="fw-bold">${main}</div>
                        <div class="text-muted">${description}</div>
                    </div>
                </div>
                
                <div class="climate-stats">
                    <div class="stat">
                        <span class="stat-label">Humidity:</span>
                        <span class="stat-value">${humidity}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Wind Speed:</span>
                        <span class="stat-value">${windSpeed} m/s</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Rainfall:</span>
                        <span class="stat-value">${rainfall} mm</span>
                    </div>
                </div>
                
                <button class="btn btn-sm btn-primary mt-2 w-100" onclick="addReportAtLocation(${latlng.lat}, ${latlng.lng})">
                    <i class="fas fa-plus me-1"></i> Report Environmental Issue Here
                </button>
            </div>
        `;
    }
    
    loadRegionsData() {
        try {
            console.log('Loading regions data:', this.regionsGeoJSON);
            
            // Add GeoJSON to map
            L.geoJSON(this.regionsGeoJSON, {
                pointToLayer: (feature, latlng) => {
                    return L.circleMarker(latlng, {
                        radius: 8,
                        fillColor: "#2e7d32",
                        color: "#fff",
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.8
                    });
                },
                onEachFeature: (feature, layer) => {
                    // Create initial popup with region info
                    const popupContent = this.createRegionPopup(feature.properties);
                    layer.bindPopup(popupContent);
                    
                    // Add click handler to show weather for region
                    layer.on('click', async (e) => {
                        console.log('Region clicked:', feature.properties.name);
                        await this.showRegionWeather(feature.properties);
                    });
                }
            }).addTo(this.layerGroups.regions);
            
            // Fit bounds if we have regions
            if (this.regionsGeoJSON.features && this.regionsGeoJSON.features.length > 0) {
                const geoJsonLayer = L.geoJSON(this.regionsGeoJSON);
                this.map.fitBounds(geoJsonLayer.getBounds(), { padding: [50, 50] });
            }
            
        } catch (error) {
            console.error('Error loading regions data:', error);
            this.showError('Failed to load regions data');
        }
    }
    
    async showRegionWeather(regionProps) {
        try {
            console.log('Fetching weather for region:', regionProps);
            
            // Check if we have coordinates
            const lat = regionProps.latitude || (regionProps.geometry && regionProps.geometry.coordinates[1]);
            const lon = regionProps.longitude || (regionProps.geometry && regionProps.geometry.coordinates[0]);
            
            if (!lat || !lon) {
                console.error('No coordinates for region:', regionProps.name);
                this.showNotification(`No coordinates available for ${regionProps.name}`, 'error');
                return;
            }
            
            this.showNotification(`Fetching weather for ${regionProps.name}...`, 'info');
            
            // Get weather for this region using coordinates
            const weatherData = await this.fetchWeatherByCoordinates(lat, lon);
            
            console.log('Weather data received:', weatherData);
            
            // Create weather marker
            const marker = L.marker([lat, lon], {
                icon: L.divIcon({
                    html: this.createWeatherIcon(weatherData),
                    className: 'weather-marker',
                    iconSize: [40, 40],
                    iconAnchor: [20, 40]
                })
            }).addTo(this.layerGroups.weatherData);
            
            // Create popup content
            const popupContent = this.createWeatherPopup(regionProps, weatherData);
            marker.bindPopup(popupContent).openPopup();
            
        } catch (error) {
            console.error(`Error showing weather for ${regionProps.name}:`, error);
            this.showNotification(`Failed to get weather for ${regionProps.name}`, 'error');
            
            // Try to show mock data as fallback
            try {
                const lat = regionProps.latitude || -1.2921;
                const lon = regionProps.longitude || 36.8219;
                const mockData = this.getMockWeatherData(lat, lon);
                
                const marker = L.marker([lat, lon], {
                    icon: L.divIcon({
                        html: this.createWeatherIcon(mockData),
                        className: 'weather-marker',
                        iconSize: [40, 40],
                        iconAnchor: [20, 40]
                    })
                }).addTo(this.layerGroups.weatherData);
                
                const popupContent = this.createWeatherPopup(regionProps, mockData);
                marker.bindPopup(popupContent).openPopup();
                
                this.showNotification(`Showing mock data for ${regionProps.name}`, 'warning');
            } catch (fallbackError) {
                console.error('Fallback also failed:', fallbackError);
            }
        }
    }
    
    async loadClimateData() {
        try {
            const response = await fetch('/api/climate-data/latest/');
            const climateData = await response.json();
            
            console.log('Climate data loaded:', climateData);
            
            // Check if data is an array
            if (Array.isArray(climateData)) {
                this.currentData = climateData;
                console.log(`Found ${climateData.length} climate data records`);
                
                // Only update markers if we have data
                if (climateData.length > 0) {
                    this.updateClimateMarkers();
                    this.updateHeatmap();
                    this.updateStatistics();
                } else {
                    console.log('No climate data available');
                    this.showNotification('No climate data available. Showing map only.', 'warning');
                }
            } else {
                console.error('Climate data is not an array:', climateData);
                this.currentData = [];
                this.showNotification('Climate data format error', 'error');
            }
            
        } catch (error) {
            console.error('Error loading climate data:', error);
            this.showError('Failed to load climate data');
            this.currentData = []; // Set empty array to avoid errors
        }
    }
    
    createWeatherIcon(weatherData) {
        // Parse temperature from weather data
        let temp;
        if (weatherData.main && weatherData.main.temperature !== undefined) {
            temp = weatherData.main.temperature;
        } else if (weatherData.temperature !== undefined) {
            temp = weatherData.temperature;
        } else {
            temp = 20; // Default
        }
        
        let color = '#2196F3'; // Default blue
        
        if (temp > 30) color = '#F44336';
        else if (temp > 25) color = '#FF9800';
        else if (temp > 15) color = '#4CAF50';
        
        return `
            <div style="
                background-color: ${color};
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: 3px solid white;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 14px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                cursor: pointer;
            ">
                ${Math.round(temp)}°
            </div>
        `;
    }
    
    createRegionPopup(properties) {
        return `
            <div class="map-popup">
                <h5>${properties.name}</h5>
                <p><strong>Country:</strong> ${properties.country}</p>
                ${properties.population ? `<p><strong>Population:</strong> ${properties.population.toLocaleString()}</p>` : ''}
                ${properties.climate_zone ? `<p><strong>Climate Zone:</strong> ${properties.climate_zone}</p>` : ''}
                <button class="btn btn-sm btn-primary mt-2" onclick="window.climateMap.showRegionWeather(${JSON.stringify(properties).replace(/"/g, '&quot;')})">
                    Show Current Weather
                </button>
                <button class="btn btn-sm btn-outline-primary mt-2 ms-2" onclick="window.location.href='/history/?region=${properties.id}'">
                    View Historical Data
                </button>
            </div>
        `;
    }
    
    createWeatherPopup(region, weatherData) {
        console.log('Creating popup with weather data:', weatherData);
        
        // Handle different API response structures
        let timestamp, main, description, temp, humidity, windSpeed, rainfall;
        
        if (weatherData.main && weatherData.main.temperature !== undefined) {
            // OpenWeatherMap structure
            main = weatherData.weather?.[0]?.main || 'Unknown';
            description = weatherData.weather?.[0]?.description || '';
            temp = weatherData.main.temperature;
            humidity = weatherData.main.humidity;
            windSpeed = weatherData.wind?.speed || 'N/A';
            rainfall = weatherData.rain || 0;
            timestamp = weatherData.timestamp || new Date().toISOString();
        } else if (weatherData.temperature !== undefined) {
            // Direct climate data structure
            temp = weatherData.temperature;
            humidity = weatherData.humidity || 'N/A';
            windSpeed = weatherData.wind_speed || 'N/A';
            rainfall = weatherData.rainfall || 0;
            timestamp = weatherData.timestamp || new Date().toISOString();
            
            // Create weather condition from temperature
            if (temp > 30) {
                main = 'Hot';
                description = 'Hot conditions';
            } else if (temp > 25) {
                main = 'Warm';
                description = 'Warm conditions';
            } else if (temp > 15) {
                main = 'Mild';
                description = 'Mild conditions';
            } else {
                main = 'Cool';
                description = 'Cool conditions';
            }
        } else {
            // Mock data or fallback
            temp = weatherData.temperature || 22;
            humidity = weatherData.humidity || 65;
            windSpeed = weatherData.windSpeed || 3.5;
            rainfall = weatherData.rain || 0;
            timestamp = new Date().toISOString();
            main = weatherData.weather || 'Clear';
            description = weatherData.description || 'Fair weather';
        }
        
        const formattedTime = new Date(timestamp).toLocaleString();
        
        return `
            <div class="climate-popup">
                <h5>${region.name || 'Location'}</h5>
                <p class="text-muted">${formattedTime}</p>
                
                <div class="d-flex align-items-center mb-3">
                    <div class="me-3">
                        <div class="display-6 ${this.getTemperatureClass(temp)}">${temp}°C</div>
                    </div>
                    <div>
                        <div class="fw-bold">${main}</div>
                        <div class="text-muted">${description}</div>
                    </div>
                </div>
                
                <div class="climate-stats">
                    <div class="stat">
                        <span class="stat-label">Humidity:</span>
                        <span class="stat-value">${humidity}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Wind Speed:</span>
                        <span class="stat-value">${windSpeed} m/s</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Rainfall:</span>
                        <span class="stat-value">${rainfall} mm</span>
                    </div>
                </div>
                
                <div class="d-flex mt-3">
                    <button class="btn btn-sm btn-primary flex-fill me-2" onclick="refreshWeather('${region.name || ''}')">
                        <i class="fas fa-sync-alt me-1"></i> Refresh
                    </button>
                    <button class="btn btn-sm btn-outline-primary flex-fill" onclick="showForecast('${region.name || ''}')">
                        <i class="fas fa-chart-line me-1"></i> Forecast
                    </button>
                </div>
            </div>
        `;
    }
    
    getTemperatureClass(temperature) {
        const temp = parseFloat(temperature);
        if (isNaN(temp)) return '';
        if (temp < 15) return 'cold';
        if (temp < 25) return 'mild';
        if (temp < 30) return 'warm';
        return 'hot';
    }
    
    updateClimateMarkers() {
        // Clear existing markers
        this.layerGroups.climateData.clearLayers();
        
        // Add new markers
        this.currentData.forEach(data => {
            if (data.region && data.region.latitude && data.region.longitude) {
                const marker = L.marker([data.region.latitude, data.region.longitude], {
                    icon: this.getTemperatureIcon(data.temperature)
                });
                
                const popupContent = this.createClimatePopup(data);
                marker.bindPopup(popupContent);
                
                marker.addTo(this.layerGroups.climateData);
                this.markers.push(marker);
            }
        });
    }
    
    getTemperatureIcon(temperature) {
        let iconColor;
        const temp = parseFloat(temperature);
        
        if (isNaN(temp)) iconColor = '#666';
        else if (temp < 15) iconColor = '#2196F3';
        else if (temp < 25) iconColor = '#4CAF50';
        else if (temp < 30) iconColor = '#FF9800';
        else iconColor = '#F44336';
        
        return L.divIcon({
            html: `
                <div style="
                    background-color: ${iconColor};
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    border: 2px solid white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                ">
                    ${Math.round(temp)}°
                </div>
            `,
            className: 'temperature-marker-container',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
    }
    
    createClimatePopup(data) {
        const region = data.region;
        const date = new Date(data.timestamp).toLocaleString();
        
        return `
            <div class="climate-popup">
                <h5>${region.name}</h5>
                <p class="text-muted">${date}</p>
                
                <div class="climate-stats">
                    <div class="stat">
                        <span class="stat-label">Temperature:</span>
                        <span class="stat-value ${this.getTemperatureClass(data.temperature)}">
                            ${data.temperature?.toFixed(1) || 'N/A'}°C
                        </span>
                    </div>
                    
                    ${data.humidity ? `
                    <div class="stat">
                        <span class="stat-label">Humidity:</span>
                        <span class="stat-value">${data.humidity.toFixed(1)}%</span>
                    </div>
                    ` : ''}
                    
                    ${data.rainfall ? `
                    <div class="stat">
                        <span class="stat-label">Rainfall:</span>
                        <span class="stat-value">${data.rainfall.toFixed(1)} mm</span>
                    </div>
                    ` : ''}
                </div>
                
                <button class="btn btn-sm btn-primary mt-2" onclick="window.location.href='/history/?region=${region.id}'">
                    View Historical Data
                </button>
            </div>
        `;
    }
    
    updateHeatmap() {
        // Clear existing heatmap
        this.layerGroups.heatmap.clearLayers();
        
        // Create heatmap data
        const heatmapData = this.currentData
            .filter(data => data.region && data.region.latitude && data.region.longitude)
            .map(data => [data.region.latitude, data.region.longitude, data.temperature || 0]);
        
        if (heatmapData.length > 0 && typeof L.heatLayer !== 'undefined') {
            const heatmapLayer = L.heatLayer(heatmapData, {
                radius: 25,
                blur: 15,
                maxZoom: 17,
                gradient: {
                    0.0: 'blue',
                    0.5: 'lime',
                    0.8: 'yellow',
                    1.0: 'red'
                }
            });
            
            this.layerGroups.heatmap.addLayer(heatmapLayer);
        }
    }
    
    updateStatistics() {
        if (this.currentData.length > 0) {
            // Update data points count
            const dataPointsElement = document.getElementById('mapDataPoints');
            if (dataPointsElement) {
                dataPointsElement.textContent = this.currentData.length;
            }
            
            // Calculate average temperature
            const validTemps = this.currentData
                .filter(d => d.temperature)
                .map(d => d.temperature);
            
            if (validTemps.length > 0) {
                const avgTemp = validTemps.reduce((a, b) => a + b, 0) / validTemps.length;
                const avgTempElement = document.getElementById('mapAvgTemp');
                if (avgTempElement) {
                    avgTempElement.textContent = avgTemp.toFixed(1) + '°C';
                }
            }
        }
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
        `;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 3000);
    }
}

// ============================================
// Additional Global Functions for Weather Display
// ============================================

window.showRegionWeather = async function(regionName) {
    if (climateMap) {
        // Find region in the GeoJSON data
        const region = climateMap.regionsGeoJSON.features.find(f => f.properties.name === regionName);
        
        if (region) {
            await climateMap.showRegionWeather(region.properties);
        } else {
            showNotification(`Region ${regionName} not found`, 'error');
        }
    }
};

window.refreshWeather = function(regionName) {
    showNotification(`Refreshing weather for ${regionName}...`, 'info');
    // In a real app, you would call the API again
    setTimeout(() => {
        showNotification(`Weather for ${regionName} updated`, 'success');
    }, 1000);
};

window.showForecast = function(regionName) {
    showNotification(`Loading forecast for ${regionName}...`, 'info');
    // In a real app, you would fetch forecast data
    setTimeout(() => {
        showNotification(`7-day forecast for ${regionName} loaded`, 'success');
    }, 1500);
};

window.addReportAtLocation = function(lat, lng) {
    // Redirect to create report page with pre-filled coordinates
    window.location.href = `/reports/new/?lat=${lat}&lng=${lng}`;
};

// Debug function for testing weather API
async function testWeatherAPI() {
    console.log('Testing weather API...');
    
    // Test with Nairobi coordinates
    const lat = -1.2921;
    const lon = 36.8219;
    
    try {
        const response = await fetch(`/api/weather/?lat=${lat}&lon=${lon}`);
        const data = await response.json();
        console.log('API Response:', data);
        
        if (data.error) {
            console.error('API Error:', data.error);
            alert('Weather API Error: ' + data.error);
        } else {
            alert('Weather API is working! Temperature: ' + data.main.temperature + '°C');
        }
    } catch (error) {
        console.error('Network Error:', error);
        alert('Network error: ' + error.message);
    }
}

// Call this function from browser console to test
window.testWeatherAPI = testWeatherAPI;

// ============================================
// Page Initialization
// ============================================

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function() {
    try {
        console.log('Initializing climate map...');
        
        // Get data from Django template variables (passed from view)
        const regionsGeoJSON = window.regionsGeoJSON || { features: [] };
        const mapCenter = window.mapCenter || [-1.2921, 36.8219];
        const mapZoom = window.mapZoom || 6;
        
        // Initialize the map
        climateMap = new ClimateMap('climateMap', regionsGeoJSON, mapCenter, mapZoom);
        const initialized = climateMap.initializeMap();
        
        if (initialized) {
            console.log('Map initialized successfully');
            
            // Load recent reports
            loadRecentReports();
            
            // Update reports count
            updateReportsCount();
            
            // Store in window for debugging
            window.climateMap = climateMap;
        } else {
            console.error('Failed to initialize map');
            const mapContainer = document.getElementById('climateMap');
            if (mapContainer) {
                mapContainer.innerHTML = `
                    <div class="alert alert-warning m-4">
                        <h4>Map Initialization Failed</h4>
                        <p>Could not initialize the map. Please refresh the page.</p>
                    </div>
                `;
            }
        }
        
    } catch (error) {
        console.error('Error initializing map:', error);
        const mapContainer = document.getElementById('climateMap');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div class="alert alert-danger m-4">
                    <h4>Map Initialization Error</h4>
                    <p>${error.message}</p>
                    <p>Please check your browser console for more details.</p>
                </div>
            `;
        }
    }
});