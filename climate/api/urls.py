"""
API URL routing for the climate application.
Updated with basename parameters for all ViewSets.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from climate.api.views import generate_monthly_predictions

from . import views

router = DefaultRouter()
router.register(r'regions', views.RegionViewSet, basename='region')
router.register(r'climate-data', views.ClimateDataViewSet, basename='climatedata')
router.register(r'carbon-footprints', views.CarbonFootprintViewSet, basename='carbonfootprint')
router.register(r'reports', views.EnvironmentalReportViewSet, basename='report')
router.register(r'predictions', views.PredictionViewSet, basename='prediction')

urlpatterns = [
    path('', include(router.urls)),
    path('weather/', views.weather_data, name='weather_data'),
    path('predict-temperature/', views.predict_temperature, name='predict_temperature'),
    path('regions/geojson/', views.regions_geojson, name='regions_geojson'),
    path('statistics/', views.climate_statistics, name='climate_statistics'),
    path('generate-monthly-predictions/', generate_monthly_predictions, name='generate-monthly-predictions'),
    
]
