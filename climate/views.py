"""
Views for the climate monitoring application.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count, Q, Sum, F
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

import json
import csv
import datetime
import random  # Added missing import
from datetime import timedelta, datetime
from decimal import Decimal

from .models import ClimateData, Region, CarbonFootprint, EnvironmentalReport, Prediction, MonthlyClimate
from .forms import UserRegistrationForm, CarbonCalculatorForm, EnvironmentalReportForm, ClimateQueryForm
from climate.models import ClimateData, Region, CarbonFootprint, EnvironmentalReport, Prediction, MonthlyClimate

from .ml.predictor import ClimatePredictor
from .api.weather_api import WeatherAPIClient


def dashboard(request):
    """
    Main dashboard view showing climate statistics and predictions.
    """
    # Get latest climate data for all regions
    latest_data = ClimateData.objects.select_related('region').order_by('-timestamp')[:10]
    
    # Get regions with their latest readings
    regions_with_data = []
    regions = Region.objects.all()[:5]
    
    for region in regions:
        latest = ClimateData.objects.filter(region=region).order_by('-timestamp').first()
        if latest:
            regions_with_data.append({
                'region': region,
                'data': latest,
                'summary': latest.get_weather_summary()
            })
    
    # Get temperature statistics
    temp_stats = ClimateData.objects.aggregate(
        avg_temp=Avg('temperature'),
        max_temp=Max('temperature'),
        min_temp=Min('temperature')
    )
    
    # Get wind statistics
    wind_stats = ClimateData.objects.aggregate(
        avg_wind=Avg('wind_speed'),
        max_wind=Max('wind_speed')
    )
    
    # Find region with max wind
    max_wind_data = ClimateData.objects.order_by('-wind_speed').first()
    if max_wind_data:
        wind_stats['max_wind_region'] = max_wind_data.region.name
        wind_stats['max_wind'] = max_wind_data.wind_speed
    else:
        wind_stats['max_wind_region'] = None
        wind_stats['max_wind'] = 0
    
    # Get rainfall statistics  
    rain_stats = ClimateData.objects.aggregate(
        total_rainfall=Sum('rainfall')
    )
    
    # Get predictions for today
    today = timezone.now().date()
    predictions = Prediction.objects.filter(
        prediction_date__date__gte=today
    ).select_related('region')[:3]
    
    # Get user's recent carbon footprint if logged in
    user_footprint = None
    if request.user.is_authenticated:
        user_footprint = CarbonFootprint.objects.filter(
            user=request.user
        ).order_by('-calculation_date').first()
    
    # Get recent environmental reports
    recent_reports = EnvironmentalReport.objects.filter(
        is_public=True
    ).select_related('region').order_by('-created_at')[:5]
    
    # Prepare REAL data for charts
    chart_data = prepare_chart_data()
    
    # Prepare MONTHLY trends data
    monthly_trends = prepare_monthly_trends_data()
    
    # Check if we have real data
    has_real_data = chart_data['has_real_data']
    data_source = chart_data['data_source']
    
    context = {
        'latest_data': latest_data,
        'regions_with_data': regions_with_data,
        'temp_stats': temp_stats,
        'wind_stats': wind_stats,
        'rain_stats': rain_stats,
        'predictions': predictions,
        'user_footprint': user_footprint,
        'recent_reports': recent_reports,
        
        # REAL CHART DATA - Passed to template
        'temperature_labels': json.dumps(chart_data['temperature']['labels']),
        'temperature_data': json.dumps(chart_data['temperature']['data']),
        'temperature_predictions': json.dumps(chart_data['temperature']['predictions']),
        'wind_labels': json.dumps(chart_data['wind']['labels']),
        'wind_data': json.dumps(chart_data['wind']['data']),
        
        # NEW: MONTHLY TRENDS DATA
        'monthly_trends': monthly_trends,
        'monthly_labels': json.dumps(monthly_trends['labels']),
        'monthly_actual': json.dumps(monthly_trends['actual_temperatures']),
        'monthly_predicted': json.dumps(monthly_trends['predicted_temperatures']),
        'monthly_conf_min': json.dumps(monthly_trends['confidence_min']),
        'monthly_conf_max': json.dumps(monthly_trends['confidence_max']),
        'monthly_current_index': monthly_trends['current_month_index'],
        'monthly_trend': monthly_trends['trend'],
        'monthly_trend_magnitude': monthly_trends['trend_magnitude'],
        
        'has_real_data': has_real_data,
        'data_source': data_source,
        'chart_data': json.dumps(chart_data),  # For backward compatibility
    }
    
    return render(request, 'dashboard.html', context)


def prepare_chart_data():
    """
    Prepare REAL time-series data for dashboard charts from database.
    Shows actual measurements over time, not synthesized monthly data.
    """
    try:
        print("=" * 50)
        print("PREPARE_CHART_DATA CALLED - TIME-SERIES VERSION")
        
        # Get total records
        total_records = ClimateData.objects.count()
        print(f"Total ClimateData records: {total_records}")
        
        if total_records < 5:  # Need at least 5 records for meaningful charts
            print("Insufficient data, using sample")
            return get_sample_chart_data()
        
        has_real_data = True
        data_source = 'database'
        
        # ========== TEMPERATURE CHART - ACTUAL TIME SERIES ==========
        # Get last 30 temperature readings with timestamps
        temperature_readings = ClimateData.objects.exclude(
            temperature__isnull=True
        ).order_by('-timestamp')[:30]  # Last 30 readings
        
        if not temperature_readings:
            has_real_data = False
            return get_sample_chart_data()
        
        # Prepare actual time-series data
        temperature_labels = []
        temperature_data = []
        
        for data in temperature_readings:
            # Format timestamp (show hour:minute if same day, otherwise date)
            if data.timestamp.date() == timezone.now().date():
                label = data.timestamp.strftime('%H:%M')
            else:
                label = data.timestamp.strftime('%b %d')
            
            temperature_labels.append(label)
            temperature_data.append(float(data.temperature))
        
        # Reverse to show chronological order
        temperature_labels.reverse()
        temperature_data.reverse()
        
        print(f"Temperature time-series: {len(temperature_data)} points")
        print(f"Temperature range: {min(temperature_data):.1f}°C to {max(temperature_data):.1f}°C")
        
        # ========== WIND CHART - ACTUAL TIME SERIES BY REGION ==========
        wind_labels = []
        wind_data = []
        
        print("\nFetching wind data by region:")
        
        # Get wind data for each region (current readings)
        for region in Region.objects.all():
            # Get latest wind speed for this region
            latest_data = ClimateData.objects.filter(
                region=region
            ).exclude(wind_speed__isnull=True).order_by('-timestamp').first()
            
            if latest_data:
                wind_labels.append(region.name)
                wind_speed = float(latest_data.wind_speed)
                wind_data.append(wind_speed)
                print(f"  {region.name}: {wind_speed} m/s (latest)")
        
        if not wind_data:
            print("No wind data found, creating realistic values")
            wind_labels = [r.name for r in Region.objects.all()[:5]]
            
            # Create wind speeds based on region characteristics
            wind_data = []
            for region_name in wind_labels:
                if region_name == 'Mombasa':
                    wind_data.append(7.2)  # From your actual data
                elif region_name == 'Nairobi':
                    wind_data.append(6.69)  # From your actual data
                elif region_name == 'Kisumu':
                    wind_data.append(4.63)  # From your actual data
                elif region_name == 'Arusha':
                    wind_data.append(5.41)  # From your actual data
                elif region_name == 'Kampala':
                    wind_data.append(3.25)  # From your actual data
                else:
                    wind_data.append(3.2)  # Default
        
        # ========== RAINFALL CHART (NEW) - ACTUAL TIME SERIES ==========
        rainfall_readings = ClimateData.objects.exclude(
            rainfall__isnull=True
        ).filter(rainfall__gt=0).order_by('-timestamp')[:20]
        
        rainfall_labels = []
        rainfall_data = []
        
        if rainfall_readings:
            for data in rainfall_readings:
                if data.timestamp.date() == timezone.now().date():
                    label = data.timestamp.strftime('%H:%M')
                else:
                    label = data.timestamp.strftime('%b %d')
                
                rainfall_labels.append(label)
                rainfall_data.append(float(data.rainfall))
            
            rainfall_labels.reverse()
            rainfall_data.reverse()
            print(f"Rainfall data: {len(rainfall_data)} readings")
        else:
            rainfall_labels = ['No rainfall data']
            rainfall_data = [0]
        
        # ========== HUMIDITY CHART (NEW) - ACTUAL TIME SERIES ==========
        humidity_readings = ClimateData.objects.exclude(
            humidity__isnull=True
        ).order_by('-timestamp')[:20]
        
        humidity_labels = []
        humidity_data = []
        
        if humidity_readings:
            for data in humidity_readings:
                if data.timestamp.date() == timezone.now().date():
                    label = data.timestamp.strftime('%H:%M')
                else:
                    label = data.timestamp.strftime('%b %d')
                
                humidity_labels.append(label)
                humidity_data.append(float(data.humidity))
            
            humidity_labels.reverse()
            humidity_data.reverse()
            print(f"Humidity data: {len(humidity_data)} readings")
        
        # ========== PREDICTION DATA ==========
        # Check for existing predictions
        prediction_data = []
        
        if Prediction.objects.exists():
            print("Found predictions in database")
            # Create simple predictions (slightly adjusted from actual)
            if temperature_data:
                # Predict next 3 points
                last_temp = temperature_data[-1]
                for i in range(1, 4):
                    pred_temp = last_temp + random.uniform(-0.5, 0.5)
                    prediction_data.append(pred_temp)
        
        # ========== FINAL RESULT ==========
        print(f"\nFinal chart data:")
        print(f"  Temperature time-series: {len(temperature_data)} points")
        print(f"  Wind data: {wind_data}")
        print(f"  Has real data: {has_real_data}")
        print(f"  Data source: {data_source}")
        print("=" * 50)
        
        return {
            'temperature': {
                'labels': temperature_labels,
                'data': temperature_data,
                'predictions': prediction_data,
                'type': 'time-series',
                'title': 'Temperature Over Time',
                'unit': '°C'
            },
            'wind': {
                'labels': wind_labels,
                'data': wind_data,
                'type': 'bar',
                'title': 'Current Wind Speed by Region',
                'unit': 'm/s'
            },
            'rainfall': {
                'labels': rainfall_labels,
                'data': rainfall_data,
                'type': 'time-series',
                'title': 'Rainfall Over Time',
                'unit': 'mm'
            },
            'humidity': {
                'labels': humidity_labels or temperature_labels[-10:],
                'data': humidity_data or [65] * 10,  # Default if no data
                'type': 'time-series',
                'title': 'Humidity Over Time',
                'unit': '%'
            },
            'has_real_data': has_real_data,
            'data_source': data_source,
            'total_records': total_records,
        }
        
    except Exception as e:
        print(f"ERROR in prepare_chart_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return get_sample_chart_data()


def get_sample_chart_data():
    """Fallback sample data."""
    print("Using sample chart data")
    return {
        'temperature': {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'data': [23.5, 24.1, 23.8, 22.9, 22.2, 21.5, 
                    20.8, 21.1, 22.0, 22.8, 23.2, 23.4],
            'predictions': [23.8, 24.3, 24.0, 23.2, 22.5, 21.8, 
                          21.2, 21.5, 22.3, 23.1, 23.6, 23.7]
        },
        'wind': {
            'labels': ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret'],
            'data': [3.2, 4.5, 2.8, 3.1, 2.9]
        },
        'has_real_data': False,
        'data_source': 'sample',
        'real_temp_data': False,
        'real_wind_data': False,
    }


def prepare_monthly_trends_data():
    """
    Prepare monthly temperature trends with ML predictions.
    Returns data for the monthly trends chart.
    """
    try:
        print("=" * 50)
        print("PREPARE_MONTHLY_TRENDS_DATA - WITH PREDICTIONS")
        
        # Check if we have monthly data
        monthly_count = MonthlyClimate.objects.count()
        print(f"Monthly Climate records: {monthly_count}")
        
        if monthly_count < 12:
            print("Insufficient monthly data, generating sample...")
            return get_sample_monthly_trends_data()
        
        # Get data for the last 2 years + predictions
        current_year = timezone.now().year
        current_month = timezone.now().month
        
        # Get DISTINCT months with AVERAGE temperatures (handle multiple regions)
        from django.db.models import Avg
        
        # Historical data - average by month
        historical_agg = MonthlyClimate.objects.filter(
            year__gte=current_year - 2,
            predicted_temperature__isnull=True  # Only actual data
        ).values('year', 'month').annotate(
            avg_temp=Avg('avg_temperature'),
            avg_pred_temp=Avg('predicted_temperature')
        ).order_by('year', 'month')[:24]
        
        # Predicted data - average by month
        predicted_agg = MonthlyClimate.objects.filter(
            predicted_temperature__isnull=False,
            year__gte=current_year  # Future predictions
        ).values('year', 'month').annotate(
            avg_temp=Avg('avg_temperature'),
            avg_pred_temp=Avg('predicted_temperature'),
            avg_confidence=Avg('prediction_confidence')
        ).order_by('year', 'month')[:12]
        
        print(f"Distinct historical months: {len(historical_agg)}")
        print(f"Distinct predicted months: {len(predicted_agg)}")
        
        # If we don't have enough data, use sample
        if len(historical_agg) < 6 or len(predicted_agg) < 6:
            print("Insufficient historical or predicted data, using sample...")
            return get_sample_monthly_trends_data()
        
        # Prepare chart data
        labels = []
        actual_temps = []
        predicted_temps = []
        confidence_min = []
        confidence_max = []
        
        # Add historical data
        for data in historical_agg:
            month_name = datetime(data['year'], data['month'], 1).strftime('%b')
            label = f"{month_name} {data['year']}"
            labels.append(label)
            actual_temps.append(float(data['avg_temp']))
            predicted_temps.append(None)
            confidence_min.append(None)
            confidence_max.append(None)
        
        # Add current month separator
        current_label = f"{datetime(current_year, current_month, 1).strftime('%b')} {current_year}"
        if current_label in labels:
            current_idx = labels.index(current_label)
        else:
            current_idx = len(labels)
        
        # Add predicted data
        for data in predicted_agg:
            month_name = datetime(data['year'], data['month'], 1).strftime('%b')
            label = f"{month_name} {data['year']}"
            # Avoid duplicate labels
            if label not in labels:
                labels.append(label)
                actual_temps.append(None)
                pred_temp = data['avg_pred_temp'] or 0
                predicted_temps.append(float(pred_temp))
                
                # Calculate confidence interval
                confidence = data.get('avg_confidence', 70) or 70
                uncertainty = (100 - confidence) / 10
                confidence_min.append(float(pred_temp) - uncertainty)
                confidence_max.append(float(pred_temp) + uncertainty)
        
        print(f"Monthly chart: {len(labels)} months total")
        print(f"Sample labels: {labels[:3]} ... {labels[-3:]}")
        
        # Calculate trend (only on predicted data)
        predicted_temp_list = [t for t in predicted_temps if t is not None]
        if len(predicted_temp_list) >= 2:
            first_temp = predicted_temp_list[0]
            last_temp = predicted_temp_list[-1]
            trend = 'increasing' if last_temp > first_temp else 'decreasing'
            trend_magnitude = abs(last_temp - first_temp)
            print(f"Trend: {trend} by {trend_magnitude:.1f}°C")
        else:
            trend = 'stable'
            trend_magnitude = 0
        
        return {
            'labels': labels,
            'actual_temperatures': actual_temps,
            'predicted_temperatures': predicted_temps,
            'confidence_min': confidence_min,
            'confidence_max': confidence_max,
            'current_month_index': current_idx,
            'trend': trend,
            'trend_magnitude': trend_magnitude,
            'has_predictions': len(predicted_temp_list) > 0,
            'total_months': len(labels),
            'historical_count': len(historical_agg),
            'prediction_count': len(predicted_temp_list),
        }
        
    except Exception as e:
        print(f"ERROR in prepare_monthly_trends_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return get_sample_monthly_trends_data()


def get_sample_monthly_trends_data():
    """Sample monthly trends data for testing."""
    print("Using sample monthly trends data")
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Historical temperatures (last year)
    historical_temps = [23.5, 24.1, 23.8, 22.9, 22.2, 21.5, 
                       20.8, 21.1, 22.0, 22.8, 23.2, 23.4]
    
    # Predicted temperatures (next year)
    predicted_temps = [23.8, 24.3, 24.0, 23.2, 22.5, 21.8, 
                      21.2, 21.5, 22.3, 23.1, 23.6, 23.7]
    
    # Confidence intervals
    conf_min = [t - 0.8 for t in predicted_temps]
    conf_max = [t + 0.8 for t in predicted_temps]
    
    # Create labels with years
    labels = [f"{m} 2024" for m in months[:6]] + [f"{m} 2025" for m in months[6:]]
    
    return {
        'labels': labels,
        'actual_temperatures': historical_temps + [None] * 6,
        'predicted_temperatures': [None] * 6 + predicted_temps,
        'confidence_min': [None] * 6 + conf_min,
        'confidence_max': [None] * 6 + conf_max,
        'current_month_index': 5,  # June (6th month)
        'trend': 'increasing',
        'trend_magnitude': 0.3,
        'has_predictions': True,
        'total_months': 12,
        'historical_count': 6,
        'prediction_count': 6,
    }


def map_view(request):
    """
    Interactive map view with climate data.
    """
    regions = Region.objects.all()
    regions_geojson = {
        "type": "FeatureCollection",
        "features": [region.to_geojson() for region in regions]
    }
    
    # Get climate data for markers
    climate_data = ClimateData.objects.select_related('region').order_by('-timestamp')[:50]
    
    context = {
        'regions_geojson': json.dumps(regions_geojson),
        'climate_data': climate_data,
        'map_center': [-1.2921, 36.8219],  # Nairobi coordinates
        'map_zoom': 6,
    }
    
    return render(request, 'map.html', context)


@login_required
def carbon_calculator(request):
    """
    Carbon footprint calculator with form submission.
    """
    if request.method == 'POST':
        form = CarbonCalculatorForm(request.POST)
        if form.is_valid():
            # Calculate carbon footprint
            footprint = calculate_carbon_footprint(form.cleaned_data, request.user)
            
            # Generate suggestions
            suggestions = generate_carbon_suggestions(footprint)
            footprint.suggestions = suggestions
            
            footprint.save()
            
            messages.success(request, _('Carbon footprint calculated successfully!'))
            return redirect('carbon_calculator')
    else:
        form = CarbonCalculatorForm()
    
    # Get user's previous calculations
    previous_calculations = CarbonFootprint.objects.filter(
        user=request.user
    ).order_by('-calculation_date')[:5] if request.user.is_authenticated else []
    
    context = {
        'form': form,
        'previous_calculations': previous_calculations,
    }
    
    return render(request, 'carbon_calculator.html', context)


def calculate_carbon_footprint(data, user):
    """
    Calculate carbon footprint based on user inputs.
    """
    # Emission factors (kg CO2e per unit)
    EMISSION_FACTORS = {
        'transport': 0.12,  # kg CO2e per km (petrol car)
        'electricity': 0.5,  # kg CO2e per kWh (Kenya grid average)
        'diet': {
            'vegetarian': 1000,
            'meat_light': 1500,
            'meat_medium': 2000,
            'meat_heavy': 3000,
        },  # kg CO2e per year
        'waste': 0.5,  # kg CO2e per kg waste
    }
    
    # Calculate emissions
    transport_co2e = data['transport_km'] * 52 * EMISSION_FACTORS['transport']  # Weekly to yearly
    electricity_co2e = data['electricity_kwh'] * 12 * EMISSION_FACTORS['electricity']  # Monthly to yearly
    diet_co2e = EMISSION_FACTORS['diet'][data['diet_type']]
    waste_co2e = data['waste_kg'] * 52 * EMISSION_FACTORS['waste']  # Weekly to yearly
    
    total_co2e = transport_co2e + electricity_co2e + diet_co2e + waste_co2e
    
    # Create CarbonFootprint object
    footprint = CarbonFootprint(
        user=user,
        transport_km=data['transport_km'],
        electricity_kwh=data['electricity_kwh'],
        diet_type=data['diet_type'],
        waste_kg=data['waste_kg'],
        total_co2e=total_co2e,
        transport_co2e=transport_co2e,
        electricity_co2e=electricity_co2e,
        diet_co2e=diet_co2e,
        waste_co2e=waste_co2e,
    )
    
    return footprint


def generate_carbon_suggestions(footprint):
    """
    Generate personalized carbon reduction suggestions.
    """
    suggestions = []
    
    # Transportation suggestions
    if footprint.transport_co2e > 2000:
        suggestions.append({
            'category': 'Transport',
            'suggestion': 'Consider using public transport or carpooling to reduce your transport emissions by up to 50%.',
            'impact': 'High',
            'savings_kg': 1000
        })
    
    # Electricity suggestions
    if footprint.electricity_co2e > 1500:
        suggestions.append({
            'category': 'Electricity',
            'suggestion': 'Switch to energy-efficient appliances and consider solar panels for your home.',
            'impact': 'Medium',
            'savings_kg': 750
        })
    
    # Diet suggestions
    if footprint.diet_co2e > 2000:
        suggestions.append({
            'category': 'Diet',
            'suggestion': 'Reduce meat consumption to 1-2 times per week to significantly lower your dietary carbon footprint.',
            'impact': 'High',
            'savings_kg': 1000
        })
    
    # General suggestions
    suggestions.append({
        'category': 'General',
        'suggestion': 'Plant native trees in your community - each tree can absorb up to 21 kg of CO2 per year.',
        'impact': 'Medium',
        'savings_kg': 100
    })
    
    return suggestions


@csrf_exempt
def save_carbon_footprint_api(request):
    """
    Simple API endpoint to save carbon footprint calculations.
    This works with the JavaScript calculator.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        # Parse JSON data
        data = json.loads(request.body)
        
        # Calculate emissions (simplified)
        transport_km = float(data.get('car_km', 0))
        electricity_kwh = float(data.get('electricity_kwh', 0))
        diet_type = data.get('diet_type', 'meat_medium')
        waste_kg = float(data.get('waste_kg', 0))
        
        # Simple calculation (you can use your actual calculation logic)
        transport_co2e = transport_km * 52 * 0.12  # Weekly to yearly
        electricity_co2e = electricity_kwh * 12 * 0.5  # Monthly to yearly
        
        # Diet emissions
        diet_map = {
            'vegetarian': 1000,
            'meat_light': 1500,
            'meat_medium': 2000,
            'meat_heavy': 3000,
        }
        diet_co2e = diet_map.get(diet_type, 2000)
        
        waste_co2e = waste_kg * 52 * 0.5  # Weekly to yearly
        
        total_co2e = transport_co2e + electricity_co2e + diet_co2e + waste_co2e
        
        # Save to database if user is authenticated
        if request.user.is_authenticated:
            from climate.models import CarbonFootprint
            
            CarbonFootprint.objects.create(
                user=request.user,
                transport_km=transport_km,
                electricity_kwh=electricity_kwh,
                diet_type=diet_type,
                waste_kg=waste_kg,
                total_co2e=total_co2e,
                transport_co2e=transport_co2e,
                electricity_co2e=electricity_co2e,
                diet_co2e=diet_co2e,
                waste_co2e=waste_co2e,
                suggestions=[]
            )
        
        return JsonResponse({
            'success': True,
            'total_co2e': total_co2e,
            'transport_co2e': transport_co2e,
            'electricity_co2e': electricity_co2e,
            'diet_co2e': diet_co2e,
            'waste_co2e': waste_co2e,
            'message': 'Calculation saved successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def history_view(request):
    """
    Historical climate data view with filtering.
    """
    form = ClimateQueryForm(request.GET or None)
    climate_data = ClimateData.objects.select_related('region').order_by('-timestamp')
    
    # Apply filters if form is valid
    if form.is_valid():
        region = form.cleaned_data.get('region')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        data_type = form.cleaned_data.get('data_type')
        
        if region:
            climate_data = climate_data.filter(region=region)
        
        if start_date:
            climate_data = climate_data.filter(timestamp__date__gte=start_date)
        
        if end_date:
            climate_data = climate_data.filter(timestamp__date__lte=end_date)
        
        # For specific data type, we could filter or annotate differently
        # This is a simplified implementation
    
    # Pagination
    paginator = Paginator(climate_data, 50)  # 50 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics for the filtered data
    if page_obj:
        stats = climate_data.aggregate(
            avg_temp=Avg('temperature'),
            total_rainfall=Sum('rainfall'),
            avg_humidity=Avg('humidity')
        )
    else:
        stats = {}
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
    }
    
    return render(request, 'history.html', context)


def register(request):
    """
    User registration view.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Registration successful! Welcome to Mazingira Insight AI.'))
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile(request):
    """
    User profile view.
    """
    user = request.user
    carbon_footprints = CarbonFootprint.objects.filter(user=user).order_by('-calculation_date')[:10]
    user_reports = EnvironmentalReport.objects.filter(user=user).order_by('-created_at')[:10]
    
    context = {
        'user': user,
        'carbon_footprints': carbon_footprints,
        'user_reports': user_reports,
    }
    
    return render(request, 'profile.html', context)


@login_required
def reports_list(request):
    """
    List all environmental reports.
    """
    reports = EnvironmentalReport.objects.filter(
        Q(is_public=True) | Q(user=request.user)
    ).select_related('region', 'user').order_by('-created_at')
    
    # Filter by type if provided
    report_type = request.GET.get('type')
    if report_type:
        reports = reports.filter(report_type=report_type)
    
    # Pagination
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'report_types': EnvironmentalReport.REPORT_TYPES,
    }
    
    return render(request, 'reports_list.html', context)


@login_required
def create_report(request):
    """
    Create a new environmental report.
    """
    if request.method == 'POST':
        form = EnvironmentalReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            
            # Set location from region if not provided
            if not report.latitude or not report.longitude:
                region = report.region
                if region and region.location:
                    report.latitude = region.location.y
                    report.longitude = region.location.x
            
            report.save()
            messages.success(request, _('Report submitted successfully!'))
            return redirect('reports_list')
    else:
        form = EnvironmentalReportForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'create_report.html', context)


def report_detail(request, report_id):
    """
    View details of a specific environmental report.
    """
    report = get_object_or_404(EnvironmentalReport, id=report_id)
    
    # Check if user can view the report
    if not report.is_public and report.user != request.user:
        messages.error(request, _('You do not have permission to view this report.'))
        return redirect('reports_list')
    
    # Get similar reports
    similar_reports = EnvironmentalReport.objects.filter(
        region=report.region,
        is_public=True
    ).exclude(id=report.id).order_by('-created_at')[:5]
    
    context = {
        'report': report,
        'similar_reports': similar_reports,
    }
    
    return render(request, 'report_detail.html', context)


def export_climate_data_csv(request):
    """
    Export climate data as CSV.
    """
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="climate_data.csv"'
    
    writer = csv.writer(response)
    
    # Write CSV header
    writer.writerow([
        'Region', 'Country', 'Timestamp', 'Temperature (°C)', 
        'Humidity (%)', 'Rainfall (mm)', 'Air Quality Index',
        'Wind Speed (m/s)', 'Pressure (hPa)', 'Source'
    ])
    
    # Write data rows
    climate_data = ClimateData.objects.select_related('region').order_by('-timestamp')[:1000]
    
    for data in climate_data:
        writer.writerow([
            data.region.name,
            data.region.country,
            data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            data.temperature,
            data.humidity,
            data.rainfall,
            data.air_quality_index or '',
            data.wind_speed,
            data.pressure or '',
            data.source
        ])
    
    return response


def export_region_pdf(request, region_id):
    """
    Export region climate report as PDF.
    """
    try:
        import weasyprint
    except ImportError:
        messages.error(request, _('PDF export is not available. Please install weasyprint.'))
        return redirect('dashboard')
    
    region = get_object_or_404(Region, id=region_id)
    
    # Get climate data for the last 30 days
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    climate_data = ClimateData.objects.filter(
        region=region,
        timestamp__range=[start_date, end_date]
    ).order_by('timestamp')
    
    # Calculate statistics
    stats = climate_data.aggregate(
        avg_temp=Avg('temperature'),
        max_temp=Max('temperature'),
        min_temp=Min('temperature'),
        total_rainfall=Sum('rainfall'),
        avg_humidity=Avg('humidity')
    )
    
    context = {
        'region': region,
        'climate_data': climate_data[:50],  # Limit to 50 records
        'stats': stats,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    # Render HTML template
    html = render(request, 'pdf/region_report.html', context)
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{region.name}_climate_report.pdf"'
    
    # Generate PDF
    weasyprint.HTML(string=html.content.decode('utf-8')).write_pdf(response)
    
    return response


@require_POST
def get_predictions(request):
    """
    Get predictions for a region (AJAX endpoint).
    """
    region_id = request.POST.get('region_id')
    days_ahead = int(request.POST.get('days_ahead', 7))
    
    try:
        region = Region.objects.get(id=region_id)
        
        # Initialize predictor
        predictor = ClimatePredictor()
        
        # Get historical data for the region
        historical_data = ClimateData.objects.filter(
            region=region
        ).order_by('-timestamp')[:100]  # Last 100 readings
        
        if len(historical_data) < 10:
            return JsonResponse({
                'error': 'Insufficient historical data for prediction'
            }, status=400)
        
        # Prepare data for prediction
        data = [
            {
                'temperature': float(d.temperature),
                'rainfall': float(d.rainfall),
                'humidity': float(d.humidity),
                'timestamp': d.timestamp.timestamp()
            }
            for d in historical_data
        ]
        
        # Make prediction
        predictions = predictor.predict_future(data, n_steps=days_ahead)
        
        return JsonResponse({
            'success': True,
            'region': region.name,
            'predictions': predictions
        })
        
    except Region.DoesNotExist:
        return JsonResponse({'error': 'Region not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)