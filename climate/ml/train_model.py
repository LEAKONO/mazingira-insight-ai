"""
Script to train the climate prediction model.
"""

import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climate_dashboard.settings')
django.setup()

from climate.models import ClimateData, Region
from climate.ml.predictor import ClimatePredictor


def generate_sample_data(num_samples=1000):
    """
    Generate sample climate data for training.
    
    Args:
        num_samples: Number of samples to generate
    
    Returns:
        list: Sample climate data
    """
    print(f"Generating {num_samples} sample data points...")
    
    # Create or get a sample region
    region, created = Region.objects.get_or_create(
        name='Nairobi',
        defaults={
            'country': 'Kenya',
            'climate_zone': 'Tropical',
            'population': 5000000
        }
    )
    
    # Generate synthetic climate data
    sample_data = []
    base_date = datetime.now() - timedelta(days=365)
    
    for i in range(num_samples):
        timestamp = base_date + timedelta(hours=i)
        
        # Generate realistic temperature data (seasonal pattern)
        hour_of_day = timestamp.hour
        day_of_year = timestamp.timetuple().tm_yday
        
        # Base temperature with seasonal variation
        seasonal_variation = 5 * np.sin(2 * np.pi * day_of_year / 365)
        daily_variation = 8 * np.sin(2 * np.pi * hour_of_day / 24)
        noise = random.uniform(-2, 2)
        
        temperature = 22 + seasonal_variation + daily_variation + noise
        
        # Other weather parameters
        humidity = 50 + 20 * np.sin(2 * np.pi * hour_of_day / 24) + random.uniform(-10, 10)
        rainfall = random.expovariate(0.1) if random.random() < 0.1 else 0  # 10% chance of rain
        
        # Create ClimateData object
        climate_data = {
            'timestamp': timestamp.timestamp(),
            'temperature': float(temperature),
            'humidity': float(humidity),
            'rainfall': float(rainfall),
            'wind_speed': random.uniform(1, 10),
            'pressure': 1013 + random.uniform(-10, 10),
        }
        
        sample_data.append(climate_data)
        
        # Also save to database
        if i % 100 == 0:  # Save every 100th sample
            ClimateData.objects.create(
                region=region,
                timestamp=timestamp,
                temperature=temperature,
                humidity=humidity,
                rainfall=rainfall,
                wind_speed=random.uniform(1, 10),
                source='synthetic'
            )
    
    print(f"Generated {len(sample_data)} sample data points")
    return sample_data


def train_model_from_sample_data():
    """Train the model using sample data."""
    print("Training climate prediction model...")
    
    # Generate or load sample data
    sample_data = generate_sample_data(500)
    
    # Initialize predictor
    predictor = ClimatePredictor()
    
    # Train the model
    print("Training model...")
    metrics = predictor.train(sample_data, model_type='random_forest')
    
    # Print training results
    print("\nTraining Results:")
    print("=" * 50)
    print(f"Model Type: {metrics['model_type']}")
    print(f"Number of Samples: {metrics['n_samples']}")
    print(f"Number of Features: {metrics['n_features']}")
    print(f"\nTraining Metrics:")
    print(f"  MAE: {metrics['train_mae']:.3f}")
    print(f"  RMSE: {metrics['train_rmse']:.3f}")
    print(f"  R²: {metrics['train_r2']:.3f}")
    print(f"\nTest Metrics:")
    print(f"  MAE: {metrics['test_mae']:.3f}")
    print(f"  RMSE: {metrics['test_rmse']:.3f}")
    print(f"  R²: {metrics['test_r2']:.3f}")
    
    # Test prediction
    print("\nTesting prediction...")
    test_data = sample_data[-100:]  # Use last 100 points for testing
    try:
        predictions = predictor.predict_future(test_data, n_steps=7)
        print(f"Generated {len(predictions)} predictions")
        for pred in predictions:
            print(f"  Day {pred['step']}: {pred['predicted_temperature']:.1f}°C")
    except Exception as e:
        print(f"Prediction test failed: {e}")
    
    return metrics


def train_model_from_database():
    """Train the model using data from the database."""
    print("Training model from database data...")
    
    # Get data from database
    climate_data = ClimateData.objects.all().order_by('timestamp')
    
    if climate_data.count() < 100:
        print(f"Not enough data in database ({climate_data.count()} records).")
        print("Generating sample data and training...")
        return train_model_from_sample_data()
    
    # Prepare data for training
    training_data = []
    for data in climate_data:
        training_data.append({
            'timestamp': data.timestamp.timestamp(),
            'temperature': float(data.temperature),
            'humidity': float(data.humidity) if data.humidity else 50.0,
            'rainfall': float(data.rainfall),
        })
    
    print(f"Loaded {len(training_data)} records from database")
    
    # Initialize predictor
    predictor = ClimatePredictor()
    
    # Train the model
    print("Training model...")
    metrics = predictor.train(training_data, model_type='random_forest')
    
    # Print results
    print("\nTraining Results (Database):")
    print("=" * 50)
    print(f"MAE: {metrics['test_mae']:.3f}")
    print(f"RMSE: {metrics['test_rmse']:.3f}")
    print(f"R²: {metrics['test_r2']:.3f}")
    
    return metrics


if __name__ == '__main__':
    print("Climate Model Training Script")
    print("=" * 50)
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--database':
        metrics = train_model_from_database()
    else:
        metrics = train_model_from_sample_data()
    
    print("\nModel training completed!")