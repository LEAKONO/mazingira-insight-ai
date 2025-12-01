"""
Signals for the climate application.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import logging

from .models import ClimateData, Prediction, EnvironmentalReport

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ClimateData)
def create_prediction_on_new_data(sender, instance, created, **kwargs):
    """
    Create or update predictions when new climate data is added.
    """
    if created:
        try:
            region = instance.region
            
            # Check if we have enough data for predictions
            recent_data = ClimateData.objects.filter(
                region=region,
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            if recent_data >= 24:  # At least 24 data points in last 7 days
                # Import here to avoid circular imports
                from .ml.predictor import ClimatePredictor
                
                try:
                    predictor = ClimatePredictor()
                    
                    # Get historical data for the region
                    historical_data = ClimateData.objects.filter(
                        region=region
                    ).order_by('-timestamp')[:100]
                    
                    if len(historical_data) >= 10:
                        # Prepare data for prediction
                        prediction_data = [
                            {
                                'timestamp': d.timestamp.timestamp(),
                                'temperature': float(d.temperature),
                                'rainfall': float(d.rainfall),
                                'humidity': float(d.humidity)
                            }
                            for d in historical_data
                        ]
                        
                        # Make predictions for next 3 days
                        predictions = predictor.predict_future(prediction_data, n_steps=3)
                        
                        # Save predictions
                        for i, pred in enumerate(predictions):
                            prediction_date = timezone.now() + timedelta(days=i+1)
                            
                            Prediction.objects.update_or_create(
                                region=region,
                                prediction_date=prediction_date.date(),
                                defaults={
                                    'predicted_temperature': pred.get('predicted_temperature', 0),
                                    'predicted_rainfall': pred.get('predicted_rainfall', 0),
                                    'model_version': 'v1.0'
                                }
                            )
                        
                        logger.info(f'Created predictions for {region.name}')
                        
                except Exception as e:
                    logger.error(f'Error creating prediction for {region.name}: {e}')
        
        except Exception as e:
            logger.error(f'Error in prediction signal: {e}')


@receiver(pre_save, sender=EnvironmentalReport)
def validate_report_location(sender, instance, **kwargs):
    """
    Validate and adjust report location before saving.
    """
    if instance.latitude and instance.longitude:
        # Ensure coordinates are within reasonable bounds for East Africa
        # East Africa roughly: Lat: -12 to 5, Lon: 29 to 42
        
        # Latitude bounds (South to North)
        if instance.latitude < -12 or instance.latitude > 5:
            logger.warning(f'Report latitude {instance.latitude} outside East Africa bounds')
            # Adjust to nearest bound
            instance.latitude = max(-12, min(5, instance.latitude))
        
        # Longitude bounds (West to East)
        if instance.longitude < 29 or instance.longitude > 42:
            logger.warning(f'Report longitude {instance.longitude} outside East Africa bounds')
            # Adjust to nearest bound
            instance.longitude = max(29, min(42, instance.longitude))
    
    elif instance.region and instance.region.location:
        # If no coordinates provided, use region coordinates
        instance.latitude = instance.region.location.y
        instance.longitude = instance.region.location.x
        logger.info(f'Set report coordinates from region: {instance.region.name}')


@receiver(post_save, sender=EnvironmentalReport)
def notify_on_report_status_change(sender, instance, created, **kwargs):
    """
    Send notifications when report status changes.
    """
    if not created:
        try:
            # Check if status changed
            old_instance = EnvironmentalReport.objects.get(id=instance.id)
            
            if old_instance.status != instance.status:
                # Status changed - could send email notification here
                logger.info(f'Report {instance.id} status changed from {old_instance.status} to {instance.status}')
        
        except EnvironmentalReport.DoesNotExist:
            pass  # New instance, no old status to compare
        except Exception as e:
            logger.error(f'Error in report status change notification: {e}')


@receiver(post_save, sender=ClimateData)
def update_region_statistics(sender, instance, created, **kwargs):
    """
    Update region statistics when new climate data is added.
    """
    if created:
        try:
            region = instance.region
            logger.debug(f'New climate data for {region.name}: {instance.temperature}°C')
            
        except Exception as e:
            logger.error(f'Error updating region statistics: {e}')