"""
Context processors for the climate application.
"""

from django.conf import settings


def language_switcher(request):
    """
    Add language switching context to all templates.
    """
    current_language = getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE)
    
    # Swahili/English translations for menu items
    translations = {
        'en': {
            'app_name': 'Mazingira Insight AI',
            'dashboard': 'Dashboard',
            'map': 'Map',
            'carbon': 'Carbon Calculator',
            'history': 'History',
            'reports': 'Reports',
            'login': 'Login',
            'register': 'Register',
            'logout': 'Logout',
            'language': 'Language',
            'english': 'English',
            'swahili': 'Swahili',
        },
        'sw': {
            'app_name': 'Mazingira Insight AI',
            'dashboard': 'Dashibodi',
            'map': 'Ramani',
            'carbon': 'Kikokotoo cha Kaboni',
            'history': 'Historia',
            'reports': 'Ripoti',
            'login': 'Ingia',
            'register': 'Jisajili',
            'logout': 'Toka',
            'language': 'Lugha',
            'english': 'Kiingereza',
            'swahili': 'Kiswahili',
        }
    }
    
    # Get translations for current language
    menu_translations = translations.get(current_language, translations['en'])
    
    return {
        'current_language': current_language,
        'menu_translations': menu_translations,
        'available_languages': [
            ('en', 'English'),
            ('sw', 'Swahili'),
        ]
    }