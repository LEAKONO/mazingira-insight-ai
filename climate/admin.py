"""
Admin configuration for the climate application.
"""

from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from .models import Region, ClimateData, CarbonFootprint, EnvironmentalReport, Prediction


@admin.register(Region)
class RegionAdmin(OSMGeoAdmin):
    """Admin interface for Region model with map."""
    list_display = ['name', 'country', 'climate_zone', 'population']
    list_filter = ['country', 'climate_zone']
    search_fields = ['name', 'country']
    ordering = ['name']
    
    # Map settings
    default_lon = 36.8219  # Nairobi
    default_lat = -1.2921
    default_zoom = 6


@admin.register(ClimateData)
class ClimateDataAdmin(admin.ModelAdmin):
    """Admin interface for ClimateData model."""
    list_display = ['region', 'timestamp', 'temperature', 'humidity', 'rainfall', 'source']
    list_filter = ['region', 'source', 'timestamp']
    search_fields = ['region__name']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('region', 'timestamp', 'source')
        }),
        ('Weather Measurements', {
            'fields': ('temperature', 'humidity', 'rainfall', 'air_quality_index')
        }),
        ('Additional Data', {
            'fields': ('wind_speed', 'wind_direction', 'pressure', 'uv_index', 'visibility')
        }),
    )


@admin.register(CarbonFootprint)
class CarbonFootprintAdmin(admin.ModelAdmin):
    """Admin interface for CarbonFootprint model."""
    list_display = ['user', 'calculation_date', 'total_co2e', 'get_emission_level']
    list_filter = ['calculation_date', 'diet_type']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['total_co2e', 'transport_co2e', 'electricity_co2e', 'diet_co2e', 'waste_co2e']
    
    def get_emission_level(self, obj):
        return obj.get_emission_level()
    get_emission_level.short_description = 'Emission Level'


@admin.register(EnvironmentalReport)
class EnvironmentalReportAdmin(admin.ModelAdmin):
    """Admin interface for EnvironmentalReport model."""
    list_display = ['title', 'report_type', 'region', 'status', 'created_at', 'is_public']
    list_filter = ['report_type', 'status', 'is_public', 'created_at']
    search_fields = ['title', 'description', 'region__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('user', 'region', 'report_type', 'title', 'description')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'photo')
        }),
        ('Status', {
            'fields': ('status', 'is_public')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    """Admin interface for Prediction model."""
    list_display = ['region', 'prediction_date', 'predicted_temperature', 'predicted_rainfall', 'model_version']
    list_filter = ['region', 'prediction_date', 'model_version']
    search_fields = ['region__name']
    date_hierarchy = 'prediction_date'
    ordering = ['-prediction_date']