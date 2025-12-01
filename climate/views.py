"""
Views for the climate monitoring application.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count, Q, Sum  # ADDED: Sum import
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.conf import settings

import json
import csv
import datetime
from datetime import timedelta
from decimal import Decimal

from .models import ClimateData, Region, CarbonFootprint, EnvironmentalReport, Prediction
from .forms import UserRegistrationForm, CarbonCalculatorForm, EnvironmentalReportForm, ClimateQueryForm
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
    
    # Get statistics
    temp_stats = ClimateData.objects.aggregate(
        avg_temp=Avg('temperature'),
        max_temp=Max('temperature'),
        min_temp=Min('temperature')
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
    
    # Prepare data for charts
    chart_data = prepare_chart_data()
    
    context = {
        'latest_data': latest_data,
        'regions_with_data': regions_with_data,
        'temp_stats': temp_stats,
        'predictions': predictions,
        'user_footprint': user_footprint,
        'recent_reports': recent_reports,
        'chart_data': json.dumps(chart_data),
    }
    
    return render(request, 'dashboard.html', context)


def prepare_chart_data():
    """
    Prepare data for dashboard charts.
    """
    # Get data for the last 30 days
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Aggregate temperature data by day
    temperature_data = ClimateData.objects.filter(
        timestamp__range=[start_date, end_date]
    ).extra({
        'date': "date(timestamp)"
    }).values('date').annotate(
        avg_temp=Avg('temperature'),
        max_temp=Max('temperature'),
        min_temp=Min('temperature')
    ).order_by('date')
    
    # Format for Chart.js
    dates = [item['date'].strftime('%Y-%m-%d') for item in temperature_data]
    avg_temps = [float(item['avg_temp']) for item in temperature_data]
    
    return {
        'temperature': {
            'labels': dates,
            'datasets': [
                {
                    'label': 'Average Temperature (°C)',
                    'data': avg_temps,
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                }
            ]
        }
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
    
    return render(request, 'registration/register.html', {'form': form})  # CHANGED: Added 'registration/'


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
    
    context = {
        'report': report,
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