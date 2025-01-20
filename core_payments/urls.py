from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout_page'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session_page'),
    path('create-billing-portal-session/', views.create_billing_portal_session, name='create_billing_portal_session_page'),
    path('success/', views.success_page, name='success_page'),
    path('create-subscription/', views.create_subscription, name='create_subscription'),
    path('get-usage/', views.get_usage, name='get_usage'),
    path('record-usage/', views.record_usage_views, name='record_usage'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]