"""
Machine Learning predictor for MONTHLY climate trends.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from django.conf import settings


class MonthlyClimatePredictor:
    """
    ML model for predicting MONTHLY climate trends.
    """
    
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = str(settings.BASE_DIR / 'climate' / 'ml' / 'models' / 'monthly_model.joblib')
        
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        
        self.load_model()
    
    def load_model(self):
        """Load trained model from disk."""
        try:
            if os.path.exists(self.model_path):
                loaded_data = joblib.load(self.model_path)
                self.model = loaded_data['model']
                self.scaler = loaded_data['scaler']
                self.feature_names = loaded_data['feature_names']
                print(f"Monthly model loaded from {self.model_path}")
            else:
                print(f"No monthly model found at {self.model_path}")
        except Exception as e:
            print(f"Error loading monthly model: {e}")
            self.model = None
    
    def save_model(self):
        """Save trained model to disk."""
        if self.model is not None:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'timestamp': datetime.now()
            }
            
            joblib.dump(model_data, self.model_path)
            print(f"Monthly model saved to {self.model_path}")
    
    def prepare_features(self, monthly_data):
        """
        Prepare features from monthly climate data.
        """
        if not monthly_data:
            raise ValueError("No monthly data provided")
        
        df = pd.DataFrame(monthly_data)
        
        # Ensure required columns
        required_cols = ['month', 'avg_temperature', 'total_rainfall']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Sort by year and month
        df = df.sort_values(['year', 'month'])
        
        # Create seasonal features
        df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
        df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Create lag features (previous months)
        for lag in [1, 2, 3, 6, 12]:
            df[f'temp_lag_{lag}'] = df['avg_temperature'].shift(lag)
            df[f'rain_lag_{lag}'] = df['total_rainfall'].shift(lag)
        
        # Rolling statistics
        df['temp_rolling_mean_3'] = df['avg_temperature'].rolling(window=3, min_periods=1).mean()
        df['temp_rolling_std_3'] = df['avg_temperature'].rolling(window=3, min_periods=1).std()
        
        # Year-over-year features
        df['temp_prev_year'] = df['avg_temperature'].shift(12)
        df['rain_prev_year'] = df['total_rainfall'].shift(12)
        
        # Drop NaN
        df = df.dropna()
        
        if len(df) == 0:
            raise ValueError("Not enough data for feature engineering")
        
        # Define features and target
        feature_cols = [
            'month', 'sin_month', 'cos_month',
            'temp_lag_1', 'temp_lag_2', 'temp_lag_3',
            'temp_rolling_mean_3', 'temp_rolling_std_3',
            'temp_prev_year'
        ]
        
        # Add rain features if available
        if 'rain_lag_1' in df.columns:
            feature_cols.extend(['rain_lag_1', 'rain_prev_year'])
        
        # Add region features if available
        if 'region_id' in df.columns:
            feature_cols.append('region_id')
        
        available_features = [col for col in feature_cols if col in df.columns]
        
        X = df[available_features].values
        y = df['avg_temperature'].values
        
        self.feature_names = available_features
        
        return X, y, df[['year', 'month']].values
    
    def train(self, monthly_data):
        """
        Train the model on monthly climate data.
        """
        X, y, _ = self.prepare_features(monthly_data)
        
        if len(X) < 12:  # Need at least 12 months of data
            raise ValueError(f"Need at least 12 months of data, got {len(X)}")
        
        # Split data (80% train, 20% test)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            random_state=42,
            n_jobs=-1,
            min_samples_split=5,
            min_samples_leaf=2
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Predictions and metrics
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        metrics = {
            'train_mae': mean_absolute_error(y_train, y_pred_train),
            'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
            'train_r2': r2_score(y_train, y_pred_train),
            'test_mae': mean_absolute_error(y_test, y_pred_test),
            'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
            'test_r2': r2_score(y_test, y_pred_test),
            'n_samples': len(X),
            'n_features': X.shape[1],
            'model_type': 'random_forest_monthly',
            'feature_names': self.feature_names,
        }
        
        self.save_model()
        
        return metrics
    
    def predict_next_12_months(self, historical_monthly_data, region_id=None):
        """
        Predict next 12 months of temperatures.
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Prepare features from historical data
        X_historical, _, months = self.prepare_features(historical_monthly_data)
        
        if len(X_historical) < 12:
            raise ValueError(f"Need at least 12 months of historical data, got {len(X_historical)}")
        
        # Get the last data point
        last_X = X_historical[-1:]
        
        predictions = []
        
        # Generate predictions for next 12 months
        for month_offset in range(1, 13):
            # Scale features
            X_scaled = self.scaler.transform(last_X)
            
            # Make prediction
            pred_temp = self.model.predict(X_scaled)[0]
            
            # Add some randomness for realism
            if month_offset <= 3:
                uncertainty = 0.5  # Lower uncertainty for near future
            elif month_offset <= 6:
                uncertainty = 1.0
            else:
                uncertainty = 1.5
            
            # Calculate confidence (decreases with time)
            confidence = max(0.5, 1.0 - (month_offset * 0.04))
            
            # Calculate date
            today = datetime.now()
            month = (today.month + month_offset - 1) % 12 + 1
            year = today.year + (today.month + month_offset - 1) // 12
            
            predictions.append({
                'year': year,
                'month': month,
                'predicted_temperature': float(pred_temp),
                'predicted_rainfall': 0,  # Could add rainfall prediction too
                'confidence': float(confidence * 100),
                'temperature_lower': float(pred_temp - uncertainty),
                'temperature_upper': float(pred_temp + uncertainty),
                'month_name': datetime(year, month, 1).strftime('%b')
            })
            
            # Update features for next prediction (simplified)
            if month_offset < 12:
                last_X = last_X.copy()
                # Update month feature
                last_X[0][0] = month  # Update month value
                last_X[0][1] = np.sin(2 * np.pi * month / 12)  # Update sin
                last_X[0][2] = np.cos(2 * np.pi * month / 12)  # Update cos
        
        return predictions