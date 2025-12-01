"""
Machine Learning predictor for climate data.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from django.conf import settings


class ClimatePredictor:
    """
    Machine Learning model for predicting climate trends.
    """
    
    def __init__(self, model_path=None):
        """
        Initialize the climate predictor.
        
        Args:
            model_path: Path to saved model file. If None, uses default path.
        """
        if model_path is None:
            model_path = settings.ML_MODEL_PATH
        
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        
        # Try to load existing model
        self.load_model()
    
    def load_model(self):
        """Load trained model from disk."""
        try:
            if os.path.exists(self.model_path):
                loaded_data = joblib.load(self.model_path)
                self.model = loaded_data['model']
                self.scaler = loaded_data['scaler']
                self.feature_names = loaded_data['feature_names']
                print(f"Model loaded from {self.model_path}")
            else:
                print(f"No model found at {self.model_path}. Train a new model first.")
        except Exception as e:
            print(f"Error loading model: {e}")
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
            print(f"Model saved to {self.model_path}")
    
    def prepare_features(self, data):
        """
        Prepare features from climate data.
        
        Args:
            data: List of dictionaries with climate data
        
        Returns:
            tuple: (X_features, y_target)
        """
        if not data:
            raise ValueError("No data provided")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure required columns exist
        required_cols = ['temperature', 'timestamp']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Sort by timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
        df = df.sort_values('timestamp')
        
        # Create time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['month'] = df['timestamp'].dt.month
        
        # Create lag features (previous values)
        for lag in [1, 2, 3, 6, 12, 24]:
            df[f'temp_lag_{lag}'] = df['temperature'].shift(lag)
        
        # Rolling statistics
        df['temp_rolling_mean_6'] = df['temperature'].rolling(window=6, min_periods=1).mean()
        df['temp_rolling_std_6'] = df['temperature'].rolling(window=6, min_periods=1).std()
        
        # Add other features if available
        if 'humidity' in df.columns:
            df['humidity_lag_1'] = df['humidity'].shift(1)
        
        if 'rainfall' in df.columns:
            df['rainfall_lag_1'] = df['rainfall'].shift(1)
        
        # Drop rows with NaN values (from lag features)
        df = df.dropna()
        
        if len(df) == 0:
            raise ValueError("Not enough data for feature engineering")
        
        # Define features and target
        feature_cols = [
            'hour', 'day_of_week', 'day_of_year', 'month',
            'temp_lag_1', 'temp_lag_2', 'temp_lag_3',
            'temp_rolling_mean_6', 'temp_rolling_std_6'
        ]
        
        # Add additional features if they exist
        for col in ['humidity_lag_1', 'rainfall_lag_1']:
            if col in df.columns:
                feature_cols.append(col)
        
        # Select only available columns
        available_features = [col for col in feature_cols if col in df.columns]
        
        X = df[available_features].values
        y = df['temperature'].values
        
        self.feature_names = available_features
        
        return X, y
    
    def train(self, data, model_type='random_forest'):
        """
        Train the model on climate data.
        
        Args:
            data: List of dictionaries with climate data
            model_type: 'linear' or 'random_forest'
        
        Returns:
            dict: Training metrics
        """
        # Prepare features
        X, y = self.prepare_features(data)
        
        if len(X) < 10:
            raise ValueError(f"Not enough data for training. Need at least 10 samples, got {len(X)}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        if model_type == 'linear':
            self.model = LinearRegression()
        elif model_type == 'random_forest':
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self.model.fit(X_train_scaled, y_train)
        
        # Make predictions
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        metrics = {
            'train_mae': mean_absolute_error(y_train, y_pred_train),
            'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
            'train_r2': r2_score(y_train, y_pred_train),
            'test_mae': mean_absolute_error(y_test, y_pred_test),
            'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
            'test_r2': r2_score(y_test, y_pred_test),
            'n_samples': len(X),
            'n_features': X.shape[1],
            'model_type': model_type,
            'feature_names': self.feature_names,
        }
        
        # Save the model
        self.save_model()
        
        return metrics
    
    def predict_future(self, data, n_steps=7):
        """
        Predict future climate values.
        
        Args:
            data: Historical climate data
            n_steps: Number of steps to predict ahead
        
        Returns:
            list: Predictions for future steps
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first or load a trained model.")
        
        if self.scaler is None:
            raise ValueError("Scaler not available.")
        
        # Prepare features from historical data
        X, y = self.prepare_features(data)
        
        if len(X) == 0:
            raise ValueError("No valid data for prediction")
        
        # Get the last data point
        last_X = X[-1:]
        
        predictions = []
        
        # Generate predictions step by step
        for step in range(n_steps):
            # Scale the features
            X_scaled = self.scaler.transform(last_X)
            
            # Make prediction
            pred = self.model.predict(X_scaled)[0]
            
            # Store prediction
            predictions.append({
                'step': step + 1,
                'predicted_temperature': float(pred),
                'predicted_date': (datetime.now() + timedelta(days=step+1)).strftime('%Y-%m-%d')
            })
            
            # Update features for next prediction (simplified)
            # In a real implementation, you would properly update all lag features
            if step < n_steps - 1:
                # Create new feature vector for next prediction
                # This is a simplified approach
                new_X = last_X.copy()
                
                # Shift lag features
                for i in range(len(self.feature_names)):
                    if 'lag' in self.feature_names[i]:
                        # Simple shift for demonstration
                        pass
                
                # Update with predicted temperature
                # This would need proper feature engineering for real use
                last_X = new_X
        
        return predictions
    
    def predict_temperature_trend(self, data, future_hours=24):
        """
        Predict temperature trend for the next hours.
        
        Args:
            data: Historical climate data
            future_hours: Number of hours to predict
        
        Returns:
            dict: Predictions with confidence intervals
        """
        predictions = self.predict_future(data, n_steps=future_hours)
        
        # Calculate trend
        if len(predictions) > 1:
            first_temp = predictions[0]['predicted_temperature']
            last_temp = predictions[-1]['predicted_temperature']
            trend = 'increasing' if last_temp > first_temp else 'decreasing'
            change = abs(last_temp - first_temp)
        else:
            trend = 'stable'
            change = 0
        
        # Calculate confidence intervals (simplified)
        for pred in predictions:
            # Add some uncertainty based on prediction horizon
            uncertainty = pred['step'] * 0.5  # 0.5°C per step
            pred['temperature_lower'] = pred['predicted_temperature'] - uncertainty
            pred['temperature_upper'] = pred['predicted_temperature'] + uncertainty
        
        return {
            'predictions': predictions,
            'trend': trend,
            'trend_magnitude': change,
            'confidence': 'medium' if change > 1 else 'high',
            'model_version': 'v1.0'
        }