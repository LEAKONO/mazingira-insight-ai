"""
Database models for the climate monitoring application.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import calendar


class Region(models.Model):
    """
    Represents a geographical region for climate monitoring.
    """
    name = models.CharField(max_length=200, help_text="Region name (e.g., Nairobi, Mombasa)")
    country = models.CharField(max_length=100, default="Kenya")
    
    # Geographic coordinates - using separate fields instead of PointField
    latitude = models.FloatField(blank=True, null=True, help_text="Latitude in decimal degrees")
    longitude = models.FloatField(blank=True, null=True, help_text="Longitude in decimal degrees")
    
    # Alternative: JSONField for complex location data
    location_data = models.JSONField(blank=True, null=True, help_text="Additional location data")
    
    population = models.IntegerField(blank=True, null=True, help_text="Population count")
    area_sq_km = models.FloatField(blank=True, null=True, help_text="Area in square kilometers")
    
    # Climate characteristics
    climate_zone = models.CharField(max_length=100, blank=True, null=True)
    elevation = models.FloatField(blank=True, null=True, help_text="Elevation in meters")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['country']),
        ]
    
    def __str__(self):
        return f"{self.name}, {self.country}"
    
    def get_coordinates(self):
        """Return latitude and longitude as tuple."""
        return (self.latitude, self.longitude)
    
    def to_geojson(self):
        """Convert region to GeoJSON feature."""
        lat, lon = self.get_coordinates()
        return {
            "type": "Feature",
            "properties": {
                "id": self.id,
                "name": self.name,
                "country": self.country,
                "population": self.population,
                "climate_zone": self.climate_zone
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat] if lon and lat else [0, 0]
            }
        }


class ClimateData(models.Model):
    """
    Stores climate measurements for specific regions and timestamps.
    """
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='climate_data')
    timestamp = models.DateTimeField(help_text="Time of measurement")
    
    # Core measurements
    temperature = models.FloatField(help_text="Temperature in Celsius")
    humidity = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Relative humidity percentage"
    )
    rainfall = models.FloatField(
        default=0,
        help_text="Rainfall in mm (cumulative since last reading)"
    )
    air_quality_index = models.FloatField(
        blank=True, null=True,
        help_text="Air Quality Index (0-500)"
    )
    wind_speed = models.FloatField(default=0, help_text="Wind speed in m/s")
    wind_direction = models.FloatField(
        blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        help_text="Wind direction in degrees"
    )
    pressure = models.FloatField(blank=True, null=True, help_text="Atmospheric pressure in hPa")
    
    # Additional data
    uv_index = models.FloatField(blank=True, null=True, help_text="UV Index")
    visibility = models.FloatField(blank=True, null=True, help_text="Visibility in meters")
    
    # Source information
    source = models.CharField(
        max_length=50,
        choices=[
            ('api', 'Weather API'),
            ('sensor', 'Local Sensor'),
            ('manual', 'Manual Entry'),
            ('predicted', 'ML Prediction')
        ],
        default='api'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Climate Data"
        indexes = [
            models.Index(fields=['region', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['temperature']),
        ]
        unique_together = ['region', 'timestamp']
    
    def __str__(self):
        return f"{self.region.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def get_weather_summary(self):
        """Return a human-readable weather summary."""
        if self.temperature > 30:
            temp_desc = "Hot"
        elif self.temperature > 20:
            temp_desc = "Warm"
        elif self.temperature > 10:
            temp_desc = "Cool"
        else:
            temp_desc = "Cold"
        
        if self.rainfall > 10:
            rain_desc = "Heavy rain"
        elif self.rainfall > 1:
            rain_desc = "Light rain"
        else:
            rain_desc = "Dry"
        
        return f"{temp_desc}, {rain_desc}"


class CarbonFootprint(models.Model):
    """
    Stores carbon footprint calculations for users.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carbon_footprints')
    calculation_date = models.DateTimeField(auto_now_add=True)
    
    # Input data
    transport_km = models.FloatField(
        default=0,
        help_text="Weekly transport distance in km"
    )
    electricity_kwh = models.FloatField(
        default=0,
        help_text="Monthly electricity consumption in kWh"
    )
    diet_type = models.CharField(
        max_length=20,
        choices=[
            ('vegetarian', 'Vegetarian'),
            ('meat_light', 'Meat 1-2 times/week'),
            ('meat_medium', 'Meat 3-5 times/week'),
            ('meat_heavy', 'Meat daily'),
        ],
        default='meat_medium'
    )
    waste_kg = models.FloatField(
        default=0,
        help_text="Weekly waste in kg"
    )
    
    # Calculated results
    total_co2e = models.FloatField(help_text="Total CO2 equivalent in kg/year")
    
    # Breakdown
    transport_co2e = models.FloatField(help_text="Transport CO2e in kg/year")
    electricity_co2e = models.FloatField(help_text="Electricity CO2e in kg/year")
    diet_co2e = models.FloatField(help_text="Diet CO2e in kg/year")
    waste_co2e = models.FloatField(help_text="Waste CO2e in kg/year")
    
    # Suggestions
    suggestions = models.JSONField(
        blank=True, null=True,
        help_text="Personalized reduction suggestions"
    )
    
    class Meta:
        ordering = ['-calculation_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.calculation_date.strftime('%Y-%m-%d')} - {self.total_co2e:.1f} kg CO2e"
    
    def get_emission_level(self):
        """Return emission level category."""
        if self.total_co2e < 2000:
            return "Low"
        elif self.total_co2e < 5000:
            return "Moderate"
        elif self.total_co2e < 10000:
            return "High"
        else:
            return "Very High"


class EnvironmentalReport(models.Model):
    """
    Allows users to report environmental events or issues.
    """
    REPORT_TYPES = [
        ('flood', 'Flood'),
        ('drought', 'Drought'),
        ('haze', 'Haze/Smog'),
        ('deforestation', 'Deforestation'),
        ('pollution', 'Pollution'),
        ('wildfire', 'Wildfire'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Location details
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Media (optional)
    photo = models.ImageField(upload_to='reports/', blank=True, null=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('reported', 'Reported'),
            ('verified', 'Verified'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
        ],
        default='reported'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_type} - {self.title} ({self.region.name})"


class Prediction(models.Model):
    """
    Stores ML model predictions for climate trends.
    """
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    prediction_date = models.DateTimeField()
    
    # Predicted values
    predicted_temperature = models.FloatField()
    predicted_rainfall = models.FloatField()
    
    # Confidence intervals
    temperature_lower = models.FloatField(blank=True, null=True)
    temperature_upper = models.FloatField(blank=True, null=True)
    rainfall_lower = models.FloatField(blank=True, null=True)
    rainfall_upper = models.FloatField(blank=True, null=True)
    
    # Model info
    model_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-prediction_date']
        unique_together = ['region', 'prediction_date']
    
    def __str__(self):
        return f"{self.region.name} - {self.prediction_date.strftime('%Y-%m-%d')}"


class MonthlyClimate(models.Model):
    """
    Monthly aggregated climate data for better trend analysis.
    """
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='monthly_data')
    year = models.IntegerField()
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])  # 1-12
    
    # Aggregated values
    avg_temperature = models.FloatField(help_text="Average temperature in Celsius")
    max_temperature = models.FloatField(help_text="Maximum temperature in Celsius")
    min_temperature = models.FloatField(help_text="Minimum temperature in Celsius")
    total_rainfall = models.FloatField(help_text="Total rainfall in mm")
    avg_humidity = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Average relative humidity percentage"
    )
    avg_wind_speed = models.FloatField(help_text="Average wind speed in m/s")
    
    # Prediction for next period
    predicted_temperature = models.FloatField(
        null=True, blank=True,
        help_text="Predicted average temperature for this month"
    )
    predicted_rainfall = models.FloatField(
        null=True, blank=True,
        help_text="Predicted total rainfall for this month"
    )
    prediction_confidence = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Prediction confidence percentage (0-100%)"
    )
    
    # Additional calculated fields
    temperature_anomaly = models.FloatField(
        null=True, blank=True,
        help_text="Temperature anomaly from historical average"
    )
    rainfall_anomaly = models.FloatField(
        null=True, blank=True,
        help_text="Rainfall anomaly from historical average"
    )
    
    # Source and metadata
    data_source = models.CharField(
        max_length=50,
        choices=[
            ('aggregated', 'Aggregated from ClimateData'),
            ('api', 'Monthly API Data'),
            ('predicted', 'ML Prediction'),
            ('manual', 'Manual Entry'),
        ],
        default='aggregated'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['region', 'year', 'month']
        verbose_name_plural = "Monthly Climate Data"
        indexes = [
            models.Index(fields=['region', 'year', 'month']),
            models.Index(fields=['year', 'month']),
            models.Index(fields=['avg_temperature']),
        ]
    
    def __str__(self):
        return f"{self.region.name} - {self.year}/{self.month:02d}: {self.avg_temperature:.1f}°C"
    
    def get_month_name(self):
        """Return month name with error handling."""
        try:
            return calendar.month_name[self.month]
        except (IndexError, AttributeError):
            # Fallback if month is invalid
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            if 1 <= self.month <= 12:
                return month_names[self.month - 1]
            return 'Unknown'
    
    def get_short_month_name(self):
        """Return abbreviated month name."""
        try:
            return calendar.month_abbr[self.month]
        except (IndexError, AttributeError):
            month_abbr = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            if 1 <= self.month <= 12:
                return month_abbr[self.month - 1]
            return 'Unknown'
    
    def get_season(self):
        """Return season based on month and hemisphere (assuming Southern Hemisphere for East Africa)."""
        if self.month in [12, 1, 2]:
            return "Summer"
        elif self.month in [3, 4, 5]:
            return "Autumn"
        elif self.month in [6, 7, 8]:
            return "Winter"
        else:
            return "Spring"
    
    def get_label(self):
        """Return formatted label for charts: 'Mar 2024'."""
        return f"{self.get_short_month_name()} {self.year}"
    
    def is_prediction(self):
        """Check if this record contains prediction data."""
        return self.predicted_temperature is not None and self.data_source == 'predicted'
    
    def calculate_anomalies(self, historical_avg_temp=None, historical_avg_rain=None):
        """
        Calculate temperature and rainfall anomalies.
        Can be called with historical averages or calculated internally.
        """
        if historical_avg_temp is not None:
            self.temperature_anomaly = self.avg_temperature - historical_avg_temp
        
        if historical_avg_rain is not None:
            self.rainfall_anomaly = self.total_rainfall - historical_avg_rain
        
        self.save()
    
    def get_prediction_interval(self):
        """Calculate prediction interval based on confidence level."""
        if self.predicted_temperature and self.prediction_confidence:
            # Simple calculation: ± uncertainty based on confidence
            uncertainty = (100 - self.prediction_confidence) / 50  # 0-2°C range
            lower = self.predicted_temperature - uncertainty
            upper = self.predicted_temperature + uncertainty
            return lower, upper
        return None, None
    
    def to_dict(self):
        """Convert to dictionary for chart data."""
        return {
            'year': self.year,
            'month': self.month,
            'month_name': self.get_month_name(),
            'avg_temperature': self.avg_temperature,
            'predicted_temperature': self.predicted_temperature,
            'prediction_confidence': self.prediction_confidence,
            'total_rainfall': self.total_rainfall,
            'predicted_rainfall': self.predicted_rainfall,
            'avg_humidity': self.avg_humidity,
            'avg_wind_speed': self.avg_wind_speed,
            'season': self.get_season(),
            'is_prediction': self.is_prediction(),
            'label': self.get_label()
        }