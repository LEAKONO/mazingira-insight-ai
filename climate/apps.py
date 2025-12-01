from django.apps import AppConfig


class ClimateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'climate'
    
    def ready(self):
        # Import signals
        import climate.signals