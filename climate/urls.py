# climate/urls.py - UPDATED VERSION

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main pages
    path('', views.dashboard, name='dashboard'),
    path('map/', views.map_view, name='map'),
    path('carbon/', views.carbon_calculator, name='carbon_calculator'),
    path('history/', views.history_view, name='history'),
    # Add this to your urlpatterns
    path('api/test/', views.test_api, name='test_api'),

    
    # Authentication
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/register/', views.register, name='register'),
    
    # User-specific pages
    path('profile/', views.profile, name='profile'),
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/new/', views.create_report, name='create_report'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    
    # REST API endpoints (v1)
    path('api/v1/', include('climate.api.urls')),
    
    # SIMPLE API endpoints for JavaScript/map (legacy) - REDIRECT to REST API
    path('api/weather/', views.weather_api_redirect, name='weather_api'),
    path('api/climate-data/latest/', views.climate_data_api, name='climate_data_latest'),
    path('api/climate-data/', views.climate_data_api, name='climate_data_api'),
    path('api/reports/', views.reports_api, name='reports_api'),
    path('api/save-carbon-footprint/', views.save_carbon_footprint_api, name='save_carbon_footprint_api'),
    
    # Data export
    path('export/csv/', views.export_climate_data_csv, name='export_climate_data_csv'),
    path('export/pdf/<int:region_id>/', views.export_region_pdf, name='export_region_pdf'),
]