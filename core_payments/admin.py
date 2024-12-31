from django.contrib import admin
from customauth.models import CustomUser
from customauth.admin import CustomUserAdmin
from .models import StripeCustomer


class StripeCustomerInline(admin.StackedInline):
    model = StripeCustomer
    can_delete = False

class CustomUserAdminWithPayments(CustomUserAdmin):
    """Extend the existing CustomUserAdmin to include StripeCustomerInline."""
    inlines = [StripeCustomerInline]

# Unregister the original admin, then register the new one with the payment inline
admin.site.unregister(CustomUser)
admin.site.register(CustomUser, CustomUserAdminWithPayments)