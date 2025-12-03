#!/bin/bash
# Mazingira Insight AI - Weather Data Updater
# This script updates weather data and can be run manually or via cron

set -e  # Exit on error

echo "========================================="
echo "Mazingira Insight AI - Weather Updater"
echo "Started at: $(date)"
echo "========================================="

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at venv/bin/activate"
    exit 1
fi

# Check if we should force update
FORCE_FLAG=""
if [ "$1" == "--force" ] || [ "$1" == "-f" ]; then
    FORCE_FLAG="--force"
    echo "⚡ Force update requested"
fi

# Run the weather fetch command
echo "🌤️  Fetching weather data..."
python manage.py fetch_weather $FORCE_FLAG

# Optional: Run any other maintenance tasks
# echo "🧹 Running maintenance tasks..."
# python manage.py clearsessions  # Clear expired sessions
# python manage.py collectstatic --noinput  # Update static files if needed

echo "========================================="
echo "✅ Weather update completed at: $(date)"
echo "========================================="
