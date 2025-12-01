/*
 * Leaflet Map Integration for Climate Data Visualization
 */

class ClimateMap {
    constructor(mapId = 'climateMap') {
        this.mapId = mapId;
        this.map = null;
        this.markers = [];
        this.layerGroups = {};
        this.currentData = [];
        this.mapCenter = [-1.2921, 36.8219]; // Nairobi coordinates
        this.mapZoom = 6;
        
        // Map tile providers
        this.tileLayers = {
            openstreetmap: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            topographical: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
            satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        };
        
        this.initializeMap();
    }
    
    initializeMap() {
        // Initialize map
        this.map = L.map(this.mapId).setView(this.mapCenter, this.mapZoom);
        
        // Add OpenStreetMap tiles
        L.tileLayer(this.tileLayers.openstreetmap, {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 18
        }).addTo(this.map);
        
        // Add layer controls
        this.initializeLayerControls();
        
        // Add scale control
        L.control.scale({ imperial: false }).addTo(this.map);
        
        // Add search control
        this.initializeSearch();
        
        // Load initial data
        this.loadRegionsData();
        this.loadClimateData();
        
        // Set up auto-refresh
        this.setupAutoRefresh();
        
        // Add event listeners
        this.addMapEventListeners();
    }
    
    initializeLayerControls() {
        // Create base layers
        const baseLayers = {
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
        };
        
        // Create overlay layers
        this.layerGroups = {
            regions: L.layerGroup(),
            climateData: L.layerGroup(),
            heatmap: L.layerGroup(),
            predictions: L.layerGroup()
        };
        
        const overlays = {
            "Regions": this.layerGroups.regions,
            "Climate Data": this.layerGroups.climateData,
            "Heatmap": this.layerGroups.heatmap,
            "Predictions": this.layerGroups.predictions
        };
        
        // Add layer control to map
        L.control.layers(baseLayers, overlays, {
            collapsed: false,
            position: 'topright'
        }).addTo(this.map);
        
        // Add base layers to map
        baseLayers["OpenStreetMap"].addTo(this.map);
        
        // Add default overlay
        this.layerGroups.regions.addTo(this.map);
        this.layerGroups.climateData.addTo(this.map);
    }
    
    initializeSearch() {
        // Add search control
        const searchControl = new L.Control.Search({
            layer: this.layerGroups.regions,
            propertyName: 'name',
            marker: false,
            moveToLocation: function(latlng, title, map) {
                map.setView(latlng, 12);
            }
        });
        
        searchControl.on('search:locationfound', function(e) {
            e.layer.openPopup();
        });
        
        this.map.addControl(searchControl);
    }
    
