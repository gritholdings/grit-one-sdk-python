import os
import django
import uuid
from unittest.mock import patch
from contextlib import ExitStack
_stripe_patcher = None
_stack = None
_initialized = False


def initialize_test_setup():
    global _stripe_patcher, _stack, _initialized
    if _initialized:
        return
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grit.core.settings")
    django.setup()
    _stack = ExitStack()
    _stripe_patcher = patch(
        'grit.payments.signals.stripe.Customer.create',
        return_value={'id': 'cus_mocked123', 'units_remaining': 1000}
    )
    _stack.enter_context(_stripe_patcher)
    price_multiplier_patcher = patch('grit.payments.utils.STRIPE_PRICE_MULTIPLIER', 100)
    _stack.enter_context(price_multiplier_patcher)
    _initialized = True
    return cleanup_test_setup


def cleanup_test_setup():
    global _stack, _initialized
    if _stack:
        _stack.close()
        _stack = None
    _initialized = False


def create_test_user(email=None, password='testpass123', **kwargs):
    from grit.auth.models import CustomUser
    if email is None:
        email = f'test_{uuid.uuid4().hex[:8]}@example.com'
    return CustomUser.objects.create(
        email=email,
        password=password,
        **kwargs
    )


def setup_stripe_customer(user, units_remaining=1000):
    from grit.payments.models import StripeCustomer
    stripe_customer = StripeCustomer.objects.get(user=user)
    stripe_customer.units_remaining = units_remaining
    stripe_customer.save()
    return stripe_customer


def cleanup_test_user(user):
    from grit.payments.models import StripeCustomer, MetricDatum
    MetricDatum.objects.filter(user=user).delete()
    StripeCustomer.objects.filter(user=user).delete()
    user.delete()