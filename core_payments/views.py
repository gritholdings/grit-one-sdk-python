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
        stripe_customer = StripeCustomer.objects.get(user=request.user)
        customer = stripe.Customer.retrieve(stripe_customer.stripe_customer_id)
        available_credits = abs(customer.balance) / 100  # Convert from cents to dollars
    except StripeCustomer.DoesNotExist:
        available_credits = 0
        
    return JsonResponse({
        'available_credits': available_credits
    })

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
