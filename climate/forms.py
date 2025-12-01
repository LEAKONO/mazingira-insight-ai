"""
Forms for the climate monitoring application.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CarbonFootprint, EnvironmentalReport


class UserRegistrationForm(UserCreationForm):
    """
    Form for user registration with additional fields.
    """
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    organization = forms.CharField(max_length=100, required=False, help_text="Optional: Your organization name")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class CarbonCalculatorForm(forms.ModelForm):
    """
    Form for carbon footprint calculation.
    """
    # Transportation
    car_type = forms.ChoiceField(
        choices=[
            ('petrol', 'Petrol Car'),
            ('diesel', 'Diesel Car'),
            ('hybrid', 'Hybrid Car'),
            ('electric', 'Electric Car'),
            ('none', 'No Car'),
        ],
        initial='petrol',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    car_km = forms.FloatField(
        min_value=0,
        initial=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weekly km'})
    )
    public_transport_km = forms.FloatField(
        min_value=0,
        initial=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weekly km'})
    )
    
    # Household
    household_size = forms.IntegerField(
        min_value=1,
        initial=4,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    renewable_energy = forms.ChoiceField(
        choices=[
            ('none', 'No Renewable Energy'),
            ('some', 'Some Solar/Wind'),
            ('most', 'Mostly Renewable'),
            ('all', '100% Renewable'),
        ],
        initial='none',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Lifestyle
    flights_hours = forms.FloatField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Hours per year'})
    )
    
    class Meta:
        model = CarbonFootprint
        fields = ['transport_km', 'electricity_kwh', 'diet_type', 'waste_kg']
        widgets = {
            'transport_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'electricity_kwh': forms.NumberInput(attrs={'class': 'form-control'}),
            'diet_type': forms.Select(attrs={'class': 'form-select'}),
            'waste_kg': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'transport_km': 'Weekly Transport (km)',
            'electricity_kwh': 'Monthly Electricity (kWh)',
            'diet_type': 'Diet Type',
            'waste_kg': 'Weekly Waste (kg)',
        }


class EnvironmentalReportForm(forms.ModelForm):
    """
    Form for submitting environmental reports.
    """
    class Meta:
        model = EnvironmentalReport
        fields = ['report_type', 'title', 'description', 'region', 'latitude', 'longitude', 'photo', 'is_public']
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title of the issue'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description...'}),
            'region': forms.Select(attrs={'class': 'form-select'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make latitude and longitude not required for form submission
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False


class ClimateQueryForm(forms.Form):
    """
    Form for querying climate data.
    """
    region = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    data_type = forms.ChoiceField(
        choices=[
            ('temperature', 'Temperature'),
            ('rainfall', 'Rainfall'),
            ('humidity', 'Humidity'),
            ('air_quality', 'Air Quality'),
            ('all', 'All Data'),
        ],
        initial='temperature',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Region
        self.fields['region'].queryset = Region.objects.all()