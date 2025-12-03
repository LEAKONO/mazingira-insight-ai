"""
Django management command to generate monthly predictions.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from climate.models import MonthlyClimate, Region
from climate.ml.monthly_predictor import MonthlyClimatePredictor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate monthly climate predictions for all regions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--generate-monthly',
            action='store_true',
            help='Generate monthly aggregates before prediction'
        )
        parser.add_argument(
            '--train',
            action='store_true',
            help='Train model before prediction'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting monthly climate predictions...'))
        
        # Optionally generate monthly data first
        if options['generate_monthly']:
            from django.core import management
            management.call_command('generate_monthly_data', months=24)
        
        # Initialize predictor
        predictor = MonthlyClimatePredictor()
        
        # Train model if requested or if no model exists
        if options['train'] or predictor.model is None:
            self.stdout.write('Training monthly prediction model...')
            
            # Get all monthly data for training
            monthly_data = list(MonthlyClimate.objects.filter(
                avg_temperature__isnull=False
            ).values('region_id', 'year', 'month', 'avg_temperature', 'total_rainfall'))
            
            if len(monthly_data) < 24:
                self.stdout.write(self.style.WARNING(
                    f'Not enough monthly data ({len(monthly_data)} records). '
                    f'Need at least 24 months.'
                ))
                if options['generate_monthly']:
                    self.stdout.write('Try running: python manage.py generate_monthly_data --months=24')
                return
            
            # Train model
            try:
                metrics = predictor.train(monthly_data)
                
                self.stdout.write(self.style.SUCCESS('\nMonthly Model Training Complete!'))
                self.stdout.write('=' * 50)
                self.stdout.write(f"Model Type: {metrics['model_type']}")
                self.stdout.write(f"R² Score: {metrics['test_r2']:.3f}")
                self.stdout.write(f"MAE: {metrics['test_mae']:.3f}°C")
                self.stdout.write(f"RMSE: {metrics['test_rmse']:.3f}°C")
                
                if metrics['test_r2'] > 0.7:
                    self.stdout.write(self.style.SUCCESS('✓ Excellent model accuracy'))
                elif metrics['test_r2'] > 0.5:
                    self.stdout.write(self.style.WARNING('⚠ Good model accuracy'))
                else:
                    self.stdout.write(self.style.ERROR('✗ Low model accuracy'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error training model: {e}'))
                return
        
        # Generate predictions for each region
        regions = Region.objects.all()
        
        self.stdout.write(f'\nGenerating predictions for {regions.count()} regions...')
        
        for region in regions:
            try:
                self.stdout.write(f'\n{region.name}:')
                
                # Get historical monthly data for this region
                historical_data = list(MonthlyClimate.objects.filter(
                    region=region,
                    avg_temperature__isnull=False
                ).order_by('year', 'month').values(
                    'year', 'month', 'avg_temperature', 'total_rainfall'
                ))
                
                if len(historical_data) < 12:
                    self.stdout.write(self.style.WARNING(
                        f'  Need at least 12 months of data, got {len(historical_data)}'
                    ))
                    continue
                
                # Add region_id to data
                for data in historical_data:
                    data['region_id'] = region.id
                
                # Generate predictions
                try:
                    predictions = predictor.predict_next_12_months(historical_data, region.id)
                    
                    # Save predictions to MonthlyClimate model
                    for pred in predictions:
                        monthly_climate, created = MonthlyClimate.objects.update_or_create(
                            region=region,
                            year=pred['year'],
                            month=pred['month'],
                            defaults={
                                'predicted_temperature': pred['predicted_temperature'],
                                'predicted_rainfall': pred['predicted_rainfall'],
                                'prediction_confidence': pred['confidence'],
                            }
                        )
                    
                    # Display first few predictions
                    self.stdout.write(self.style.SUCCESS('  Next 12 months:'))
                    for pred in predictions[:6]:  # Show first 6 months
                        self.stdout.write(f"    {pred['month_name']} {pred['year']}: "
                                        f"{pred['predicted_temperature']:.1f}°C "
                                        f"(±{pred['temperature_upper'] - pred['predicted_temperature']:.1f}°C)")
                    
                    if len(predictions) > 6:
                        self.stdout.write(f"    ... and {len(predictions) - 6} more months")
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Prediction error: {e}'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing {region.name}: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('Monthly predictions complete!'))
        self.stdout.write('\nNow run the server to see the new monthly trends dashboard.')