import json
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from .models import StripeCustomer
from .utils import record_usage
from core.utils import load_credential
from core.settings import DJANGO_ENV
from app.settings import DOMAIN_NAME, SUBDOMAIN_NAME, STRIPE_PRICE_ID

stripe.api_key = load_credential("STRIPE_SECRET_KEY")

if DJANGO_ENV != 'PROD':
    DOMAIN_NAME = "http://127.0.0.1:8000"
else:
    DOMAIN_NAME = f"https://{SUBDOMAIN_NAME}.{DOMAIN_NAME}"

@login_required
def checkout(request):
    return render(request, 'core_payments/checkout.html', {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })

def create_checkout_session(request):
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': STRIPE_PRICE_ID
                },
            ],
            mode='subscription',
            success_url=DOMAIN_NAME + '/success.html',
            cancel_url=DOMAIN_NAME + '/payments/checkout',
        )
    except Exception as e:
        # Handle the error gracefully
        return JsonResponse({'error': str(e)}, status=400)

    # Redirect the user to the checkout_session's URL
    return redirect(checkout_session.url, code=303)

@login_required
def create_billing_portal_session(request):
    try:
        user =request.user
        stripe_customer_id = user.stripecustomer.stripe_customer_id

        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=DOMAIN_NAME + '/payments/checkout'
        )

        return redirect(portal_session.url, code=303)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

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
        user = request.user
        units_remaining = user.stripecustomer.units_remaining

        return JsonResponse({
            'remaining_units': units_remaining
        })

    except StripeCustomer.DoesNotExist:
        return JsonResponse({
            'error': 'No Stripe Customer found for this user.'
        }, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def record_usage_views(request):
    try:
        user = request.user
        user_id = user.id
        stripe_customer_id = user.stripecustomer.stripe_customer_id
        units_remaining = user.stripecustomer.units_remaining
        success = record_usage(user_id, stripe_customer_id, int("100"), units_remaining)
        
        if success:
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'error': 'No remaining units'}, status=400)
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
