"""
Django management command to generate monthly climate aggregates.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg, Max, Min, Sum
import logging

from climate.models import ClimateData, Region, MonthlyClimate

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate monthly aggregated climate data from daily records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=12,
            help='Number of past months to process (default: 12)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if monthly data exists'
        )
        parser.add_argument(
            '--region',
            type=str,
            help='Process specific region only'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Generating monthly climate aggregates...'))
        
        # Get regions to process
        if options['region']:
            regions = Region.objects.filter(name__icontains=options['region'])
        else:
            regions = Region.objects.all()
        
        months_to_process = options['months']
        force = options['force']
        
        self.stdout.write(f'Processing {regions.count()} regions for past {months_to_process} months...')
        
        total_created = 0
        total_updated = 0
        
        for region in regions:
            try:
                self.stdout.write(f'\nProcessing {region.name}...')
                
                # Process each of the last N months
                for month_offset in range(months_to_process):
                    # Calculate month start and end
                    today = timezone.now()
                    target_month = today.month - month_offset
                    target_year = today.year
                    
                    # Handle year rollover
                    while target_month < 1:
                        target_month += 12
                        target_year -= 1
                    
                    # Get first and last day of month
                    import calendar
                    last_day = calendar.monthrange(target_year, target_month)[1]
                    
                    month_start = datetime(target_year, target_month, 1).date()
                    month_end = datetime(target_year, target_month, last_day).date()
                    
                    # Check if monthly data already exists
                    existing_monthly = MonthlyClimate.objects.filter(
                        region=region,
                        year=target_year,
                        month=target_month
                    ).first()
                    
                    if existing_monthly and not force:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Skipping {target_year}-{target_month:02d}: already exists'
                            )
                        )
                        continue
                    
                    # Get all climate data for this month
                    monthly_data = ClimateData.objects.filter(
                        region=region,
                        timestamp__date__gte=month_start,
                        timestamp__date__lte=month_end
                    )
                    
                    if not monthly_data.exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f'  No data for {target_year}-{target_month:02d}'
                            )
                        )
                        continue
                    
                    # Calculate aggregates
                    aggregates = monthly_data.aggregate(
                        avg_temp=Avg('temperature'),
                        max_temp=Max('temperature'),
                        min_temp=Min('temperature'),
                        total_rain=Sum('rainfall'),
                        avg_humidity=Avg('humidity'),
                        avg_wind=Avg('wind_speed')
                    )
                    
                    # Create or update MonthlyClimate record
                    monthly_climate, created = MonthlyClimate.objects.update_or_create(
                        region=region,
                        year=target_year,
                        month=target_month,
                        defaults={
                            'avg_temperature': aggregates['avg_temp'] or 0,
                            'max_temperature': aggregates['max_temp'] or 0,
                            'min_temperature': aggregates['min_temp'] or 0,
                            'total_rainfall': aggregates['total_rain'] or 0,
                            'avg_humidity': aggregates['avg_humidity'] or 0,
                            'avg_wind_speed': aggregates['avg_wind'] or 0,
                        }
                    )
                    
                    if created:
                        total_created += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  Created {target_year}-{target_month:02d}: '
                                f'{monthly_climate.avg_temperature:.1f}°C'
                            )
                        )
                    else:
                        total_updated += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  Updated {target_year}-{target_month:02d}: '
                                f'{monthly_climate.avg_temperature:.1f}°C'
                            )
                        )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {region.name}: {e}')
                )
                logger.error(f'Error processing {region.name}: {e}')
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('Monthly Data Generation Complete!'))
        self.stdout.write(self.style.SUCCESS(f'Created: {total_created} monthly records'))
        self.stdout.write(self.style.SUCCESS(f'Updated: {total_updated} monthly records'))
        
        if total_created + total_updated > 0:
            self.stdout.write(self.style.SUCCESS(
                '\nNow run: python manage.py predict_monthly --generate-predictions'
            ))