    async loadRegionsData() {
        try {
            const response = await fetch('/api/regions/geojson/');
            const geojson = await response.json();
            
            // Add GeoJSON to map
            L.geoJSON(geojson, {
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
                    // Add popup with region info
                    const popupContent = `
                        <div class="map-popup">
                            <h5>${feature.properties.name}</h5>
                            <p><strong>Country:</strong> ${feature.properties.country}</p>
                            <p><strong>Population:</strong> ${feature.properties.population?.toLocaleString() || 'N/A'}</p>
                            <p><strong>Climate Zone:</strong> ${feature.properties.climate_zone || 'N/A'}</p>
                            <button class="btn btn-sm btn-primary mt-2 view-region-btn" 
                                    data-region-id="${feature.properties.id}">
                                View Details
                            </button>
                        </div>
                    `;
                    
                    layer.bindPopup(popupContent);
                    
                    // Store properties on layer for search
                    layer.feature = feature;
                    layer.properties = feature.properties;
                    layer.name = feature.properties.name;
                    
                    // Add click handler for details
                    layer.on('click', () => {
                        this.showRegionDetails(feature.properties.id);
                    });
                }
            }).addTo(this.layerGroups.regions);
            
            // Fit bounds to show all regions
            const bounds = L.geoJSON(geojson).getBounds();
            this.map.fitBounds(bounds, { padding: [50, 50] });
            
        } catch (error) {
            console.error('Error loading regions data:', error);
            this.showError('Failed to load regions data');
        }
    }
    
    async loadClimateData() {
        try {
            const response = await fetch('/api/climate-data/latest/');
            const climateData = await response.json();
            
            this.currentData = climateData;
            this.updateClimateMarkers();
            this.updateHeatmap();
            
        } catch (error) {
            console.error('Error loading climate data:', error);
        }
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
                
                // Store reference
                this.markers.push(marker);
            }
        });
    }
    
    getTemperatureIcon(temperature) {
        // Create custom icon based on temperature
        let iconColor;
        
        if (temperature < 15) {
            iconColor = '#2196F3'; // Blue for cold
        } else if (temperature < 25) {
            iconColor = '#4CAF50'; // Green for mild
        } else if (temperature < 30) {
            iconColor = '#FF9800'; // Orange for warm
        } else {
            iconColor = '#F44336'; // Red for hot
        }
        
        return L.divIcon({
            html: `
                <div class="temperature-marker" style="
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
                    ${Math.round(temperature)}°
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
                            ${data.temperature.toFixed(1)}°C
                        </span>
                    </div>
                    
                    <div class="stat">
                        <span class="stat-label">Humidity:</span>
                        <span class="stat-value">${data.humidity?.toFixed(1) || 'N/A'}%</span>
                    </div>
                    
                    <div class="stat">
                        <span class="stat-label">Rainfall:</span>
                        <span class="stat-value">${data.rainfall?.toFixed(1) || 'N/A'} mm</span>
                    </div>
                    
                    ${data.air_quality_index ? `
                    <div class="stat">
                        <span class="stat-label">Air Quality:</span>
                        <span class="stat-value ${this.getAQIClass(data.air_quality_index)}">
                            ${data.air_quality_index.toFixed(1)} AQI
                        </span>
                    </div>
                    ` : ''}
                </div>
                
                <button class="btn btn-sm btn-primary mt-2 view-details-btn" 
                        data-data-id="${data.id}">
                    View Historical Data
                </button>
            </div>
        `;
    }
    
    getTemperatureClass(temperature) {
        if (temperature < 15) return 'cold';
        if (temperature < 25) return 'mild';
        if (temperature < 30) return 'warm';
        return 'hot';
    }
    
    getAQIClass(aqi) {
        if (aqi <= 50) return 'good';
        if (aqi <= 100) return 'moderate';
        if (aqi <= 150) return 'unhealthy-sensitive';
        if (aqi <= 200) return 'unhealthy';
        if (aqi <= 300) return 'very-unhealthy';
        return 'hazardous';
    }
    
    updateHeatmap() {
        // Clear existing heatmap
        this.layerGroups.heatmap.clearLayers();
        
        // Create heatmap data
        const heatmapData = this.currentData
            .filter(data => data.region && data.region.latitude && data.region.longitude)
            .map(data => [data.region.latitude, data.region.longitude, data.temperature || 0]);
        
        if (heatmapData.length > 0) {
            // Create heatmap layer
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
    
    async showRegionDetails(regionId) {
        try {
            // Fetch region details
            const response = await fetch(`/api/regions/${regionId}/`);
            const region = await response.json();
            
            // Show details in modal or sidebar
            this.displayRegionDetails(region);
            
        } catch (error) {
            console.error('Error loading region details:', error);
            this.showError('Failed to load region details');
        }
    }
    
    displayRegionDetails(region) {
        // Create or update details panel
        let detailsPanel = document.getElementById('regionDetailsPanel');
        
        if (!detailsPanel) {
            detailsPanel = this.createDetailsPanel();
        }
        
        // Update panel content
        detailsPanel.innerHTML = `
            <div class="region-details">
                <button class="btn btn-sm btn-close close-panel-btn" 
                        style="float: right; margin-bottom: 10px;">
                </button>
                
                <h4>${region.name}</h4>
                <p class="text-muted">${region.country}</p>
                
                <div class="region-stats">
                    ${region.population ? `
                    <div class="stat">
                        <i class="fas fa-users"></i>
                        <span>Population:</span>
                        <strong>${region.population.toLocaleString()}</strong>
                    </div>
                    ` : ''}
                    
                    ${region.area_sq_km ? `
                    <div class="stat">
                        <i class="fas fa-mountain"></i>
                        <span>Area:</span>
                        <strong>${region.area_sq_km.toLocaleString()} km²</strong>
                    </div>
                    ` : ''}
                    
                    ${region.elevation ? `
                    <div class="stat">
                        <i class="fas fa-mountain"></i>
                        <span>Elevation:</span>
                        <strong>${region.elevation.toLocaleString()} m</strong>
                    </div>
                    ` : ''}
                    
                    ${region.climate_zone ? `
                    <div class="stat">
                        <i class="fas fa-cloud-sun"></i>
                        <span>Climate Zone:</span>
                        <strong>${region.climate_zone}</strong>
                    </div>
                    ` : ''}
                </div>
                
                ${region.latest_data ? `
                <div class="current-weather mt-3">
                    <h5>Current Weather</h5>
                    <div class="weather-info">
                        <div class="temperature">
                            <i class="fas fa-thermometer-half"></i>
                            ${region.latest_data.temperature.toFixed(1)}°C
                        </div>
                        <div class="humidity">
                            <i class="fas fa-tint"></i>
                            ${region.latest_data.humidity.toFixed(1)}% humidity
                        </div>
                    </div>
                </div>
                ` : ''}
                
                <div class="mt-3">
                    <button class="btn btn-primary btn-sm view-history-btn" 
                            data-region-id="${region.id}">
                        View Historical Data
                    </button>
                    <button class="btn btn-outline-primary btn-sm ms-2 predict-btn" 
                            data-region-id="${region.id}">
                        Get Predictions
                    </button>
                </div>
            </div>
        `;
        
        // Show panel
        detailsPanel.style.display = 'block';
        
        // Add event listeners
        this.addDetailsPanelListeners();
    }
    
    createDetailsPanel() {
        const panel = document.createElement('div');
        panel.id = 'regionDetailsPanel';
        panel.className = 'region-details-panel';
        panel.style.cssText = `
            position: absolute;
            top: 20px;
            right: 20px;
            width: 300px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            display: none;
        `;
        
        document.getElementById(this.mapId).parentElement.appendChild(panel);
        return panel;
    }
    
    addDetailsPanelListeners() {
        // Close button
        const closeBtn = document.querySelector('.close-panel-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                document.getElementById('regionDetailsPanel').style.display = 'none';
            });
        }
        
        // View history button
        const historyBtn = document.querySelector('.view-history-btn');
        if (historyBtn) {
            historyBtn.addEventListener('click', (e) => {
                const regionId = e.target.dataset.regionId;
                window.location.href = `/history/?region=${regionId}`;
            });
        }
        
        // Predict button
        const predictBtn = document.querySelector('.predict-btn');
        if (predictBtn) {
            predictBtn.addEventListener('click', async (e) => {
                const regionId = e.target.dataset.regionId;
                await this.getPredictions(regionId);
            });
        }
    }
    
    async getPredictions(regionId) {
        try {
            const response = await fetch(`/api/predict-temperature/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    region_id: parseInt(regionId),
                    days_ahead: 7,
                    include_confidence: true
                })
            });
            
            const result = await response.json();
            
            if (result.predictions) {
                this.displayPredictions(result.predictions);
            }
            
        } catch (error) {
            console.error('Error getting predictions:', error);
            this.showError('Failed to get predictions');
        }
    }
    
    displayPredictions(predictions) {
        // Clear existing prediction markers
        this.layerGroups.predictions.clearLayers();
        
        // Add prediction markers
        predictions.forEach(prediction => {
            // This is simplified - in reality, you'd have coordinates for each prediction
            const marker = L.marker([this.mapCenter[0], this.mapCenter[1]], {
                icon: L.divIcon({
                    html: `
                        <div class="prediction-marker">
                            <span>${prediction.predicted_temperature.toFixed(1)}°C</span>
                        </div>
                    `,
                    className: 'prediction-marker',
                    iconSize: [40, 40]
                })
            });
            
            marker.addTo(this.layerGroups.predictions);
        });
        
        // Show predictions layer
        this.map.addLayer(this.layerGroups.predictions);
    }
    
    addMapEventListeners() {
        // Update data when map moves
        this.map.on('moveend', () => {
            this.loadClimateData();
        });
        
        // Handle clicks on map
        this.map.on('click', (e) => {
            this.handleMapClick(e);
        });
    }
    
    handleMapClick(e) {
        // Show coordinates
        const popup = L.popup()
            .setLatLng(e.latlng)
            .setContent(`
                <div class="coordinates-popup">
                    <p>Latitude: ${e.latlng.lat.toFixed(4)}</p>
                    <p>Longitude: ${e.latlng.lng.toFixed(4)}</p>
                    <button class="btn btn-sm btn-primary mt-1 add-report-btn"
                            data-lat="${e.latlng.lat}"
                            data-lng="${e.latlng.lng}">
                        Report Environmental Issue
                    </button>
                </div>
            `)
            .openOn(this.map);
        
        // Add event listener to report button
        setTimeout(() => {
            const reportBtn = document.querySelector('.add-report-btn');
            if (reportBtn) {
                reportBtn.addEventListener('click', () => {
                    this.openReportForm(e.latlng.lat, e.latlng.lng);
                });
            }
        }, 100);
    }
    
    openReportForm(lat, lng) {
        // Redirect to report form with coordinates
        window.location.href = `/reports/new/?lat=${lat}&lng=${lng}`;
    }
    
    setupAutoRefresh() {
        // Refresh data every 5 minutes
        setInterval(() => {
            this.loadClimateData();
        }, 5 * 60 * 1000);
    }
    
    showError(message) {
        // Show error notification
        L.popup()
            .setLatLng(this.map.getCenter())
            .setContent(`
                <div class="error-popup">
                    <i class="fas fa-exclamation-triangle text-danger"></i>
                    <p>${message}</p>
                </div>
            `)
            .openOn(this.map);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function() {
    const climateMap = new ClimateMap();
    window.climateMap = climateMap;
});