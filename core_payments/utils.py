import time
import stripe
from django.conf import settings
from .models import StripeCustomer
from core.utils import load_credential

stripe.api_key = load_credential("STRIPE_SECRET_KEY")

def get_stripe_subscription(user):
    try:
        stripe_customer = StripeCustomer.objects.get(user=user)
        return stripe.Subscription.retrieve(stripe_customer.stripe_subscription_id)
    except StripeCustomer.DoesNotExist:
        return None

def get_remaining_units(user):
    try:
        stripe_customer = StripeCustomer.objects.get(user=user)
        subscription = stripe.Subscription.retrieve(stripe_customer.stripe_subscription_id)
        
        # Get the current usage for this billing period
        usage_record = stripe.SubscriptionItem.list_usage_record_summaries(
            subscription.items.data[0].id,
            limit=1
        ).data[0]
        
        # Calculate remaining units (10 - used_units)
        used_units = usage_record.total_usage
        remaining_units = 10 - int(used_units)
        return max(remaining_units, 0)
    except Exception:
        return 0

def record_usage(user):
    try:
        stripe_customer = StripeCustomer.objects.get(user=user)
        subscription = stripe.Subscription.retrieve(stripe_customer.stripe_subscription_id)
        
        # Record 1 unit of usage
        stripe.SubscriptionItem.create_usage_record(
            subscription.items.data[0].id,
            quantity=1,
            timestamp=int(time.time()),
            action='increment'
        )
        return True
    except Exception:
        return False
