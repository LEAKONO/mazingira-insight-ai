"""
Django management command to fetch and store weather data from APIs.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from climate.models import Region, ClimateData
from climate.api.weather_api import WeatherAPIClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch current weather data for all regions and store in database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            type=str,
            help='Fetch data for specific region only'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force fetch even if recent data exists'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting weather data fetch...'))
        
        # Get regions to fetch
        if options['region']:
            regions = Region.objects.filter(name__icontains=options['region'])
            if not regions.exists():
                self.stdout.write(self.style.ERROR(f'Region "{options["region"]}" not found'))
                return
        else:
            regions = Region.objects.all()
        
        self.stdout.write(f'Fetching data for {regions.count()} regions...')
        
        # Initialize weather client
        weather_client = WeatherAPIClient()
        
        success_count = 0
        fail_count = 0
        
        for region in regions:
            try:
                # Check if we have recent data (within last hour)
                if not options['force']:
                    recent_data = ClimateData.objects.filter(
                        region=region,
                        timestamp__gte=timezone.now() - timedelta(hours=1)
                    ).exists()
                    
                    if recent_data:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping {region.name} - recent data exists')
                        )
                        continue
                
                # Get coordinates
                lat, lon = region.get_coordinates()
                if not lat or not lon:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping {region.name} - no coordinates')
                    )
                    continue
                
                # Fetch weather data
                self.stdout.write(f'Fetching data for {region.name}...')
                weather_data = weather_client.get_weather_data({
                    'latitude': lat,
                    'longitude': lon
                })
                
                # Fetch air quality data
                air_quality = None
                try:
                    air_quality = weather_client.get_air_quality(lat, lon)
                except Exception as e:
                    logger.warning(f'Failed to fetch air quality for {region.name}: {e}')
                
                # Get rainfall from API response
                rainfall_data = weather_data.get('rain', 0)
                # If it's a dictionary with '1h' key (hourly rainfall), extract that value
                if isinstance(rainfall_data, dict):
                    rainfall = rainfall_data.get('1h', 0)
                else:
                    rainfall = rainfall_data
                
                # Create ClimateData record
                climate_data = ClimateData(
                    region=region,
                    timestamp=weather_data.get('timestamp', timezone.now()),
                    temperature=weather_data['main']['temperature'],
                    humidity=weather_data['main']['humidity'],
                    rainfall=rainfall,  # Now using actual rainfall data
                    air_quality_index=(
                        self._calculate_aqi_from_data(air_quality)
                        if air_quality and air_quality.get('aqi')
                        else None
                    ),
                    wind_speed=weather_data['wind']['speed'],
                    wind_direction=weather_data['wind'].get('direction'),
                    pressure=weather_data['main'].get('pressure'),
                    visibility=weather_data.get('visibility'),
                    source='api'
                )
                
                # Save the data
                climate_data.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully fetched data for {region.name}: '
                        f'{climate_data.temperature}°C, '
                        f'{climate_data.humidity}% humidity, '
                        f'{climate_data.rainfall}mm rain'
                    )
                )
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to fetch data for {region.name}: {e}')
                )
                logger.error(f'Error fetching data for {region.name}: {e}')
                fail_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('Weather Data Fetch Summary:'))
        self.stdout.write(self.style.SUCCESS(f'Successfully fetched: {success_count} regions'))
        self.stdout.write(self.style.WARNING(f'Failed: {fail_count} regions'))
        self.stdout.write(self.style.SUCCESS(f'Total regions processed: {regions.count()}'))
        
        if success_count == 0 and fail_count > 0:
            self.stdout.write(self.style.ERROR(
                '\nAll fetches failed. Check your API keys and internet connection.'
            ))
            self.stdout.write(self.style.ERROR(
                'Make sure OPENWEATHER_API_KEY is set in your .env file.'
            ))
    
    def _calculate_aqi_from_data(self, air_quality_data):
        """
        Calculate AQI from air quality data.
        
        This is a simplified calculation. In production, use proper AQI formulas.
        """
        if not air_quality_data or not air_quality_data.get('pollutants'):
            return None
        
        # Find PM2.5 value
        pm25 = None
        for pollutant in air_quality_data['pollutants']:
            if pollutant.get('parameter') == 'pm25':
                pm25 = pollutant.get('value')
                break
        
        if pm25 is None:
            return None
        
        # Simplified AQI calculation based on PM2.5
        # Based on US EPA AQI breakpoints (simplified)
        if pm25 <= 12.0:
            aqi = (50/12.0) * pm25  # Good (0-50)
        elif pm25 <= 35.4:
            aqi = 50 + (50/(35.4-12.0)) * (pm25 - 12.0)  # Moderate (51-100)
        elif pm25 <= 55.4:
            aqi = 100 + (50/(55.4-35.4)) * (pm25 - 35.4)  # Unhealthy for Sensitive Groups (101-150)
        elif pm25 <= 150.4:
            aqi = 150 + (100/(150.4-55.4)) * (pm25 - 55.4)  # Unhealthy (151-200)
        elif pm25 <= 250.4:
            aqi = 200 + (100/(250.4-150.4)) * (pm25 - 150.4)  # Very Unhealthy (201-300)
        else:
            aqi = 300 + (200/(500.4-250.4)) * (pm25 - 250.4)  # Hazardous (301-500)
        
        return round(aqi, 1)