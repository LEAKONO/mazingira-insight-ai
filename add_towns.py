# add_towns.py - Add 30+ East African towns to the database
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climate_dashboard.settings')
django.setup()

from climate.models import Region

towns = [
    # Kenya (12 towns)
    {'name': 'Nakuru', 'country': 'Kenya', 'lat': -0.3031, 'lon': 36.0800, 'pop': 570674, 'elev': 1850},
    {'name': 'Eldoret', 'country': 'Kenya', 'lat': 0.5143, 'lon': 35.2698, 'pop': 475716, 'elev': 2100},
    {'name': 'Kisumu', 'country': 'Kenya', 'lat': -0.0917, 'lon': 34.7680, 'pop': 397957, 'elev': 1131},
    {'name': 'Thika', 'country': 'Kenya', 'lat': -1.0392, 'lon': 37.0894, 'pop': 279429, 'elev': 1531},
    {'name': 'Malindi', 'country': 'Kenya', 'lat': -3.2175, 'lon': 40.1167, 'pop': 207253, 'elev': 0},
    {'name': 'Kitale', 'country': 'Kenya', 'lat': 1.0167, 'lon': 35.0000, 'pop': 162174, 'elev': 1900},
    {'name': 'Garissa', 'country': 'Kenya', 'lat': -0.4569, 'lon': 39.6583, 'pop': 119696, 'elev': 150},
    {'name': 'Kakamega', 'country': 'Kenya', 'lat': 0.2842, 'lon': 34.7523, 'pop': 107227, 'elev': 1580},
    {'name': 'Kisii', 'country': 'Kenya', 'lat': -0.6833, 'lon': 34.7667, 'pop': 112417, 'elev': 1765},
    {'name': 'Nyeri', 'country': 'Kenya', 'lat': -0.4167, 'lon': 36.9500, 'pop': 119273, 'elev': 1755},
    {'name': 'Embu', 'country': 'Kenya', 'lat': -0.5369, 'lon': 37.4500, 'pop': 60898, 'elev': 1350},
    {'name': 'Machakos', 'country': 'Kenya', 'lat': -1.5167, 'lon': 37.2667, 'pop': 150041, 'elev': 1700},
    
    # Tanzania (8 towns)
    {'name': 'Dar es Salaam', 'country': 'Tanzania', 'lat': -6.7924, 'lon': 39.2083, 'pop': 7962000, 'elev': 0},
    {'name': 'Dodoma', 'country': 'Tanzania', 'lat': -6.1630, 'lon': 35.7516, 'pop': 213636, 'elev': 1120},
    {'name': 'Mwanza', 'country': 'Tanzania', 'lat': -2.5167, 'lon': 32.9000, 'pop': 706543, 'elev': 1140},
    {'name': 'Arusha', 'country': 'Tanzania', 'lat': -3.3869, 'lon': 36.6830, 'pop': 416442, 'elev': 1387},
    {'name': 'Mbeya', 'country': 'Tanzania', 'lat': -8.9000, 'lon': 33.4500, 'pop': 385279, 'elev': 1697},
    {'name': 'Zanzibar', 'country': 'Tanzania', 'lat': -6.1659, 'lon': 39.2026, 'pop': 896721, 'elev': 0},
    {'name': 'Morogoro', 'country': 'Tanzania', 'lat': -6.8242, 'lon': 37.6633, 'pop': 315866, 'elev': 526},
    {'name': 'Tanga', 'country': 'Tanzania', 'lat': -5.0667, 'lon': 39.1000, 'pop': 273332, 'elev': 25},
    
    # Uganda (6 towns)
    {'name': 'Jinja', 'country': 'Uganda', 'lat': 0.4244, 'lon': 33.2022, 'pop': 72931, 'elev': 1143},
    {'name': 'Gulu', 'country': 'Uganda', 'lat': 2.7809, 'lon': 32.2997, 'pop': 152276, 'elev': 1078},
    {'name': 'Mbarara', 'country': 'Uganda', 'lat': -0.6136, 'lon': 30.6586, 'pop': 195013, 'elev': 1480},
    {'name': 'Entebbe', 'country': 'Uganda', 'lat': 0.0516, 'lon': 32.4637, 'pop': 79931, 'elev': 1180},
    {'name': 'Lira', 'country': 'Uganda', 'lat': 2.2350, 'lon': 32.9097, 'pop': 119323, 'elev': 1090},
    {'name': 'Masaka', 'country': 'Uganda', 'lat': -0.3333, 'lon': 31.7333, 'pop': 103829, 'elev': 1280},
    
    # Rwanda (4 towns)
    {'name': 'Kigali', 'country': 'Rwanda', 'lat': -1.9441, 'lon': 30.0619, 'pop': 1132686, 'elev': 1567},
    {'name': 'Butare', 'country': 'Rwanda', 'lat': -2.5967, 'lon': 29.7439, 'pop': 89600, 'elev': 1768},
    {'name': 'Gisenyi', 'country': 'Rwanda', 'lat': -1.6928, 'lon': 29.2583, 'pop': 83623, 'elev': 1481},
    {'name': 'Ruhengeri', 'country': 'Rwanda', 'lat': -1.5000, 'lon': 29.6333, 'pop': 59333, 'elev': 1860},
    
    # Ethiopia (4 towns)
    {'name': 'Addis Ababa', 'country': 'Ethiopia', 'lat': 9.0320, 'lon': 38.7469, 'pop': 3384569, 'elev': 2355},
    {'name': 'Dire Dawa', 'country': 'Ethiopia', 'lat': 9.6000, 'lon': 41.8667, 'pop': 440000, 'elev': 1276},
    {'name': 'Bahir Dar', 'country': 'Ethiopia', 'lat': 11.6000, 'lon': 37.3833, 'pop': 243300, 'elev': 1800},
    {'name': 'Hawassa', 'country': 'Ethiopia', 'lat': 7.0500, 'lon': 38.4667, 'pop': 300000, 'elev': 1708},
    
    # South Sudan (2 towns)
    {'name': 'Juba', 'country': 'South Sudan', 'lat': 4.8594, 'lon': 31.5713, 'pop': 525953, 'elev': 550},
    {'name': 'Wau', 'country': 'South Sudan', 'lat': 7.7000, 'lon': 27.9833, 'pop': 151000, 'elev': 450},
    
    # Burundi (2 towns)
    {'name': 'Bujumbura', 'country': 'Burundi', 'lat': -3.3822, 'lon': 29.3644, 'pop': 497166, 'elev': 774},
    {'name': 'Gitega', 'country': 'Burundi', 'lat': -3.4264, 'lon': 29.9306, 'pop': 135467, 'elev': 1504},
]

