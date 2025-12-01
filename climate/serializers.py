"""
Serializers for the climate application API.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Region, ClimateData, CarbonFootprint, EnvironmentalReport, Prediction


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class RegionSerializer(serializers.ModelSerializer):
    """Serializer for Region model."""
    coordinates = serializers.SerializerMethodField()
    latest_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Region
        fields = [
            'id', 'name', 'country', 'coordinates', 'population',
            'area_sq_km', 'climate_zone', 'elevation', 'latest_data'
        ]
    
    def get_coordinates(self, obj):
        """Return coordinates as dict."""
        lat, lon = obj.get_coordinates()
        return {'lat': lat, 'lon': lon} if lat and lon else None
    
    def get_latest_data(self, obj):
        """Return latest climate data for the region."""
        latest = ClimateData.objects.filter(region=obj).order_by('-timestamp').first()
        if latest:
            return {
                'temperature': latest.temperature,
                'humidity': latest.humidity,
                'rainfall': latest.rainfall,
                'timestamp': latest.timestamp
            }
        return None


class ClimateDataSerializer(serializers.ModelSerializer):
    """Serializer for ClimateData model."""
    region_name = serializers.CharField(source='region.name', read_only=True)
    
    class Meta:
        model = ClimateData
        fields = [
            'id', 'region', 'region_name', 'timestamp', 'temperature',
            'humidity', 'rainfall', 'air_quality_index', 'wind_speed',
            'wind_direction', 'pressure', 'uv_index', 'visibility', 'source'
        ]


class CarbonFootprintSerializer(serializers.ModelSerializer):
    """Serializer for CarbonFootprint model."""
    user = UserSerializer(read_only=True)
    emission_level = serializers.SerializerMethodField()
    
    class Meta:
        model = CarbonFootprint
        fields = [
            'id', 'user', 'calculation_date', 'transport_km', 'electricity_kwh',
            'diet_type', 'waste_kg', 'total_co2e', 'transport_co2e',
            'electricity_co2e', 'diet_co2e', 'waste_co2e', 'suggestions',
            'emission_level'
        ]
        read_only_fields = ['total_co2e', 'transport_co2e', 'electricity_co2e',
                          'diet_co2e', 'waste_co2e', 'suggestions']
    
    def get_emission_level(self, obj):
        """Return emission level category."""
        return obj.get_emission_level()


class EnvironmentalReportSerializer(serializers.ModelSerializer):
    """Serializer for EnvironmentalReport model."""
    user = UserSerializer(read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)
    
    class Meta:
        model = EnvironmentalReport
        fields = [
            'id', 'user', 'region', 'region_name', 'report_type', 'title',
            'description', 'latitude', 'longitude', 'photo', 'status',
            'created_at', 'updated_at', 'is_public'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PredictionSerializer(serializers.ModelSerializer):
    """Serializer for Prediction model."""
    region_name = serializers.CharField(source='region.name', read_only=True)
    
    class Meta:
        model = Prediction
        fields = [
            'id', 'region', 'region_name', 'prediction_date',
            'predicted_temperature', 'predicted_rainfall',
            'temperature_lower', 'temperature_upper',
            'rainfall_lower', 'rainfall_upper', 'model_version'
        ]


class WeatherRequestSerializer(serializers.Serializer):
    """Serializer for weather API requests."""
    location = serializers.CharField(required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    city = serializers.CharField(required=False)
    
    def validate(self, data):
        """Validate that at least one location parameter is provided."""
        if not any([data.get('location'), data.get('city'), 
                   (data.get('latitude') and data.get('longitude'))]):
            raise serializers.ValidationError(
                "Provide location, city, or latitude/longitude"
            )
        return data


class PredictionRequestSerializer(serializers.Serializer):
    """Serializer for prediction requests."""
    region_id = serializers.IntegerField(required=True)
    days_ahead = serializers.IntegerField(default=7, min_value=1, max_value=30)
    include_confidence = serializers.BooleanField(default=True)
