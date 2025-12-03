"""
Seed monthly climate data with synthetic historical data for ML training.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import random
import math

from climate.models import Region, MonthlyClimate


class Command(BaseCommand):
    help = 'Seed monthly climate data with synthetic historical data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--years',
            type=int,
            default=3,
            help='Number of years of historical data to generate (default: 3)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing monthly data'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌍 Seeding monthly climate data...'))
        
        years = options['years']
        force = options['force']
        regions = Region.objects.all()
        
        total_created = 0
        total_updated = 0
        
        for region in regions:
            self.stdout.write(f'\n📊 Generating data for {region.name}...')
            
            # Base temperature varies by region
            region_base = {
                'Nairobi': 22.0,
                'Mombasa': 27.0,
                'Kisumu': 25.0,
                'Arusha': 20.0,
                'Kampala': 23.0,
            }.get(region.name, 22.0)
            
            # Generate data for past N years
            current_year = timezone.now().year
            current_month = timezone.now().month
            
            # We'll generate data for years: current_year-2, current_year-1, current_year
            for year_offset in range(years):
                target_year = current_year - year_offset
                
                # Generate all 12 months for this year
                for month in range(1, 13):
                    # Skip future months for current year
                    if year_offset == 0 and month > current_month:
                        continue
                    
                    # Check if data already exists
                    existing = MonthlyClimate.objects.filter(
                        region=region,
                        year=target_year,
                        month=month
                    ).first()
                    
                    if existing and not force:
                        self.stdout.write(
                            self.style.WARNING(f'  Skipping {target_year}-{month:02d}: exists')
                        )
                        continue
                    
                    # Seasonal variation
                    seasonal_variation = 3 * math.sin(2 * math.pi * month / 12)
                    
                    # Random variation
                    random_variation = random.uniform(-1.5, 1.5)
                    
                    # Yearly trend (slight warming trend)
                    yearly_trend = year_offset * -0.15  # Slightly cooler in past years
                    
                    # Calculate temperature
                    temperature = region_base + seasonal_variation + random_variation + yearly_trend
                    
                    # Rainfall pattern for East Africa
                    if month in [3, 4, 5]:  # Long rains (Mar-May)
                        rainfall = random.uniform(80, 180)
                        humidity = random.uniform(75, 90)
                    elif month in [10, 11]:  # Short rains (Oct-Nov)
                        rainfall = random.uniform(40, 120)
                        humidity = random.uniform(70, 85)
                    else:
                        rainfall = random.uniform(0, 60)
                        humidity = random.uniform(60, 75)
                    
                    # Wind patterns
                    if month in [6, 7, 8]:  # Drier season
                        wind_speed = random.uniform(3, 8)
                    else:
                        wind_speed = random.uniform(2, 6)
                    
                    # Create or update
                    if existing and force:
                        existing.avg_temperature = temperature
                        existing.max_temperature = temperature + random.uniform(2, 5)
                        existing.min_temperature = temperature - random.uniform(2, 5)
                        existing.total_rainfall = rainfall
                        existing.avg_humidity = humidity
                        existing.avg_wind_speed = wind_speed
                        existing.save()
                        total_updated += 1
                        
                        self.stdout.write(
                            self.style.WARNING(f'  Updated {target_year}-{month:02d}: {temperature:.1f}°C')
                        )
                    else:
                        MonthlyClimate.objects.create(
                            region=region,
                            year=target_year,
                            month=month,
                            avg_temperature=temperature,
                            max_temperature=temperature + random.uniform(2, 5),
                            min_temperature=temperature - random.uniform(2, 5),
                            total_rainfall=rainfall,
                            avg_humidity=humidity,
                            avg_wind_speed=wind_speed,
                        )
                        total_created += 1
                        
                        if total_created % 12 == 0:
                            self.stdout.write(
                                self.style.SUCCESS(f'  Created {target_year}-{month:02d}: {temperature:.1f}°C')
                            )
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 50))
        self.stdout.write(self.style.SUCCESS('🌱 Seeding complete!'))
        self.stdout.write(self.style.SUCCESS(f'📈 Created: {total_created} monthly records'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Updated: {total_updated} monthly records'))
        
        if total_created > 0:
            self.stdout.write(self.style.SUCCESS(
                '\n🚀 Now run: python manage.py predict_monthly --train'
            ))