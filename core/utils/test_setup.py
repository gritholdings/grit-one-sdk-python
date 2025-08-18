"""
Quick Start Example:
--------------------
# In your test file:
from core.utils.test_setup import initialize_test_setup, create_test_user, cleanup_test_user
initialize_test_setup()

class MyTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
    
    def tearDown(self):
        # Clean up test data to avoid conflicts
        cleanup_test_user(self.user)
        
    def test_something(self):
        # Your test here - everything is already mocked!
        pass
"""
import os
import django
import uuid
from unittest.mock import patch
from contextlib import ExitStack

# Global variables to store patchers and context
_stripe_patcher = None
_stack = None
_initialized = False

def initialize_test_setup():
    """
    Initialize all test dependencies with a single function call.
    This function sets up Django, mocks Stripe, and prepares the test environment.
    
    Usage:
        from core.util.test import initialize_test_setup
        initialize_test_setup()
    """
    global _stripe_patcher, _stack, _initialized
    
    if _initialized:
        return
    
    # Set up Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()
    
    # Create exit stack for managing multiple context managers
    _stack = ExitStack()
    
    # Mock Stripe Customer creation
    _stripe_patcher = patch(
        'core_payments.signals.stripe.Customer.create',
        return_value={'id': 'cus_mocked123', 'units_remaining': 1000}
    )
    _stack.enter_context(_stripe_patcher)
    
    # Mock Stripe price multiplier
    price_multiplier_patcher = patch('core_payments.utils.STRIPE_PRICE_MULTIPLIER', 100)
    _stack.enter_context(price_multiplier_patcher)
    
    # Add any other global mocks here
    # Example: Mock external API calls, timezone, etc.
    # _stack.enter_context(patch('requests.post', return_value=Mock(status_code=200)))
    # _stack.enter_context(patch('django.utils.timezone.now', return_value=datetime(2025, 1, 1)))
    
    _initialized = True
    
    # Return cleanup function
    return cleanup_test_setup


def cleanup_test_setup():
    """Clean up all test mocks and patches"""
    global _stack, _initialized
    
    if _stack:
        _stack.close()
        _stack = None
    
    _initialized = False


# Helper functions for creating test data
def create_test_user(email=None, password='testpass123', **kwargs):
    """Create a test user with default or custom attributes.
    Always use CustomUser model for consistency instead of User model."""
    from customauth.models import CustomUser
    if email is None:
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
    return CustomUser.objects.create(
        email=email,
        password=password,
        **kwargs
    )


def setup_stripe_customer(user, units_remaining=1000):
    """Set up a StripeCustomer for a user with specified units"""
    from core_payments.models import StripeCustomer
    stripe_customer = StripeCustomer.objects.get(user=user)
    stripe_customer.units_remaining = units_remaining
    stripe_customer.save()
    return stripe_customer


def cleanup_test_user(user):
    """Clean up a test user and all related objects
    
    Args:
        user: The user object to clean up
    """
    from core_payments.models import StripeCustomer, MetricDatum
    
    # Delete all related objects first
    MetricDatum.objects.filter(user=user).delete()
    StripeCustomer.objects.filter(user=user).delete()
    
    # Delete the user
    user.delete()