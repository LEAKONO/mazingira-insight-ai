from django.apps import AppConfig


class ClimateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'climate'
    
    def ready(self):
        """Import signals when app is ready."""
        # Import signals module
        try:
            import climate.signals
        except ImportError:
            # Signals module might not exist yet
            pass