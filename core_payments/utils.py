import datetime
import calendar
import stripe
from django.db.models import F
from .models import StripeCustomer
from core.utils import load_credential
from app.settings import STRIPE_METER_ID, STRIPE_METER_EVENT_NAME


# v1 API
stripe.api_key = load_credential("STRIPE_SECRET_KEY")
# v2 API
stripe_client = stripe.StripeClient(load_credential("STRIPE_SECRET_KEY"))


def get_current_month_start_end():
    """
    Returns Unix timestamps for the first second of the current month at 00:00 UTC
    and the first second of the next month at 00:00 UTC.
    This ensures daily granularity alignment for Stripe Meters.
    """
    # Get the current date/time in UTC
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # First day (UTC) of the current month (00:00 UTC)
    first_day_utc = datetime.datetime(
        year=now_utc.year,
        month=now_utc.month,
        day=1,
        hour=0,
        minute=0,
        second=0,
        tzinfo=datetime.timezone.utc
    )

    # Number of days in the current month
    _, last_day_of_month = calendar.monthrange(now_utc.year, now_utc.month)

    # Last day (UTC) of the current month at 00:00 UTC
    # (We actually use the next day at 00:00 to include the full last day.)
    last_day_utc = datetime.datetime(
        year=now_utc.year,
        month=now_utc.month,
        day=last_day_of_month,
        hour=0,
        minute=0,
        second=0,
        tzinfo=datetime.timezone.utc
    )
    # Move to 00:00 UTC of the next day (i.e., the first day of the next month)
    end_of_month_utc = last_day_utc + datetime.timedelta(days=1)

    start_time = int(first_day_utc.timestamp())
    end_time = int(end_of_month_utc.timestamp())

    return start_time, end_time

def get_stripe_monthly_units_used(stripe_customer_id):
    # Get usage record summaries for the current billing period
    start_time, end_time = get_current_month_start_end()

    total_usage = 0
    last_id = None

    while True:
        # Fetch a page of event summaries
        event_summaries = stripe.billing.Meter.list_event_summaries(
            STRIPE_METER_ID,
            customer=stripe_customer_id,
            start_time=start_time,
            end_time=end_time,
            value_grouping_window="day",
            starting_after=last_id  # None on the first request
        )

        # Sum up the aggregated_value from each event in this page

        for event_summary in event_summaries.data:
            total_usage += event_summary.aggregated_value

        # If there are more pages, update last_id so we can fetch the next page
        if event_summaries.has_more:
            last_id = event_summaries.data[-1].id
        else:
            break
    return total_usage

def record_usage(user_id, stripe_customer_id, value, units_remaining):
    try:
        StripeCustomer.objects.filter(user=user_id).update(
            units_remaining=F('units_remaining') - value
        )
        # Record 1 unit of usage
        stripe.billing.MeterEvent.create(
            event_name=STRIPE_METER_EVENT_NAME,
            payload={
                "value": value,
                "stripe_customer_id": stripe_customer_id
            }
        )
        return True
    except Exception as e:
        return False