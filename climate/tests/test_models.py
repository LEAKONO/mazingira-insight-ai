"""
Tests for climate models.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta

from climate.models import Region, ClimateData, CarbonFootprint, EnvironmentalReport, Prediction


class RegionModelTest(TestCase):
    """Test the Region model."""
    
    def setUp(self):
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921),
            population=5000000,
            area_sq_km=696,
            climate_zone='Tropical Highland',
            elevation=1795
        )
    
    def test_region_creation(self):
        """Test region creation."""
        self.assertEqual(self.region.name, 'Nairobi')
        self.assertEqual(self.region.country, 'Kenya')
        self.assertEqual(self.region.population, 5000000)
        self.assertTrue(self.region.location)
    
    def test_region_str(self):
        """Test string representation."""
        self.assertEqual(str(self.region), 'Nairobi, Kenya')
    
    def test_get_coordinates(self):
        """Test get_coordinates method."""
        lat, lon = self.region.get_coordinates()
        self.assertAlmostEqual(lat, -1.2921, places=4)
        self.assertAlmostEqual(lon, 36.8219, places=4)
    
    def test_to_geojson(self):
        """Test GeoJSON conversion."""
        geojson = self.region.to_geojson()
        self.assertEqual(geojson['type'], 'Feature')
        self.assertEqual(geojson['properties']['name'], 'Nairobi')
        self.assertEqual(geojson['properties']['country'], 'Kenya')
        self.assertEqual(geojson['geometry']['type'], 'Point')


class ClimateDataModelTest(TestCase):
    """Test the ClimateData model."""
    
    def setUp(self):
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        self.climate_data = ClimateData.objects.create(
            region=self.region,
            timestamp=timezone.now(),
            temperature=22.5,
            humidity=65.0,
            rainfall=0.0,
            air_quality_index=45.0,
            wind_speed=5.0,
            source='api'
        )
    
    def test_climate_data_creation(self):
        """Test climate data creation."""
        self.assertEqual(self.climate_data.temperature, 22.5)
        self.assertEqual(self.climate_data.humidity, 65.0)
        self.assertEqual(self.climate_data.source, 'api')
        self.assertEqual(self.climate_data.region, self.region)
    
    def test_climate_data_str(self):
        """Test string representation."""
        expected = f'Nairobi - {self.climate_data.timestamp.strftime("%Y-%m-%d %H:%M")}'
        self.assertEqual(str(self.climate_data), expected)
    
    def test_get_weather_summary(self):
        """Test weather summary generation."""
        summary = self.climate_data.get_weather_summary()
        self.assertIn('Warm', summary)
        self.assertIn('Dry', summary)
        
        # Test with different temperatures
        self.climate_data.temperature = 15.0
        summary = self.climate_data.get_weather_summary()
        self.assertIn('Cool', summary)
        
        self.climate_data.temperature = 32.0
        summary = self.climate_data.get_weather_summary()
        self.assertIn('Hot', summary)
        
        # Test with rainfall
        self.climate_data.rainfall = 15.0
        summary = self.climate_data.get_weather_summary()
        self.assertIn('Heavy rain', summary)


class CarbonFootprintModelTest(TestCase):
    """Test the CarbonFootprint model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.carbon_footprint = CarbonFootprint.objects.create(
            user=self.user,
            transport_km=100,
            electricity_kwh=200,
            diet_type='meat_medium',
            waste_kg=5,
            total_co2e=4500,
            transport_co2e=1200,
            electricity_co2e=1800,
            diet_co2e=2000,
            waste_co2e=300
        )
    
    def test_carbon_footprint_creation(self):
        """Test carbon footprint creation."""
        self.assertEqual(self.carbon_footprint.user, self.user)
        self.assertEqual(self.carbon_footprint.transport_km, 100)
        self.assertEqual(self.carbon_footprint.total_co2e, 4500)
    
    def test_carbon_footprint_str(self):
        """Test string representation."""
        expected = f'testuser - {self.carbon_footprint.calculation_date.strftime("%Y-%m-%d")} - 4500.0 kg CO2e'
        self.assertEqual(str(self.carbon_footprint), expected)
    
    def test_get_emission_level(self):
        """Test emission level classification."""
        # Low emissions
        self.carbon_footprint.total_co2e = 1500
        self.assertEqual(self.carbon_footprint.get_emission_level(), 'Low')
        
        # Moderate emissions
        self.carbon_footprint.total_co2e = 3500
        self.assertEqual(self.carbon_footprint.get_emission_level(), 'Moderate')
        
        # High emissions
        self.carbon_footprint.total_co2e = 7500
        self.assertEqual(self.carbon_footprint.get_emission_level(), 'High')
        
        # Very high emissions
        self.carbon_footprint.total_co2e = 15000
        self.assertEqual(self.carbon_footprint.get_emission_level(), 'Very High')


