"""
Tests for climate API views.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta
import json

from climate.models import Region, ClimateData, CarbonFootprint, EnvironmentalReport
from climate.serializers import RegionSerializer


class RegionAPITest(TestCase):
    """Test Region API endpoints."""
    
    def setUp(self):
        self.client = TestCase.client_class()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921),
            population=5000000,
            climate_zone='Tropical Highland'
        )
        
        # Create some climate data for the region
        for i in range(5):
            ClimateData.objects.create(
                region=self.region,
                timestamp=timezone.now() - timedelta(days=i),
                temperature=22.0 + i,
                humidity=60.0 + i,
                rainfall=i * 0.5,
                source='api'
            )
    
    def test_region_list_api(self):
        """Test region list API endpoint."""
        response = self.client.get('/api/regions/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertGreater(len(data['results']), 0)
        
        # Check first region data
        first_region = data['results'][0]
        self.assertEqual(first_region['name'], 'Nairobi')
        self.assertEqual(first_region['country'], 'Kenya')
    
    def test_region_detail_api(self):
        """Test region detail API endpoint."""
        response = self.client.get(f'/api/regions/{self.region.id}/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['name'], 'Nairobi')
        self.assertEqual(data['country'], 'Kenya')
        self.assertIn('coordinates', data)
        self.assertIn('latest_data', data)
    
    def test_region_climate_data_api(self):
        """Test region climate data API endpoint."""
        response = self.client.get(f'/api/regions/{self.region.id}/climate_data/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 5)
        
        # Check climate data structure
        first_data = data[0]
        self.assertIn('temperature', first_data)
        self.assertIn('humidity', first_data)
        self.assertIn('timestamp', first_data)
    
    def test_region_statistics_api(self):
        """Test region statistics API endpoint."""
        response = self.client.get(f'/api/regions/{self.region.id}/statistics/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('avg_temp', data)
        self.assertIn('max_temp', data)
        self.assertIn('min_temp', data)
        self.assertIn('total_rainfall', data)
        self.assertIn('record_count', data)
        
        # Check that statistics are calculated correctly
        self.assertEqual(data['record_count'], 5)


class ClimateDataAPITest(TestCase):
    """Test ClimateData API endpoints."""
    
    def setUp(self):
        self.client = TestCase.client_class()
        
        self.region1 = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        self.region2 = Region.objects.create(
            name='Mombasa',
            country='Kenya',
            location=Point(39.6682, -4.0435)
        )
        
        # Create climate data for both regions
        for i, region in enumerate([self.region1, self.region2]):
            for j in range(3):
                ClimateData.objects.create(
                    region=region,
                    timestamp=timezone.now() - timedelta(hours=j),
                    temperature=25.0 + i,
                    humidity=60.0 + j,
                    rainfall=j * 0.5,
                    source='api'
                )
    
    def test_climate_data_list_api(self):
        """Test climate data list API endpoint."""
        response = self.client.get('/api/climate-data/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 6)  # 2 regions × 3 data points
    
    def test_climate_data_filter_by_region(self):
        """Test filtering climate data by region."""
        response = self.client.get(f'/api/climate-data/?region_id={self.region1.id}')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['results']), 3)  # Only region1's data
        
        # Check that all data belongs to region1
        for item in data['results']:
            self.assertEqual(item['region'], self.region1.id)
    
    def test_climate_data_filter_by_date(self):
        """Test filtering climate data by date range."""
        yesterday = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        response = self.client.get(
            f'/api/climate-data/?start_date={yesterday}&end_date={tomorrow}'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['results']), 6)  # All data within range
    
    def test_climate_data_latest_api(self):
        """Test latest climate data API endpoint."""
        response = self.client.get('/api/climate-data/latest/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 2)  # Latest from each region
        
        # Check that we have latest data for each region
        regions = {item['region'] for item in data}
        self.assertEqual(len(regions), 2)


class WeatherAPITest(TestCase):
    """Test weather API endpoints."""
    
    def setUp(self):
        self.client = TestCase.client_class()
    
    def test_weather_data_api(self):
        """Test weather data API endpoint."""
        # Test with city parameter
        response = self.client.get('/api/weather/?city=Nairobi')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Check response structure
        self.assertIn('location', data)
        self.assertIn('weather', data)
        self.assertIn('main', data)
        
        # Check location data
        self.assertEqual(data['location']['name'], 'Nairobi')
        self.assertEqual(data['location']['country'], 'KE')
        
        # Check weather data
        self.assertIn('temperature', data['main'])
        self.assertIn('humidity', data['main'])
        self.assertIn('pressure', data['main'])
    
    def test_weather_data_api_with_coordinates(self):
        """Test weather data API with coordinates."""
        response = self.client.get('/api/weather/?latitude=-1.2921&longitude=36.8219')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('location', data)
        self.assertIn('main', data)
    
    def test_weather_data_api_validation(self):
        """Test weather data API validation."""
        # Test without any location parameter
        response = self.client.get('/api/weather/')
        
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('location', data['error'])


class CarbonFootprintAPITest(TestCase):
    """Test CarbonFootprint API endpoints."""
    
    def setUp(self):
        self.client = TestCase.client_class()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create carbon footprints for the user
        for i in range(3):
            CarbonFootprint.objects.create(
                user=self.user,
                transport_km=100 + i * 10,
                electricity_kwh=200 + i * 20,
                diet_type='meat_medium',
                waste_kg=5,
                total_co2e=4500 + i * 500,
                transport_co2e=1200,
                electricity_co2e=1800,
                diet_co2e=2000,
                waste_co2e=300
            )
    
    def test_carbon_footprint_list_api_requires_auth(self):
        """Test that carbon footprint list requires authentication."""
        response = self.client.get('/api/carbon-footprints/')
        
        # Should return 401 or 403 for unauthenticated users
        self.assertIn(response.status_code, [401, 403])
    
    def test_carbon_footprint_list_api_with_auth(self):
        """Test carbon footprint list with authentication."""
        self.client.force_login(self.user)
        
        response = self.client.get('/api/carbon-footprints/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 3)
        
        # Check that all footprints belong to the authenticated user
        for footprint in data['results']:
            self.assertEqual(footprint['user']['username'], 'testuser')
    
    def test_carbon_footprint_create_api(self):
        """Test creating carbon footprint via API."""
        self.client.force_login(self.user)
        
        new_footprint = {
            'transport_km': 150,
            'electricity_kwh': 250,
            'diet_type': 'meat_light',
            'waste_kg': 4,
            'total_co2e': 4000,
            'transport_co2e': 1500,
            'electricity_co2e': 2000,
            'diet_co2e': 1500,
            'waste_co2e': 250
        }
        
        response = self.client.post(
            '/api/carbon-footprints/',
            data=json.dumps(new_footprint),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Check that footprint was created
        data = response.json()
        self.assertEqual(data['transport_km'], 150)
        self.assertEqual(data['diet_type'], 'meat_light')
        self.assertEqual(data['user']['username'], 'testuser')
        
        # Check total count
        self.assertEqual(CarbonFootprint.objects.filter(user=self.user).count(), 4)
    
    def test_carbon_footprint_statistics_api(self):
        """Test carbon footprint statistics API."""
        self.client.force_login(self.user)
        
        response = self.client.get('/api/carbon-footprints/statistics/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('latest_footprint', data)
        self.assertIn('average_co2e', data)
        self.assertIn('total_calculations', data)
        self.assertIn('emission_level', data)
        
        # Check statistics values
        self.assertEqual(data['total_calculations'], 3)
        self.assertIsInstance(data['average_co2e'], float)


class EnvironmentalReportAPITest(TestCase):
    """Test EnvironmentalReport API endpoints."""
    
    def setUp(self):
        self.client = TestCase.client_class()
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
        
        # Create public and private reports
        self.public_report = EnvironmentalReport.objects.create(
            user=self.user,
            region=self.region,
            report_type='flood',
            title='Public Flood Report',
            description='This is a public report.',
            latitude=-1.2921,
            longitude=36.8219,
            is_public=True
        )
        
        self.private_report = EnvironmentalReport.objects.create(
            user=self.user,
            region=self.region,
            report_type='pollution',
            title='Private Pollution Report',
            description='This is a private report.',
            latitude=-1.2921,
            longitude=36.8219,
            is_public=False
        )
    
    def test_environmental_report_list_api_public(self):
        """Test environmental report list API for public reports."""
        response = self.client.get('/api/reports/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        
        # Should only see public reports when not authenticated
        public_reports = [r for r in data['results'] if r['is_public']]
        self.assertEqual(len(public_reports), len(data['results']))
        
        # Check that private report is not included
        report_titles = [r['title'] for r in data['results']]
        self.assertIn('Public Flood Report', report_titles)
        self.assertNotIn('Private Pollution Report', report_titles)
    
    def test_environmental_report_list_api_with_auth(self):
        """Test environmental report list API with authentication."""
        self.client.force_login(self.user)
        
        response = self.client.get('/api/reports/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Should see both public and own private reports when authenticated
        report_titles = [r['title'] for r in data['results']]
        self.assertIn('Public Flood Report', report_titles)
        self.assertIn('Private Pollution Report', report_titles)
    
    def test_environmental_report_create_api(self):
        """Test creating environmental report via API."""
        self.client.force_login(self.user)
        
        new_report = {
            'region': self.region.id,
            'report_type': 'drought',
            'title': 'New Drought Report',
            'description': 'This is a new drought report created via API.',
            'latitude': -1.2921,
            'longitude': 36.8219,
            'is_public': True
        }
        
        response = self.client.post(
            '/api/reports/',
            data=json.dumps(new_report),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Check that report was created
        data = response.json()
        self.assertEqual(data['title'], 'New Drought Report')
        self.assertEqual(data['report_type'], 'drought')
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertTrue(data['is_public'])
        
        # Check total count
        self.assertEqual(EnvironmentalReport.objects.count(), 3)


class ClimateStatisticsAPITest(TestCase):
    """Test climate statistics API endpoint."""
    
    def setUp(self):
        self.client = TestCase.client_class()
        
        self.region1 = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        self.region2 = Region.objects.create(
            name='Mombasa',
            country='Kenya',
            location=Point(39.6682, -4.0435)
        )
        
        # Create climate data with different values
        ClimateData.objects.create(
            region=self.region1,
            timestamp=timezone.now(),
            temperature=22.0,
            humidity=60.0,
            rainfall=10.0,
            air_quality_index=45.0,
            source='api'
        )
        
        ClimateData.objects.create(
            region=self.region2,
            timestamp=timezone.now(),
            temperature=28.0,
            humidity=75.0,
            rainfall=5.0,
            air_quality_index=55.0,
            source='api'
        )
    
    def test_climate_statistics_api(self):
        """Test climate statistics API endpoint."""
        response = self.client.get('/api/statistics/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Check basic statistics
        self.assertIn('basic_statistics', data)
        basic_stats = data['basic_statistics']
        
        self.assertIn('total_readings', basic_stats)
        self.assertIn('avg_temperature', basic_stats)
        self.assertIn('avg_humidity', basic_stats)
        self.assertIn('total_rainfall', basic_stats)
        
        # Check values
        self.assertEqual(basic_stats['total_readings'], 2)
        self.assertEqual(basic_stats['avg_temperature'], 25.0)  # (22 + 28) / 2
        self.assertEqual(basic_stats['total_rainfall'], 15.0)  # 10 + 5
        
        # Check regional statistics
        self.assertIn('regional_statistics', data)
        regional_stats = data['regional_statistics']
        
        self.assertEqual(len(regional_stats), 2)
        
        # Check that we have stats for both regions
        region_names = {stat['region'] for stat in regional_stats}
        self.assertEqual(region_names, {'Nairobi', 'Mombasa'})
        
        # Check recent predictions
        self.assertIn('recent_predictions', data)
        self.assertIn('last_updated', data)


class RegionsGeoJSONAPITest(TestCase):
    """Test regions GeoJSON API endpoint."""
    
    def setUp(self):
        self.client = TestCase.client_class()
        
        self.region1 = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921),
            population=5000000,
            climate_zone='Tropical Highland'
        )
        
        self.region2 = Region.objects.create(
            name='Mombasa',
            country='Kenya',
            location=Point(39.6682, -4.0435),
            population=1200000,
            climate_zone='Tropical Coastal'
        )
    
    def test_regions_geojson_api(self):
        """Test regions GeoJSON API endpoint."""
        response = self.client.get('/api/regions/geojson/')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Check GeoJSON structure
        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertIn('features', data)
        self.assertEqual(len(data['features']), 2)
        
        # Check first feature
        first_feature = data['features'][0]
        self.assertEqual(first_feature['type'], 'Feature')
        self.assertIn('properties', first_feature)
        self.assertIn('geometry', first_feature)
        
        # Check properties
        properties = first_feature['properties']
        self.assertIn('name', properties)
        self.assertIn('country', properties)
        self.assertIn('population', properties)
        self.assertIn('climate_zone', properties)
        
        # Check geometry
        geometry = first_feature['geometry']
        self.assertEqual(geometry['type'], 'Point')
        self.assertIn('coordinates', geometry)
        self.assertEqual(len(geometry['coordinates']), 2)