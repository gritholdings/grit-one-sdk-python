import json
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import StripeCustomer
from .utils import get_remaining_units
from core.utils import load_credential

stripe.api_key = load_credential("STRIPE_SECRET_KEY")

@login_required
def subscription_page(request):
    return render(request, 'core_payments/create_subscription.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })

@login_required
def success_page(request):
    return render(request, 'core_payments/success.html')

@csrf_exempt
@login_required
def create_subscription(request):
    try:
        # Parse JSON data from request body
        data = json.loads(request.body.decode('utf-8'))
        stripe_token = data.get('stripeToken')
        
        if not stripe_token:
            return JsonResponse({'error': 'stripeToken is required'}, status=400)
            
        # Get or create StripeCustomer
        stripe_customer, created = StripeCustomer.objects.get_or_create(
            user=request.user,
            defaults={'stripe_customer_id': None, 'stripe_subscription_id': None}
        )
        
        if not stripe_customer.stripe_customer_id:
            # Create new Stripe customer if none exists
            customer = stripe.Customer.create(
                email=request.user.email,
                source=stripe_token
            )
            stripe_customer.stripe_customer_id = customer.id
            stripe_customer.save()
        else:
            # Use existing Stripe customer
            customer = stripe.Customer.retrieve(stripe_customer.stripe_customer_id)
            if stripe_token:
                # Update payment source if provided
                customer.source = stripe_token
                customer.save()
        
        # Create subscription with metered billing
        subscription = stripe.Subscription.create(
            customer=stripe_customer.stripe_customer_id,
            items=[{
                'price': settings.STRIPE_PRICE_ID,  # $10/month base price
                'quantity': 1
            }],
            expand=['latest_invoice.payment_intent']
        )
        
        # Update subscription info
        stripe_customer.stripe_subscription_id = subscription.id
        stripe_customer.save()
        
        return JsonResponse({
            'subscription': subscription.id,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def get_usage(request):
    try:
        # 1. Look up the StripeCustomer entry for the current user
        stripe_customer = StripeCustomer.objects.get(user=request.user)
        # 2. Retrieve the Customer in Stripe (not strictly needed
        #    unless you want to confirm the customer still exists, etc.)
        customer = stripe.Customer.retrieve(stripe_customer.stripe_customer_id)

        # 3. Retrieve the Subscription that has metered billing
        subscription = stripe.Subscription.retrieve(stripe_customer.stripe_subscription_id)

        # 4. Identify the Subscription Item ID that is "metered"
        #    (Assuming the subscription has a single item. If you have multiple items,
        #    find the one with metered pricing.)
        subscription_item_id = subscription['items'].data[0].id

        # 5. Get usage record summaries for the current billing period
        usage_record_summaries = stripe.SubscriptionItem.list_usage_record_summaries(
            subscription_item=subscription_item_id,
            limit=100  # adjust as needed
        )

        total_usage = 0
        for summary in usage_record_summaries.auto_paging_iter():
            total_usage += summary.total_usage

        # Example: Suppose each user is allowed 1000 "units" per month
        monthly_allowance = 1000
        remaining_credits = monthly_allowance - total_usage

        return JsonResponse({
            'total_usage': total_usage,
            'remaining_credits': max(remaining_credits, 0)  # Avoid negative if usage goes over
        })

    except StripeCustomer.DoesNotExist:
        return JsonResponse({
            'error': 'No Stripe Customer found for this user.'
        }, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event.type == 'invoice.payment_succeeded':
            # Handle successful payment
            pass
        elif event.type == 'customer.subscription.deleted':
            # Handle subscription cancellation
            pass
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