print("Adding 38 East African towns...\n")
print("=" * 50)

added_count = 0
existing_count = 0

for town in towns:
    try:
        region, created = Region.objects.get_or_create(
            name=town['name'],
            country=town['country'],
            defaults={
                'latitude': town['lat'],
                'longitude': town['lon'],
                'population': town['pop'],
                'elevation': town.get('elev', 0),
                'climate_zone': 'Tropical',
                'area_sq_km': town.get('area', 0)
            }
        )
        if created:
            print(f"✅ Added: {town['name']}, {town['country']}")
            added_count += 1
        else:
            print(f"⚠️ Exists: {town['name']} (updating data)")
            # Update existing region with new data
            region.latitude = town['lat']
            region.longitude = town['lon']
            region.population = town['pop']
            region.elevation = town.get('elev', 0)
            region.save()
            existing_count += 1
    except Exception as e:
        print(f"❌ Error adding {town['name']}: {e}")

print("=" * 50)
print(f"\n📊 Summary:")
print(f"✅ Newly added: {added_count} towns")
print(f"⚠️ Already existed (updated): {existing_count} towns")
print(f"📈 Total regions in database: {Region.objects.count()}")
print("\n📝 Next steps:")
print("1. Fetch weather data: python manage.py fetch_weather")
print("2. Generate monthly data: python manage.py generate_monthly_data --months=24")
print("3. Update predictions: python manage.py predict_monthly --train")
print("4. Start server: python manage.py runserver")
