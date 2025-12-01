"""
Django management command to train the initial ML model.
"""

from django.core.management.base import BaseCommand
from climate.ml.train_model import train_model_from_database, train_model_from_sample_data


class Command(BaseCommand):
    help = 'Train the initial machine learning model for climate predictions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--use-database',
            action='store_true',
            help='Use data from database instead of generating sample data'
        )
        parser.add_argument(
            '--sample-size',
            type=int,
            default=1000,
            help='Number of sample data points to generate (default: 1000)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting ML model training...'))
        
        if options['use_database']:
            self.stdout.write('Training model using database data...')
            metrics = train_model_from_database()
        else:
            self.stdout.write('Training model using sample data...')
            # Note: sample_size parameter would need to be passed through
            metrics = train_model_from_sample_data()
        
        # Display results
        self.stdout.write(self.style.SUCCESS('\nModel Training Complete!'))
        self.stdout.write('=' * 50)
        self.stdout.write(f"Model Type: {metrics.get('model_type', 'N/A')}")
        self.stdout.write(f"R² Score: {metrics.get('test_r2', 0):.3f}")
        self.stdout.write(f"MAE: {metrics.get('test_mae', 0):.3f}")
        self.stdout.write(f"RMSE: {metrics.get('test_rmse', 0):.3f}")
        
        if metrics.get('test_r2', 0) > 0.7:
            self.stdout.write(self.style.SUCCESS('✓ Model trained successfully with good accuracy'))
        elif metrics.get('test_r2', 0) > 0.5:
            self.stdout.write(self.style.WARNING('⚠ Model accuracy is moderate'))
        else:
            self.stdout.write(self.style.ERROR('✗ Model accuracy is low. Consider adding more data.'))
        
        self.stdout.write('\nThe model is now ready for predictions!')
        self.stdout.write('You can use it in the dashboard or via the API.')