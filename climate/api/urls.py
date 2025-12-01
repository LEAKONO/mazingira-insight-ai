"""
API URL routing for the climate application.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'regions', views.RegionViewSet)
router.register(r'climate-data', views.ClimateDataViewSet)
router.register(r'carbon-footprints', views.CarbonFootprintViewSet, basename='carbonfootprint')
router.register(r'reports', views.EnvironmentalReportViewSet)
router.register(r'predictions', views.PredictionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('weather/', views.weather_data, name='weather_data'),
    path('predict-temperature/', views.predict_temperature, name='predict_temperature'),
    path('regions/geojson/', views.regions_geojson, name='regions_geojson'),
    path('statistics/', views.climate_statistics, name='climate_statistics'),
]