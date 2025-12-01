"""
Tests for climate views.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta

from climate.models import Region, ClimateData, CarbonFootprint, EnvironmentalReport


class DashboardViewTest(TestCase):
    """Test the dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        # Create some climate data
        for i in range(5):
            ClimateData.objects.create(
                region=self.region,
                timestamp=timezone.now() - timedelta(hours=i),
                temperature=22.0 + i,
                humidity=60.0 + i,
                rainfall=i * 0.5,
                source='api'
            )
    
    def test_dashboard_view_status_code(self):
        """Test that dashboard view returns 200."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_view_uses_correct_template(self):
        """Test that dashboard view uses correct template."""
        response = self.client.get(reverse('dashboard'))
        self.assertTemplateUsed(response, 'dashboard.html')
    
    def test_dashboard_view_context(self):
        """Test that dashboard view has correct context data."""
        response = self.client.get(reverse('dashboard'))
        
        # Check that context contains required data
        self.assertIn('latest_data', response.context)
        self.assertIn('regions_with_data', response.context)
        self.assertIn('temp_stats', response.context)
        
        # Check data types
        self.assertIsInstance(response.context['latest_data'].first(), ClimateData)
        self.assertIsInstance(response.context['temp_stats'], dict)
    
    def test_dashboard_view_with_authenticated_user(self):
        """Test dashboard view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        
        # Create carbon footprint for user
        CarbonFootprint.objects.create(
            user=self.user,
            transport_km=100,
            electricity_kwh=200,
            diet_type='meat_medium',
            waste_kg=5,
            total_co2e=4500
        )
        
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_footprint', response.context)
        self.assertIsInstance(response.context['user_footprint'], CarbonFootprint)


class MapViewTest(TestCase):
    """Test the map view."""
    
    def setUp(self):
        self.client = Client()
        
        # Create regions with locations
        self.region1 = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921),
            geojson={
                'type': 'Point',
                'coordinates': [36.8219, -1.2921]
            }
        )
        
        self.region2 = Region.objects.create(
            name='Mombasa',
            country='Kenya',
            location=Point(39.6682, -4.0435),
            geojson={
                'type': 'Point',
                'coordinates': [39.6682, -4.0435]
            }
        )
    
    def test_map_view_status_code(self):
        """Test that map view returns 200."""
        response = self.client.get(reverse('map'))
        self.assertEqual(response.status_code, 200)
    
    def test_map_view_uses_correct_template(self):
        """Test that map view uses correct template."""
        response = self.client.get(reverse('map'))
        self.assertTemplateUsed(response, 'map.html')
    
    def test_map_view_context(self):
        """Test that map view has correct context data."""
        response = self.client.get(reverse('map'))
        
        self.assertIn('regions_geojson', response.context)
        self.assertIn('climate_data', response.context)
        self.assertIn('map_center', response.context)
        self.assertIn('map_zoom', response.context)
        
        # Check that geojson is a JSON string
        geojson = response.context['regions_geojson']
        self.assertIsInstance(geojson, str)
        
        # Parse and validate JSON
        import json
        parsed = json.loads(geojson)
        self.assertEqual(parsed['type'], 'FeatureCollection')
        self.assertEqual(len(parsed['features']), 2)


