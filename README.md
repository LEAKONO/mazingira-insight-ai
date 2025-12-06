# Mazingira Insight AI

A Django-based climate monitoring platform that provides real-time climate data, predictions, carbon footprint calculation, and geospatial visualization.

## Features
- Real-time climate data monitoring from OpenWeatherMap & OpenAQ
- Machine Learning predictions for temperature trends
- Carbon footprint calculator with personalized suggestions
- Interactive Leaflet maps with climate data visualization
- Historical climate data tracking
- REST API for integrations
- Multi-language support (Swahili/English)

## Quick Start (Development)

### Prerequisites
- Python 3.10+
- PostgreSQL (for production) or SQLite (for development)
- Git

### Installation

1. **Clone and setup environment**
```bash
git clone https://github.com/LEAKONO/mazingira-insight-ai
cd mazingira-insight-ai
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### Install dependencies
```bash
   pip install -r requirements.txt
```

### Configure environment

```bash
 cp .env.example .env
# Edit .env with your configuration
```

### Setup database

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data  # Load sample data
python manage.py train_initial_model  # Train ML model
```
### Run development server

```bash
   python manage.py runserver
```
## Data Fetching (Background Task)
To fetch real weather data periodically:



```bash
  # Run once to test
python manage.py fetch_weather

# For production (add to cron):
# */30 * * * * cd /path/to/project && python manage.py fetch_weather
```
## Machine Learning


#### Training the model
```bash
  python manage.py train_initial_model
# Or manually:
python climate/ml/train_model.py
```

### Using predictions
The model is automatically loaded in views. Sample training data: climate/data/sample_climate_data.csv

### API Endpoints

- GET /api/weather/?location=Nairobi - Current weather data

- POST /api/predict-temperature/ - Predict temperature trends

- GET /api/regions/ - Region data in GeoJSON

- POST /api/report/ - Submit environmental reports

## Deployment
#### Render.com
1. Create new Web Service

2. Connect your repository

3. Set build command: pip install -r requirements.txt

4. Set start command: gunicorn climate_dashboard.wsgi:application

5 .Add environment variables

6 .Add PostgreSQL database

## Environment Variables
Required variables:

- SECRET_KEY - Django secret key

- DEBUG - Set to False in production

- DATABASE_URL - PostgreSQL connection string

- OPENWEATHER_API_KEY - From openweathermap.org

- OPENAIR_API_KEY - From openaq.org (optional)


## Testing
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test climate

# Run with coverage
coverage run manage.py test
coverage report
```
## License
MIT License - See LICENSE file for details.

### Acknowledgments
- OpenWeatherMap for climate data

- OpenAQ for air quality data

- Leaflet.js for mapping

- Bootstrap for UI components
