"""
URL routing for the climate application.
"""

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .api import views as api_views

urlpatterns = [
    # Main pages
    path('', views.dashboard, name='dashboard'),
    path('map/', views.map_view, name='map'),
    path('carbon/', views.carbon_calculator, name='carbon_calculator'),
    path('history/', views.history_view, name='history'),
    
    # Authentication
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',  # CHANGED: Added 'registration/'
        redirect_authenticated_user=True
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/register/', views.register, name='register'),
    
    # User-specific pages
    path('profile/', views.profile, name='profile'),
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/new/', views.create_report, name='create_report'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    
    # API endpoints (also available via REST framework)
    path('api/', include('climate.api.urls')),
    
    # Data export
    path('export/csv/', views.export_climate_data_csv, name='export_climate_data_csv'),
    path('export/pdf/<int:region_id>/', views.export_region_pdf, name='export_region_pdf'),
]