class CarbonCalculatorViewTest(TestCase):
    """Test the carbon calculator view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_carbon_calculator_view_status_code(self):
        """Test that carbon calculator view returns 200."""
        response = self.client.get(reverse('carbon_calculator'))
        self.assertEqual(response.status_code, 200)
    
    def test_carbon_calculator_view_requires_login(self):
        """Test that carbon calculator view requires login."""
        # Should redirect to login when not authenticated
        response = self.client.get(reverse('carbon_calculator'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/accounts/login/?next={reverse("carbon_calculator")}')
    
    def test_carbon_calculator_view_with_authenticated_user(self):
        """Test carbon calculator view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('carbon_calculator'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'carbon_calculator.html')
    
    def test_carbon_calculator_form_submission(self):
        """Test carbon calculator form submission."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'transport_km': 100,
            'electricity_kwh': 200,
            'diet_type': 'meat_medium',
            'waste_kg': 5,
            'car_type': 'petrol',
            'car_km': 100,
            'public_transport_km': 50,
            'household_size': 4,
            'renewable_energy': 'none',
            'flights_hours': 0
        }
        
        response = self.client.post(reverse('carbon_calculator'), form_data)
        
        # Should redirect to same page on success
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('carbon_calculator'))
        
        # Check that carbon footprint was created
        self.assertTrue(CarbonFootprint.objects.filter(user=self.user).exists())
        
        # Check the created footprint
        footprint = CarbonFootprint.objects.filter(user=self.user).first()
        self.assertGreater(footprint.total_co2e, 0)
        self.assertIsNotNone(footprint.suggestions)


class HistoryViewTest(TestCase):
    """Test the history view."""
    
    def setUp(self):
        self.client = Client()
        
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        # Create climate data for testing
        for i in range(20):
            ClimateData.objects.create(
                region=self.region,
                timestamp=timezone.now() - timedelta(days=i),
                temperature=22.0 + (i % 5),
                humidity=60.0 + (i % 10),
                rainfall=i * 0.2,
                source='api'
            )
    
    def test_history_view_status_code(self):
        """Test that history view returns 200."""
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)
    
    def test_history_view_uses_correct_template(self):
        """Test that history view uses correct template."""
        response = self.client.get(reverse('history'))
        self.assertTemplateUsed(response, 'history.html')
    
    def test_history_view_pagination(self):
        """Test that history view paginates correctly."""
        response = self.client.get(reverse('history'))
        
        self.assertIn('page_obj', response.context)
        page_obj = response.context['page_obj']
        
        # Should have pagination with 20 items
        self.assertEqual(page_obj.paginator.count, 20)
        self.assertEqual(len(page_obj), 20)  # Default page size is 50
    
    def test_history_view_filtering(self):
        """Test that history view filters correctly."""
        # Filter by region
        response = self.client.get(f'{reverse("history")}?region={self.region.id}')
        self.assertEqual(response.status_code, 200)
        
        # Filter by date range
        start_date = (timezone.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        end_date = timezone.now().strftime('%Y-%m-%d')
        
        response = self.client.get(
            f'{reverse("history")}?start_date={start_date}&end_date={end_date}'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should have fewer items when filtered
        page_obj = response.context['page_obj']
        self.assertLessEqual(len(page_obj), 11)  # 10 days + today


class AuthenticationViewsTest(TestCase):
    """Test authentication views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_view(self):
        """Test login view."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Should redirect to dashboard on success
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
    
    def test_login_failure(self):
        """Test failed login."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        # Should return 200 with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'didn&#x27;t match')
    
    def test_logout_view(self):
        """Test logout view."""
        # Login first
        self.client.login(username='testuser', password='testpass123')
        
        # Logout
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
    
    def test_register_view(self):
        """Test registration view."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
    
    def test_registration_success(self):
        """Test successful registration."""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'first_name': 'New',
            'last_name': 'User'
        })
        
        # Should redirect to dashboard on success
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check that user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_registration_failure(self):
        """Test failed registration."""
        response = self.client.post(reverse('register'), {
            'username': 'testuser',  # Already exists
            'email': 'test@example.com',
            'password1': 'pass',
            'password2': 'pass'  # Too simple
        })
        
        # Should return 200 with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')


class ExportViewsTest(TestCase):
    """Test export views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.region = Region.objects.create(
            name='Nairobi',
            country='Kenya',
            location=Point(36.8219, -1.2921)
        )
        
        # Create some climate data
        ClimateData.objects.create(
            region=self.region,
            timestamp=timezone.now(),
            temperature=22.5,
            humidity=65.0,
            rainfall=0.0,
            source='api'
        )
    
    def test_export_csv_view(self):
        """Test CSV export view."""
        response = self.client.get(reverse('export_climate_data_csv'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Check CSV content
        content = response.content.decode('utf-8')
        self.assertIn('Region', content)
        self.assertIn('Temperature', content)
        self.assertIn('Nairobi', content)
    
    def test_export_pdf_view(self):
        """Test PDF export view."""
        # This test would require weasyprint to be installed
        # We'll skip it for now and just test the redirect
        response = self.client.get(reverse('export_region_pdf', args=[self.region.id]))
        
        # Should either return PDF or redirect with error
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/pdf')
        else:
            # Might redirect with error message
            self.assertEqual(response.status_code, 302)