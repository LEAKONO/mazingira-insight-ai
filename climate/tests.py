"""
Main test module for climate app.
All tests are organized in the tests/ directory.
This file imports all tests for easy running.
"""

# Import all test modules
from .tests.test_models import *
from .tests.test_views import *
from .tests.test_api import *

# You can run all tests with: python manage.py test climate