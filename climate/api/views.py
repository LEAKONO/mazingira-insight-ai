"""
API views for the climate application.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Max, Min, Sum, Count
from django.http import JsonResponse
import datetime

from climate.models import Region, ClimateData, CarbonFootprint, EnvironmentalReport, Prediction
from climate.serializers import (
    RegionSerializer, ClimateDataSerializer, CarbonFootprintSerializer,
    EnvironmentalReportSerializer, PredictionSerializer,
    WeatherRequestSerializer, PredictionRequestSerializer
)
from climate.ml.predictor import ClimatePredictor
from .weather_api import WeatherAPIClient


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing regions."""
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    
    @action(detail=True, methods=['get'])
    def climate_data(self, request, pk=None):
        """Get climate data for a specific region."""
        region = self.get_object()
        days = request.query_params.get('days', 30)
        
        start_date = timezone.now() - datetime.timedelta(days=int(days))
        climate_data = ClimateData.objects.filter(
            region=region,
            timestamp__gte=start_date
        ).order_by('timestamp')
        
        serializer = ClimateDataSerializer(climate_data, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get climate statistics for a region."""
        region = self.get_object()
        
        stats = ClimateData.objects.filter(region=region).aggregate(
            avg_temp=Avg('temperature'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            total_rainfall=Sum('rainfall'),
            avg_humidity=Avg('humidity'),
            record_count=Count('id')
        )
        
        return Response(stats)


class ClimateDataViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing climate data."""
    queryset = ClimateData.objects.all().order_by('-timestamp')
    serializer_class = ClimateDataSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = ClimateData.objects.all().order_by('-timestamp')
        
        # Filter by region
        region_id = self.request.query_params.get('region_id')
        if region_id:
            queryset = queryset.filter(region_id=region_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        # Limit results
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except ValueError:
                pass
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest climate data for all regions."""
        latest_data = []
        regions = Region.objects.all()[:10]  # Limit to 10 regions
        
        for region in regions:
            data = ClimateData.objects.filter(region=region).order_by('-timestamp').first()
            if data:
                latest_data.append(data)
        
        serializer = self.get_serializer(latest_data, many=True)
        return Response(serializer.data)


class CarbonFootprintViewSet(viewsets.ModelViewSet):
    """API endpoint for carbon footprints."""
    serializer_class = CarbonFootprintSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only the user's carbon footprints."""
        return CarbonFootprint.objects.filter(user=self.request.user).order_by('-calculation_date')
    
    def perform_create(self, serializer):
        """Set the user when creating a carbon footprint."""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get carbon footprint statistics for the user."""
        footprints = self.get_queryset()
        
        if not footprints.exists():
            return Response({'message': 'No carbon footprint data available'})
        
        latest = footprints.first()
        avg_co2e = footprints.aggregate(avg=Avg('total_co2e'))['avg']
        
        return Response({
            'latest_footprint': CarbonFootprintSerializer(latest).data,
            'average_co2e': avg_co2e,
            'total_calculations': footprints.count(),
            'emission_level': latest.get_emission_level()
        })


class EnvironmentalReportViewSet(viewsets.ModelViewSet):
    """API endpoint for environmental reports."""
    serializer_class = EnvironmentalReportSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Filter reports based on user permissions."""
        user = self.request.user
        
        if user.is_authenticated:
            # Return user's reports and public reports
            return EnvironmentalReport.objects.filter(
                models.Q(user=user) | models.Q(is_public=True)
            ).order_by('-created_at')
        else:
            # Return only public reports for anonymous users
            return EnvironmentalReport.objects.filter(is_public=True).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set the user when creating a report."""
        serializer.save(user=self.request.user)


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for predictions."""
    queryset = Prediction.objects.all().order_by('-prediction_date')
    serializer_class = PredictionSerializer
    permission_classes = [AllowAny]


@api_view(['GET'])
@permission_classes([AllowAny])
def weather_data(request):
    """Get weather data for a location."""
    serializer = WeatherRequestSerializer(data=request.query_params)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    weather_client = WeatherAPIClient()
    
    try:
        # Try to get weather data
        weather_result = weather_client.get_weather_data(data)
        
        # Also get air quality data if available
        try:
            air_quality = weather_client.get_air_quality(
                data.get('latitude'),
                data.get('longitude')
            )
            weather_result['air_quality'] = air_quality
        except Exception:
            # Air quality data is optional
            pass
        
        return Response(weather_result)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def predict_temperature(request):
    """Make temperature predictions using ML model."""
    serializer = PredictionRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    region_id = data['region_id']
    days_ahead = data['days_ahead']
    
    try:
        region = Region.objects.get(id=region_id)
        predictor = ClimatePredictor()
        
        # Get historical data
        historical_data = ClimateData.objects.filter(
            region=region
        ).order_by('-timestamp')[:100]
        
        if len(historical_data) < 10:
            return Response(
                {'error': 'Insufficient historical data for prediction'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare data for prediction
        prediction_data = [
            {
                'temperature': float(d.temperature),
                'rainfall': float(d.rainfall),
                'humidity': float(d.humidity),
                'timestamp': d.timestamp.timestamp()
            }
            for d in historical_data
        ]
        
        # Make predictions
        predictions = predictor.predict_future(prediction_data, n_steps=days_ahead)
        
        # Store predictions in database
        prediction_objects = []
        for i, pred in enumerate(predictions):
            prediction_date = timezone.now() + datetime.timedelta(days=i+1)
            
            prediction_obj = Prediction(
                region=region,
                prediction_date=prediction_date,
                predicted_temperature=pred.get('temperature', 0),
                predicted_rainfall=pred.get('rainfall', 0),
                model_version='v1.0'
            )
            prediction_objects.append(prediction_obj)
        
        # Bulk create predictions
        Prediction.objects.bulk_create(prediction_objects)
        
        return Response({
            'region': region.name,
            'days_ahead': days_ahead,
            'predictions': predictions
        })
        
    except Region.DoesNotExist:
        return Response(
            {'error': 'Region not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def regions_geojson(request):
    """Get all regions as GeoJSON."""
    regions = Region.objects.all()
    
    features = []
    for region in regions:
        features.append(region.to_geojson())
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return Response(geojson)


@api_view(['GET'])
@permission_classes([AllowAny])
def climate_statistics(request):
    """Get overall climate statistics."""
    # Basic statistics
    basic_stats = ClimateData.objects.aggregate(
        total_readings=Count('id'),
        avg_temperature=Avg('temperature'),
        avg_humidity=Avg('humidity'),
        total_rainfall=Sum('rainfall'),
        avg_air_quality=Avg('air_quality_index')
    )
    
    # Regional statistics
    regional_stats = []
    regions = Region.objects.all()[:5]  # Limit to 5 regions
    
    for region in regions:
        stats = ClimateData.objects.filter(region=region).aggregate(
            avg_temp=Avg('temperature'),
            total_rain=Sum('rainfall'),
            readings=Count('id')
        )
        
        regional_stats.append({
            'region': region.name,
            'avg_temperature': stats['avg_temp'],
            'total_rainfall': stats['total_rain'],
            'readings': stats['readings']
        })
    
    # Recent predictions
    recent_predictions = Prediction.objects.filter(
        prediction_date__date__gte=timezone.now().date()
    ).select_related('region')[:3]
    
    prediction_data = PredictionSerializer(recent_predictions, many=True).data
    
    return Response({
        'basic_statistics': basic_stats,
        'regional_statistics': regional_stats,
        'recent_predictions': prediction_data,
        'last_updated': timezone.now()
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def generate_monthly_predictions(request):
    """Generate monthly climate predictions."""
    try:
        # Run monthly aggregation first
        from django.core import management
        management.call_command('generate_monthly_data', months=24)
        
        # Run monthly predictions
        management.call_command('predict_monthly', train=True)
        
        # Count predictions generated
        predictions_count = MonthlyClimate.objects.filter(
            predicted_temperature__isnull=False
        ).count()
        
        return Response({
            'success': True,
            'predictions_generated': predictions_count,
            'message': f'Successfully generated {predictions_count} monthly predictions'
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)