class EnvironmentalReportModelTest(TestCase):
    """Test the EnvironmentalReport model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        self.report = EnvironmentalReport.objects.create(
            user=self.user,
            region=self.region,
            report_type='flood',
            title='Test Flood Report',
            description='This is a test flood report description.',
            latitude=-1.2921,
            longitude=36.8219,
            status='reported',
            is_public=True
        )
    
    def test_environmental_report_creation(self):
        """Test environmental report creation."""
        self.assertEqual(self.report.user, self.user)
        self.assertEqual(self.report.region, self.region)
        self.assertEqual(self.report.report_type, 'flood')
        self.assertEqual(self.report.title, 'Test Flood Report')
        self.assertTrue(self.report.is_public)
    
    def test_environmental_report_str(self):
        """Test string representation."""
        expected = 'flood - Test Flood Report (Nairobi)'
        self.assertEqual(str(self.report), expected)


class PredictionModelTest(TestCase):
    """Test the Prediction model."""
    
    def setUp(self):
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        self.prediction = Prediction.objects.create(
            region=self.region,
            prediction_date=timezone.now() + timedelta(days=1),
            predicted_temperature=23.5,
            predicted_rainfall=2.5,
            temperature_lower=22.0,
            temperature_upper=25.0,
            rainfall_lower=1.0,
            rainfall_upper=4.0,
            model_version='v1.0'
        )
    
    def test_prediction_creation(self):
        """Test prediction creation."""
        self.assertEqual(self.prediction.region, self.region)
        self.assertEqual(self.prediction.predicted_temperature, 23.5)
        self.assertEqual(self.prediction.model_version, 'v1.0')
    
    def test_prediction_str(self):
        """Test string representation."""
        date_str = self.prediction.prediction_date.strftime('%Y-%m-%d')
        expected = f'Nairobi - {date_str}'
        self.assertEqual(str(self.prediction), expected)


class ModelValidationTest(TestCase):
    """Test model validation and constraints."""
    
    def test_climate_data_unique_constraint(self):
        """Test unique constraint on region and timestamp."""
        region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        timestamp = timezone.now()
        
        # Create first record
        ClimateData.objects.create(
            region=region,
            timestamp=timestamp,
            temperature=22.5,
            humidity=65.0,
            source='api'
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            ClimateData.objects.create(
                region=region,
                timestamp=timestamp,
                temperature=23.0,
                humidity=60.0,
                source='api'
            )
    
    def test_prediction_unique_constraint(self):
        """Test unique constraint on region and prediction_date."""
        region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        prediction_date = timezone.now() + timedelta(days=1)
        
        # Create first prediction
        Prediction.objects.create(
            region=region,
            prediction_date=prediction_date,
            predicted_temperature=23.5,
            predicted_rainfall=2.5,
            model_version='v1.0'
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            Prediction.objects.create(
                region=region,
                prediction_date=prediction_date,
                predicted_temperature=24.0,
                predicted_rainfall=3.0,
                model_version='v1.0'
            )