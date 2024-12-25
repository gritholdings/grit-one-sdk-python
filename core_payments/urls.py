from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('subscribe/', views.subscription_page, name='subscription_page'),
    path('success/', views.success_page, name='success_page'),
    path('create-subscription/', views.create_subscription, name='create_subscription'),
    path('get-usage/', views.get_usage, name='get_usage'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]
