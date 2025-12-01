#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

def setup_environment():
    """Setup environment variables and settings."""
    # Load environment variables from .env file
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print(f"Loaded environment variables from: {env_path}")
    
    # Set default settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climate_dashboard.settings')
    
    # Check for required environment variables in production
    if os.getenv('DJANGO_ENV') == 'production':
        required_vars = ['DJANGO_SECRET_KEY', 'ALLOWED_HOSTS']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            print(f"ERROR: Missing required environment variables in production: {', '.join(missing_vars)}")
            print("Please set these variables in your .env file or environment.")
            sys.exit(1)

def main():
    """Run administrative tasks."""
    # Setup environment first
    setup_environment()
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Add custom commands or hooks here if needed
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        # Pre-command hooks
        if command == 'runserver':
            print("🚀 Starting Mazingira Insight AI development server...")
            print("🌍 Visit: http://localhost:8000")
            print("📊 Dashboard: http://localhost:8000/")
            print("🗺️  Map: http://localhost:8000/map/")
            print("♻️  Carbon Calculator: http://localhost:8000/carbon/")
            
            # Check if database exists
            db_path = Path(__file__).resolve().parent / 'db.sqlite3'
            if not db_path.exists():
                print("\n⚠️  Database not found. Running migrations first...")
                from django.core.management import execute_from_command_line
                execute_from_command_line(['manage.py', 'migrate'])
        
        elif command == 'seed_data':
            print("🌱 Seeding database with sample climate data...")
            
        elif command == 'train_initial_model':
            print("🤖 Training initial machine learning model...")
    
    # Execute the command
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()