"""
URL configuration for climate_dashboard project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('climate.urls')),  # Main app URLs
    path('api/', include('climate.api.urls')),  # API endpoints
    path('accounts/', include('django.contrib.auth.urls')),  # Authentication
    path('i18n/', include('django.conf.urls.i18n')),  # Internationalization
    
    # Redirect root to dashboard
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)