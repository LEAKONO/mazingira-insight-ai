"""
Django management command to seed the database with sample data.
FIXED VERSION - matches current model structure
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import random
import json
import math  # Using math instead of numpy

from climate.models import Region, ClimateData, Prediction


class Command(BaseCommand):
    help = 'Seed the database with sample climate data'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))
        
        # Create admin user if not exists
        self.create_admin_user()
        
        # Create sample regions
        regions = self.create_sample_regions()
        
        # Create sample climate data
        self.create_sample_climate_data(regions)
        
        # Create sample predictions
        self.create_sample_predictions(regions)
        
        self.stdout.write(self.style.SUCCESS('Database seeding completed!'))
    
    def create_admin_user(self):
        """Create an admin user if not exists."""
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@mazingirainsight.ai',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS('Created admin user: admin/admin123'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))
    
    def create_sample_regions(self):
        """Create sample regions for East Africa."""
        regions_data = [
            {
                'name': 'Nairobi',
                'country': 'Kenya',
                'latitude': -1.2921,
                'longitude': 36.8219,
                'population': 5000000,
                'area_sq_km': 696,
                'climate_zone': 'Tropical Highland',
                'elevation': 1795,
            },
            {
                'name': 'Mombasa',
                'country': 'Kenya',
                'latitude': -4.0435,
                'longitude': 39.6682,
                'population': 1200000,
                'area_sq_km': 295,
                'climate_zone': 'Tropical Coastal',
                'elevation': 50,
            },
            {
                'name': 'Kisumu',
                'country': 'Kenya',
                'latitude': -0.1022,
                'longitude': 34.7617,
                'population': 500000,
                'area_sq_km': 417,
                'climate_zone': 'Tropical Lakeside',
                'elevation': 1131,
            },
            {
                'name': 'Arusha',
                'country': 'Tanzania',
                'latitude': -3.3869,
                'longitude': 36.6830,
                'population': 800000,
                'area_sq_km': 1590,
                'climate_zone': 'Tropical Highland',
                'elevation': 1387,
            },
            {
                'name': 'Kampala',
                'country': 'Uganda',
                'latitude': 0.3476,
                'longitude': 32.5825,
                'population': 3500000,
                'area_sq_km': 189,
                'climate_zone': 'Tropical',
                'elevation': 1190,
            },
        ]
        
        regions = []
        for data in regions_data:
            region, created = Region.objects.update_or_create(
                name=data['name'],
                country=data['country'],
                defaults={
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    'population': data['population'],
                    'area_sq_km': data['area_sq_km'],
                    'climate_zone': data['climate_zone'],
                    'elevation': data['elevation'],
                    'location_data': {  # Use location_data instead of geojson
                        'type': 'Point',
                        'coordinates': [data['longitude'], data['latitude']]
                    }
                }
            )
            regions.append(region)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created region: {region.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Updated region: {region.name}'))
        
        return regions
    
    def create_sample_climate_data(self, regions):
        """Create sample climate data for regions."""
        self.stdout.write('Creating sample climate data...')
        
        # Delete existing data to avoid duplicates
        ClimateData.objects.all().delete()
        
        # Generate data for the last 30 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        climate_data_objects = []
        
        for region in regions:
            # Base climate parameters for the region
            if 'Nairobi' in region.name:
                base_temp = 22.0
                base_humidity = 60.0
                base_rainfall = 2.0
            elif 'Mombasa' in region.name:
                base_temp = 28.0
                base_humidity = 75.0
                base_rainfall = 5.0
            elif 'Kisumu' in region.name:
                base_temp = 25.0
                base_humidity = 70.0
                base_rainfall = 4.0
            elif 'Arusha' in region.name:
                base_temp = 20.0
                base_humidity = 65.0
                base_rainfall = 3.0
            else:
                base_temp = 24.0
                base_humidity = 65.0
                base_rainfall = 3.0
            
            # Generate DAILY data (instead of hourly) to reduce complexity
            current_date = start_date
            while current_date <= end_date:
                # Add some randomness
                hour = current_date.hour
                day_of_year = current_date.timetuple().tm_yday
                
                # Daily temperature variation using math.sin
                daily_variation = 8 * (math.sin(2 * math.pi * hour / 24) + 1) / 2
                
                # Seasonal variation (simplified)
                seasonal_variation = 5 * math.sin(2 * math.pi * day_of_year / 365)
                
                # Calculate final values
                temperature = base_temp + daily_variation + seasonal_variation + random.uniform(-2, 2)
                humidity = base_humidity + random.uniform(-10, 10)
                
                # Rainfall (higher probability during certain hours)
                if random.random() < 0.1:  # 10% chance of rain
                    rainfall = random.uniform(0.1, 5.0)
                else:
                    rainfall = 0.0
                
                # Air quality (worse during certain hours)
                if hour in [8, 9, 17, 18]:  # Rush hours
                    aqi = random.uniform(50, 100)
                else:
                    aqi = random.uniform(20, 50)
                
                # Create ClimateData object
                climate_data = ClimateData(
                    region=region,
                    timestamp=current_date,
                    temperature=temperature,
                    humidity=humidity,
                    rainfall=rainfall,
                    air_quality_index=aqi,
                    wind_speed=random.uniform(1, 10),
                    wind_direction=random.uniform(0, 360),
                    pressure=1013 + random.uniform(-10, 10),
                    source='synthetic'
                )
                
                climate_data_objects.append(climate_data)
                
                # Move to next DAY (not hour) to reduce data volume
                current_date += timedelta(days=1)
        
        # Bulk create in smaller batches
        batch_size = 100
        for i in range(0, len(climate_data_objects), batch_size):
            batch = climate_data_objects[i:i + batch_size]
            ClimateData.objects.bulk_create(batch)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(climate_data_objects)} climate data records'))
    
    def create_sample_predictions(self, regions):
        """Create sample predictions."""
        self.stdout.write('Creating sample predictions...')
        
        # Delete existing predictions
        Prediction.objects.all().delete()
        
        prediction_objects = []
        
        for region in regions:
            # Base values
            if 'Nairobi' in region.name:
                base_temp = 22.0
                base_rainfall = 2.0
            elif 'Mombasa' in region.name:
                base_temp = 28.0
                base_rainfall = 5.0
            elif 'Kisumu' in region.name:
                base_temp = 25.0
                base_rainfall = 4.0
            else:
                base_temp = 24.0
                base_rainfall = 3.0
            
            # Create predictions for next 7 days
            for day in range(1, 8):
                prediction_date = timezone.now() + timedelta(days=day)
                
                # Add some variation
                temp_variation = random.uniform(-3, 3)
                rainfall_variation = random.uniform(-1, 1)
                
                prediction = Prediction(
                    region=region,
                    prediction_date=prediction_date,
                    predicted_temperature=base_temp + temp_variation,
                    predicted_rainfall=max(0, base_rainfall + rainfall_variation),
                    temperature_lower=base_temp + temp_variation - 1.5,
                    temperature_upper=base_temp + temp_variation + 1.5,
                    rainfall_lower=max(0, base_rainfall + rainfall_variation - 0.5),
                    rainfall_upper=max(0, base_rainfall + rainfall_variation + 0.5),
                    model_version='v1.0'
                )
                
                prediction_objects.append(prediction)
        
        # Bulk create predictions
        Prediction.objects.bulk_create(prediction_objects)
        self.stdout.write(self.style.SUCCESS(f'Created {len(prediction_objects)} prediction records'))