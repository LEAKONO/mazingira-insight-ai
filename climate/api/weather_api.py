"""
Weather API client for fetching external weather data.
"""

import requests
import json
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class WeatherAPIClient:
    """Client for fetching weather data from external APIs."""
    
    def __init__(self):
        self.openweather_api_key = settings.OPENWEATHER_API_KEY
        self.openaq_api_key = settings.OPENAIR_API_KEY
        self.base_urls = {
            'openweather': 'https://api.openweathermap.org/data/2.5',
            'openaq': 'https://api.openaq.org/v2'
        }
    
    def get_weather_data(self, location_data):
        """
        Get weather data for a location.
        
        Args:
            location_data: dict with 'location', 'city', or 'latitude'/'longitude'
        
        Returns:
            dict: Weather data
        """
        if not self.openweather_api_key:
            logger.warning("OpenWeather API key not configured")
            return self._get_mock_weather_data(location_data)
        
        try:
            # Determine location parameters
            if location_data.get('city'):
                params = {'q': location_data['city'], 'appid': self.openweather_api_key}
            elif location_data.get('latitude') and location_data.get('longitude'):
                params = {
                    'lat': location_data['latitude'],
                    'lon': location_data['longitude'],
                    'appid': self.openweather_api_key
                }
            elif location_data.get('location'):
                # Try to parse location string
                location = location_data['location']
                if ',' in location:
                    # Assume format: "city,country" or "lat,lon"
                    parts = location.split(',')
                    if len(parts) == 2:
                        try:
                            # Try parsing as coordinates
                            lat = float(parts[0].strip())
                            lon = float(parts[1].strip())
                            params = {
                                'lat': lat,
                                'lon': lon,
                                'appid': self.openweather_api_key
                            }
                        except ValueError:
                            # Assume city,country format
                            params = {'q': location, 'appid': self.openweather_api_key}
                else:
                    params = {'q': location, 'appid': self.openweather_api_key}
            else:
                raise ValueError("No valid location provided")
            
            # Add units
            params['units'] = 'metric'
            
            # Make API request
            response = requests.get(
                f"{self.base_urls['openweather']}/weather",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_openweather_data(data)
            else:
                logger.error(f"OpenWeather API error: {response.status_code}")
                return self._get_mock_weather_data(location_data)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {e}")
            return self._get_mock_weather_data(location_data)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return self._get_mock_weather_data(location_data)
    
    def _parse_openweather_data(self, data):
        """Parse OpenWeatherMap API response."""
        return {
            'location': {
                'name': data.get('name', 'Unknown'),
                'country': data.get('sys', {}).get('country', ''),
                'latitude': data.get('coord', {}).get('lat'),
                'longitude': data.get('coord', {}).get('lon'),
            },
            'weather': {
                'main': data.get('weather', [{}])[0].get('main', ''),
                'description': data.get('weather', [{}])[0].get('description', ''),
                'icon': data.get('weather', [{}])[0].get('icon', ''),
            },
            'main': {
                'temperature': data.get('main', {}).get('temp'),
                'feels_like': data.get('main', {}).get('feels_like'),
                'pressure': data.get('main', {}).get('pressure'),
                'humidity': data.get('main', {}).get('humidity'),
            },
            'wind': {
                'speed': data.get('wind', {}).get('speed'),
                'direction': data.get('wind', {}).get('deg'),
            },
            'visibility': data.get('visibility'),
            'clouds': data.get('clouds', {}).get('all'),
            'timestamp': datetime.fromtimestamp(data.get('dt', timezone.now().timestamp())),
            'source': 'openweathermap',
        }
    
    def get_air_quality(self, latitude, longitude):
        """
        Get air quality data for a location.
        
        Args:
            latitude: float
            longitude: float
        
        Returns:
            dict: Air quality data
        """
        if not self.openaq_api_key:
            # Return mock data if no API key
            return self._get_mock_air_quality()
        
        try:
            headers = {'X-API-Key': self.openaq_api_key} if self.openaq_api_key else {}
            
            response = requests.get(
                f"{self.base_urls['openaq']}/latest",
                params={
                    'coordinates': f"{latitude},{longitude}",
                    'radius': 10000,  # 10km radius
                    'limit': 1,
                },
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_openaq_data(data)
            else:
                logger.warning(f"OpenAQ API error: {response.status_code}")
                return self._get_mock_air_quality()
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching air quality data: {e}")
            return self._get_mock_air_quality()
    
    def _parse_openaq_data(self, data):
        """Parse OpenAQ API response."""
        if not data.get('results'):
            return {'aqi': None, 'pollutants': []}
        
        result = data['results'][0]
        measurements = result.get('measurements', [])
        
        pollutants = []
        aqi = None
        
        for measurement in measurements:
            pollutant = {
                'parameter': measurement.get('parameter'),
                'value': measurement.get('value'),
                'unit': measurement.get('unit'),
                'last_updated': measurement.get('lastUpdated'),
            }
            pollutants.append(pollutant)
            
            # Simple AQI calculation (simplified)
            if measurement.get('parameter') == 'pm25':
                value = measurement.get('value', 0)
                # Very basic AQI calculation
                if value <= 12:
                    aqi = 'Good'
                elif value <= 35.4:
                    aqi = 'Moderate'
                elif value <= 55.4:
                    aqi = 'Unhealthy for Sensitive Groups'
                elif value <= 150.4:
                    aqi = 'Unhealthy'
                elif value <= 250.4:
                    aqi = 'Very Unhealthy'
                else:
                    aqi = 'Hazardous'
        
        return {
            'aqi': aqi,
            'pollutants': pollutants,
            'location': result.get('location'),
            'source': 'openaq',
        }
    
    def _get_mock_weather_data(self, location_data):
        """Return mock weather data for development/testing."""
        location_name = location_data.get('city') or location_data.get('location') or 'Nairobi'
        
        # Generate some realistic-looking mock data
        import random
        from datetime import datetime
        
        base_temp = 22.0  # Base temperature for Nairobi
        temp_variation = random.uniform(-3, 3)
        
        return {
            'location': {
                'name': location_name,
                'country': 'KE',
                'latitude': -1.2921,
                'longitude': 36.8219,
            },
            'weather': {
                'main': 'Clear',
                'description': 'clear sky',
                'icon': '01d',
            },
            'main': {
                'temperature': round(base_temp + temp_variation, 1),
                'feels_like': round(base_temp + temp_variation + 1, 1),
                'pressure': 1013,
                'humidity': random.randint(40, 70),
            },
            'wind': {
                'speed': round(random.uniform(1, 5), 1),
                'direction': random.randint(0, 360),
            },
            'visibility': 10000,
            'clouds': random.randint(0, 30),
            'timestamp': datetime.now(),
            'source': 'mock',
            'note': 'Mock data - configure OPENWEATHER_API_KEY for real data',
        }
    
    def _get_mock_air_quality(self):
        """Return mock air quality data."""
        import random
        
        pollutants = [
            {
                'parameter': 'pm25',
                'value': round(random.uniform(5, 25), 1),
                'unit': 'µg/m³',
                'last_updated': datetime.now().isoformat(),
            },
            {
                'parameter': 'pm10',
                'value': round(random.uniform(10, 40), 1),
                'unit': 'µg/m³',
                'last_updated': datetime.now().isoformat(),
            },
            {
                'parameter': 'o3',
                'value': round(random.uniform(20, 60), 1),
                'unit': 'ppb',
                'last_updated': datetime.now().isoformat(),
            },
        ]
        
        # Calculate AQI based on PM2.5
        pm25 = pollutants[0]['value']
        if pm25 <= 12:
            aqi = 'Good'
        elif pm25 <= 35.4:
            aqi = 'Moderate'
        elif pm25 <= 55.4:
            aqi = 'Unhealthy for Sensitive Groups'
        elif pm25 <= 150.4:
            aqi = 'Unhealthy'
        else:
            aqi = 'Very Unhealthy'
        
        return {
            'aqi': aqi,
            'pollutants': pollutants,
            'location': 'Mock Location',
            'source': 'mock',
            'note': 'Mock data - configure OPENAIR_API_KEY for real data',
        }
    
    def get_forecast(self, latitude, longitude, days=5):
        """
        Get weather forecast for a location.
        
        Args:
            latitude: float
            longitude: float
            days: int (1-5)
        
        Returns:
            list: Forecast data
        """
        if not self.openweather_api_key:
            return self._get_mock_forecast(days)
        
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.openweather_api_key,
                'units': 'metric',
                'cnt': days * 8  # 3-hour intervals
            }
            
            response = requests.get(
                f"{self.base_urls['openweather']}/forecast",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_forecast_data(data)
            else:
                logger.error(f"OpenWeather forecast error: {response.status_code}")
                return self._get_mock_forecast(days)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching forecast: {e}")
            return self._get_mock_forecast(days)
    
    def _parse_forecast_data(self, data):
        """Parse forecast data from OpenWeather."""
        forecast_list = []
        
        for item in data.get('list', []):
            forecast = {
                'timestamp': datetime.fromtimestamp(item.get('dt')),
                'temperature': item.get('main', {}).get('temp'),
                'feels_like': item.get('main', {}).get('feels_like'),
                'humidity': item.get('main', {}).get('humidity'),
                'pressure': item.get('main', {}).get('pressure'),
                'weather': item.get('weather', [{}])[0].get('main'),
                'description': item.get('weather', [{}])[0].get('description'),
                'wind_speed': item.get('wind', {}).get('speed'),
                'wind_direction': item.get('wind', {}).get('deg'),
                'rain': item.get('rain', {}).get('3h', 0),
                'snow': item.get('snow', {}).get('3h', 0),
            }
            forecast_list.append(forecast)
        
        return forecast_list
    
    def _get_mock_forecast(self, days):
        """Return mock forecast data."""
        import random
        from datetime import datetime, timedelta
        
        forecast_list = []
        base_temp = 22.0
        
        for i in range(days * 8):  # 3-hour intervals
            timestamp = datetime.now() + timedelta(hours=i*3)
            temp_variation = random.uniform(-4, 4)
            
            forecast = {
                'timestamp': timestamp,
                'temperature': round(base_temp + temp_variation, 1),
                'feels_like': round(base_temp + temp_variation + 1, 1),
                'humidity': random.randint(40, 80),
                'pressure': 1013 + random.randint(-10, 10),
                'weather': random.choice(['Clear', 'Clouds', 'Rain', 'Thunderstorm']),
                'description': random.choice(['clear sky', 'few clouds', 'light rain', 'thunderstorm']),
                'wind_speed': round(random.uniform(1, 8), 1),
                'wind_direction': random.randint(0, 360),
                'rain': random.uniform(0, 5) if random.random() > 0.7 else 0,
                'snow': 0,
            }
            forecast_list.append(forecast)
        
        return forecast_list