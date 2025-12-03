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
        self.openweather_api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        self.openaq_api_key = getattr(settings, 'OPENAIR_API_KEY', None)
        self.base_urls = {
            'openweather': 'https://api.openweathermap.org/data/2.5',
            'openaq': 'https://api.openaq.org/v2'
        }
        
        # Log API key status on initialization
        if self.openweather_api_key:
            logger.info(f"Weather API Client initialized with OpenWeather API key: {self.openweather_api_key[:8]}...")
        else:
            logger.warning("Weather API Client initialized WITHOUT OpenWeather API key")
    
    def get_weather_data(self, location_data):
        """
        Get weather data for a location.
        
        Args:
            location_data: dict with 'location', 'city', or 'latitude'/'longitude'
        
        Returns:
            dict: Weather data
        """
        # Log the incoming request
        logger.info(f"get_weather_data called with: {location_data}")
        
        if not self.openweather_api_key:
            logger.warning("OpenWeather API key not configured, using mock data")
            mock_data = self._get_mock_weather_data(location_data)
            mock_data['error'] = 'API key not configured'
            return mock_data
        
        try:
            # Determine location parameters
            params = {}
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
                logger.error("No valid location provided in location_data")
                mock_data = self._get_mock_weather_data(location_data)
                mock_data['error'] = 'No valid location provided'
                return mock_data
            
            # Add units for metric system
            params['units'] = 'metric'
            
            # Log the API request details
            logger.info(f"Making OpenWeather API request with params: {params}")
            
            # Construct URL
            url = f"{self.base_urls['openweather']}/weather"
            logger.debug(f"Request URL: {url}")
            
            # Make API request with timeout
            response = requests.get(url, params=params, timeout=15)
            
            # Log response status
            logger.info(f"OpenWeather API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"API response data received")
                parsed_data = self._parse_openweather_data(data)
                logger.info(f"Successfully parsed OpenWeather data for {parsed_data['location']['name']}")
                return parsed_data
            elif response.status_code == 401:
                # Unauthorized - likely invalid API key
                logger.error(f"OpenWeather API error: 401 Unauthorized")
                logger.error(f"API Key used: {self.openweather_api_key[:8]}...")
                logger.error(f"Full error response: {response.text}")
                
                # Return mock data with detailed error
                mock_data = self._get_mock_weather_data(location_data)
                mock_data['error'] = 'API Key Invalid (401 Unauthorized)'
                mock_data['error_details'] = response.text
                mock_data['api_key_used'] = f"{self.openweather_api_key[:8]}..."
                return mock_data
            elif response.status_code == 429:
                # Too many requests
                logger.error(f"OpenWeather API error: 429 Too Many Requests")
                mock_data = self._get_mock_weather_data(location_data)
                mock_data['error'] = 'API Rate Limit Exceeded'
                mock_data['error_details'] = 'Too many requests. Please wait and try again.'
                return mock_data
            elif response.status_code == 404:
                # City not found
                logger.error(f"OpenWeather API error: 404 Not Found for location: {location_data}")
                mock_data = self._get_mock_weather_data(location_data)
                mock_data['error'] = 'Location not found'
                mock_data['error_details'] = response.text
                return mock_data
            else:
                # Other API errors
                logger.error(f"OpenWeather API error: {response.status_code}")
                logger.error(f"Error response: {response.text}")
                mock_data = self._get_mock_weather_data(location_data)
                mock_data['error'] = f'API Error {response.status_code}'
                mock_data['error_details'] = response.text[:200]
                return mock_data
                
        except requests.exceptions.Timeout:
            logger.error("OpenWeather API request timed out")
            mock_data = self._get_mock_weather_data(location_data)
            mock_data['error'] = 'Request timeout'
            return mock_data
        except requests.exceptions.ConnectionError:
            logger.error("OpenWeather API connection error")
            mock_data = self._get_mock_weather_data(location_data)
            mock_data['error'] = 'Connection error'
            return mock_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {e}")
            mock_data = self._get_mock_weather_data(location_data)
            mock_data['error'] = f'Request error: {str(e)}'
            return mock_data
        except Exception as e:
            logger.error(f"Unexpected error in get_weather_data: {e}", exc_info=True)
            mock_data = self._get_mock_weather_data(location_data)
            mock_data['error'] = f'Unexpected error: {str(e)}'
            return mock_data
    
    def _parse_openweather_data(self, data):
        """Parse OpenWeatherMap API response."""
        try:
            parsed_data = {
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
                    'temp_min': data.get('main', {}).get('temp_min'),
                    'temp_max': data.get('main', {}).get('temp_max'),
                },
                'wind': {
                    'speed': data.get('wind', {}).get('speed'),
                    'direction': data.get('wind', {}).get('deg'),
                },
                'visibility': data.get('visibility'),
                'clouds': data.get('clouds', {}).get('all'),
                'rain': data.get('rain', {}).get('1h', 0),
                'snow': data.get('snow', {}).get('1h', 0),
                'timestamp': datetime.fromtimestamp(data.get('dt', timezone.now().timestamp())),
                'sunrise': datetime.fromtimestamp(data.get('sys', {}).get('sunrise', 0)) if data.get('sys', {}).get('sunrise') else None,
                'sunset': datetime.fromtimestamp(data.get('sys', {}).get('sunset', 0)) if data.get('sys', {}).get('sunset') else None,
                'source': 'openweathermap',
                'api_response_id': data.get('id'),
                'timezone': data.get('timezone'),
            }
            
            # Add a note for debugging
            parsed_data['note'] = 'Real data from OpenWeatherMap API'
            
            return parsed_data
        except Exception as e:
            logger.error(f"Error parsing OpenWeather data: {e}", exc_info=True)
            raise
    
    def get_air_quality(self, latitude, longitude):
        """
        Get air quality data for a location.
        
        Args:
            latitude: float
            longitude: float
        
        Returns:
            dict: Air quality data
        """
        logger.info(f"get_air_quality called for coordinates: {latitude}, {longitude}")
        
        if not self.openaq_api_key:
            logger.warning("OpenAQ API key not configured, using mock data")
            mock_data = self._get_mock_air_quality()
            mock_data['error'] = 'OpenAQ API key not configured'
            return mock_data
        
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
            
            logger.info(f"OpenAQ API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                parsed_data = self._parse_openaq_data(data)
                logger.info(f"Successfully fetched air quality data")
                return parsed_data
            else:
                logger.warning(f"OpenAQ API error: {response.status_code}")
                mock_data = self._get_mock_air_quality()
                mock_data['error'] = f'OpenAQ API Error {response.status_code}'
                return mock_data
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching air quality data: {e}")
            mock_data = self._get_mock_air_quality()
            mock_data['error'] = f'Request error: {str(e)}'
            return mock_data
    
    def _parse_openaq_data(self, data):
        """Parse OpenAQ API response."""
        try:
            if not data.get('results'):
                return {'aqi': None, 'pollutants': [], 'source': 'openaq', 'note': 'No data available'}
            
            result = data['results'][0]
            measurements = result.get('measurements', [])
            
            pollutants = []
            aqi = None
            aqi_numeric = None
            
            for measurement in measurements:
                pollutant = {
                    'parameter': measurement.get('parameter'),
                    'value': measurement.get('value'),
                    'unit': measurement.get('unit'),
                    'last_updated': measurement.get('lastUpdated'),
                }
                pollutants.append(pollutant)
                
                # Calculate AQI based on pollutants
                if measurement.get('parameter') == 'pm25':
                    value = measurement.get('value', 0)
                    # Calculate AQI (simplified)
                    if value <= 12:
                        aqi = 'Good'
                        aqi_numeric = 50 * (value / 12)
                    elif value <= 35.4:
                        aqi = 'Moderate'
                        aqi_numeric = 50 + (50 * (value - 12) / (35.4 - 12))
                    elif value <= 55.4:
                        aqi = 'Unhealthy for Sensitive Groups'
                        aqi_numeric = 100 + (50 * (value - 35.4) / (55.4 - 35.4))
                    elif value <= 150.4:
                        aqi = 'Unhealthy'
                        aqi_numeric = 150 + (50 * (value - 55.4) / (150.4 - 55.4))
                    elif value <= 250.4:
                        aqi = 'Very Unhealthy'
                        aqi_numeric = 200 + (100 * (value - 150.4) / (250.4 - 150.4))
                    else:
                        aqi = 'Hazardous'
                        aqi_numeric = 300 + (200 * (value - 250.4) / (500.4 - 250.4))
            
            return {
                'aqi': aqi,
                'aqi_numeric': round(aqi_numeric, 1) if aqi_numeric else None,
                'pollutants': pollutants,
                'location': result.get('location'),
                'source': 'openaq',
                'note': 'Real data from OpenAQ API',
            }
        except Exception as e:
            logger.error(f"Error parsing OpenAQ data: {e}")
            return {'aqi': None, 'pollutants': [], 'source': 'openaq', 'error': str(e)}
    
    def _get_mock_weather_data(self, location_data):
        """Return mock weather data for development/testing."""
        location_name = location_data.get('city') or location_data.get('location') or 'Nairobi'
        
        # Generate some realistic-looking mock data
        import random
        from datetime import datetime
        
        base_temp = 22.0  # Base temperature for Nairobi
        hour = datetime.now().hour
        # Temperature varies by time of day
        if 2 <= hour < 6:  # Early morning
            temp_variation = -4
        elif 6 <= hour < 10:  # Morning
            temp_variation = -2
        elif 10 <= hour < 14:  # Midday
            temp_variation = 3
        elif 14 <= hour < 18:  # Afternoon
            temp_variation = 2
        elif 18 <= hour < 22:  # Evening
            temp_variation = -1
        else:  # Night
            temp_variation = -3
        
        temp_variation += random.uniform(-1, 1)
        
        # Weather conditions based on temperature
        if base_temp + temp_variation > 25:
            weather_main = 'Clear'
            weather_desc = 'clear sky'
        elif base_temp + temp_variation > 20:
            weather_main = random.choice(['Clear', 'Clouds'])
            weather_desc = random.choice(['clear sky', 'few clouds'])
        else:
            weather_main = random.choice(['Clouds', 'Rain'])
            weather_desc = random.choice(['broken clouds', 'scattered clouds', 'light rain'])
        
        return {
            'location': {
                'name': location_name,
                'country': 'KE',
                'latitude': -1.2921,
                'longitude': 36.8219,
            },
            'weather': {
                'main': weather_main,
                'description': weather_desc,
                'icon': '01d' if weather_main == 'Clear' else '03d',
            },
            'main': {
                'temperature': round(base_temp + temp_variation, 1),
                'feels_like': round(base_temp + temp_variation + random.uniform(-1, 2), 1),
                'pressure': 1013 + random.randint(-10, 10),
                'humidity': random.randint(40, 70),
                'temp_min': round(base_temp + temp_variation - 2, 1),
                'temp_max': round(base_temp + temp_variation + 2, 1),
            },
            'wind': {
                'speed': round(random.uniform(1, 5), 1),
                'direction': random.randint(0, 360),
            },
            'visibility': 10000 - random.randint(0, 2000) if weather_main == 'Clouds' else 10000,
            'clouds': random.randint(0, 100) if weather_main == 'Clouds' else random.randint(0, 30),
            'rain': random.uniform(0, 2) if weather_main == 'Rain' else 0,
            'snow': 0,
            'timestamp': datetime.now(),
            'source': 'mock',
            'note': 'Mock data - configure OPENWEATHER_API_KEY for real data',
            'sunrise': datetime.now().replace(hour=6, minute=30, second=0, microsecond=0),
            'sunset': datetime.now().replace(hour=18, minute=45, second=0, microsecond=0),
        }
    
    def _get_mock_air_quality(self):
        """Return mock air quality data."""
        import random
        from datetime import datetime
        
        # Generate more realistic mock data
        hour = datetime.now().hour
        # Air quality tends to be worse during rush hours
        if (7 <= hour < 9) or (17 <= hour < 19):
            pm25_base = random.uniform(20, 40)
        else:
            pm25_base = random.uniform(5, 25)
        
        pollutants = [
            {
                'parameter': 'pm25',
                'value': round(pm25_base, 1),
                'unit': 'µg/m³',
                'last_updated': datetime.now().isoformat(),
            },
            {
                'parameter': 'pm10',
                'value': round(pm25_base * 1.5, 1),
                'unit': 'µg/m³',
                'last_updated': datetime.now().isoformat(),
            },
            {
                'parameter': 'o3',
                'value': round(random.uniform(20, 60), 1),
                'unit': 'ppb',
                'last_updated': datetime.now().isoformat(),
            },
            {
                'parameter': 'no2',
                'value': round(random.uniform(10, 40), 1),
                'unit': 'ppb',
                'last_updated': datetime.now().isoformat(),
            },
        ]
        
        # Calculate AQI based on PM2.5
        pm25 = pollutants[0]['value']
        if pm25 <= 12:
            aqi = 'Good'
            aqi_numeric = 50 * (pm25 / 12)
        elif pm25 <= 35.4:
            aqi = 'Moderate'
            aqi_numeric = 50 + (50 * (pm25 - 12) / (35.4 - 12))
        elif pm25 <= 55.4:
            aqi = 'Unhealthy for Sensitive Groups'
            aqi_numeric = 100 + (50 * (pm25 - 35.4) / (55.4 - 35.4))
        elif pm25 <= 150.4:
            aqi = 'Unhealthy'
            aqi_numeric = 150 + (50 * (pm25 - 55.4) / (150.4 - 55.4))
        else:
            aqi = 'Very Unhealthy'
            aqi_numeric = 200 + (100 * (pm25 - 150.4) / (250.4 - 150.4))
        
        return {
            'aqi': aqi,
            'aqi_numeric': round(aqi_numeric, 1),
            'pollutants': pollutants,
            'location': 'Mock Location - Nairobi',
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
        logger.info(f"get_forecast called for coordinates: {latitude}, {longitude}, days: {days}")
        
        if not self.openweather_api_key:
            logger.warning("OpenWeather API key not configured for forecast")
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
            
            logger.info(f"OpenWeather forecast API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                forecast = self._parse_forecast_data(data)
                logger.info(f"Successfully fetched forecast data with {len(forecast)} entries")
                return forecast
            elif response.status_code == 401:
                logger.error("OpenWeather forecast API error: 401 Unauthorized")
                mock_forecast = self._get_mock_forecast(days)
                for item in mock_forecast:
                    item['error'] = 'API Key Invalid'
                return mock_forecast
            else:
                logger.error(f"OpenWeather forecast error: {response.status_code}")
                mock_forecast = self._get_mock_forecast(days)
                for item in mock_forecast:
                    item['error'] = f'API Error {response.status_code}'
                return mock_forecast
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching forecast: {e}")
            mock_forecast = self._get_mock_forecast(days)
            for item in mock_forecast:
                item['error'] = f'Request error: {str(e)}'
            return mock_forecast
    
    def _parse_forecast_data(self, data):
        """Parse forecast data from OpenWeather."""
        forecast_list = []
        
        for item in data.get('list', []):
            try:
                forecast = {
                    'timestamp': datetime.fromtimestamp(item.get('dt')),
                    'temperature': item.get('main', {}).get('temp'),
                    'feels_like': item.get('main', {}).get('feels_like'),
                    'humidity': item.get('main', {}).get('humidity'),
                    'pressure': item.get('main', {}).get('pressure'),
                    'weather': item.get('weather', [{}])[0].get('main'),
                    'description': item.get('weather', [{}])[0].get('description'),
                    'icon': item.get('weather', [{}])[0].get('icon'),
                    'wind_speed': item.get('wind', {}).get('speed'),
                    'wind_direction': item.get('wind', {}).get('deg'),
                    'rain': item.get('rain', {}).get('3h', 0),
                    'snow': item.get('snow', {}).get('3h', 0),
                    'clouds': item.get('clouds', {}).get('all'),
                    'source': 'openweathermap',
                }
                forecast_list.append(forecast)
            except Exception as e:
                logger.warning(f"Error parsing forecast item: {e}")
                continue
        
        return forecast_list
    
    def _get_mock_forecast(self, days):
        """Return mock forecast data."""
        import random
        from datetime import datetime, timedelta
        
        forecast_list = []
        base_temp = 22.0
        
        for i in range(min(days * 8, 40)):  # Limit to 40 entries
            timestamp = datetime.now() + timedelta(hours=i*3)
            
            # Temperature follows a daily pattern
            hour_of_day = timestamp.hour
            if 2 <= hour_of_day < 6:
                temp_variation = -4
            elif 6 <= hour_of_day < 10:
                temp_variation = -2
            elif 10 <= hour_of_day < 14:
                temp_variation = 3
            elif 14 <= hour_of_day < 18:
                temp_variation = 2
            elif 18 <= hour_of_day < 22:
                temp_variation = -1
            else:
                temp_variation = -3
            
            temp_variation += random.uniform(-1.5, 1.5)
            
            # Weather pattern
            if base_temp + temp_variation > 25 and random.random() > 0.3:
                weather_main = 'Clear'
                weather_desc = 'clear sky'
                icon = '01d' if 6 <= hour_of_day < 18 else '01n'
            elif base_temp + temp_variation > 20:
                weather_main = random.choice(['Clear', 'Clouds'])
                weather_desc = random.choice(['clear sky', 'few clouds', 'scattered clouds'])
                icon = '02d' if 6 <= hour_of_day < 18 else '02n'
            else:
                weather_main = random.choice(['Clouds', 'Rain'])
                weather_desc = random.choice(['broken clouds', 'overcast clouds', 'light rain', 'moderate rain'])
                icon = '04d' if 6 <= hour_of_day < 18 else '04n'
            
            forecast = {
                'timestamp': timestamp,
                'temperature': round(base_temp + temp_variation, 1),
                'feels_like': round(base_temp + temp_variation + random.uniform(-1, 2), 1),
                'humidity': random.randint(40, 80),
                'pressure': 1013 + random.randint(-10, 10),
                'weather': weather_main,
                'description': weather_desc,
                'icon': icon,
                'wind_speed': round(random.uniform(1, 8), 1),
                'wind_direction': random.randint(0, 360),
                'rain': random.uniform(0, 5) if weather_main == 'Rain' else 0,
                'snow': 0,
                'clouds': random.randint(20, 100) if weather_main == 'Clouds' else random.randint(0, 30),
                'source': 'mock',
                'note': 'Mock forecast data',
            }
            forecast_list.append(forecast)
        
        return forecast_list
    
    def validate_api_key(self):
        """
        Validate the OpenWeatherMap API key.
        
        Returns:
            tuple: (is_valid, message)
        """
        if not self.openweather_api_key:
            return False, "No API key configured"
        
        try:
            # Simple test request
            test_url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': 'London',
                'appid': self.openweather_api_key,
                'units': 'metric'
            }
            
            response = requests.get(test_url, params=params, timeout=10)
            
            if response.status_code == 200:
                return True, "API key is valid"
            elif response.status_code == 401:
                return False, "API key is invalid or not activated"
            elif response.status_code == 429:
                return False, "API rate limit exceeded"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {str(e)}"