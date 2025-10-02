from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from customauth.settings import auth_settings


def verified_user_required(function=None):
    """
    Decorator that requires login and conditionally requires email verification
    based on the EMAIL_VERIFICATION setting.

    Behavior:
    - When EMAIL_VERIFICATION = 'mandatory': Requires both login and email verification
    - When EMAIL_VERIFICATION = 'optional' or 'skip': Only requires login

    Usage:
        @verified_user_required
        def my_view(request):
            ...

        @verified_user_required(redirect_url='custom_verify_page', message='Custom message')
        def another_view(request):
            ...
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Only check email verification if it's mandatory
            if auth_settings.EMAIL_VERIFICATION == 'mandatory':
                if request.user.is_authenticated and not request.user.is_email_verified:
                    messages.warning(request, 'Please verify your email address to access this page.')
                    # Preserve the original URL they were trying to access
                    next_url = request.get_full_path()
                    redirect_response = redirect('send_verification_email')
                    redirect_response['Location'] += f'?next={next_url}'
                    return redirect_response

            return view_func(request, *args, **kwargs)

        return wrapped_view

    if function:
        return decorator(function)
    return decorator


def email_verified_required(function=None, redirect_url='send_verification_email', message=None):
    """
    Decorator that only checks email verification (assumes user is already logged in).
    Use this when you already have @login_required from elsewhere.

    Usage:
        @login_required  # From Django
        @email_verified_required
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and not request.user.is_email_verified:
                if message:
                    messages.warning(request, message)
                else:
                    messages.warning(request, 'Please verify your email address to access this page.')

                # Preserve the original URL they were trying to access
                next_url = request.get_full_path()
                redirect_response = redirect(redirect_url)
                redirect_response['Location'] += f'?next={next_url}'
                return redirect_response

            return view_func(request, *args, **kwargs)
        return wrapped_view

    if function:
        return decorator(function)
    return decorator


# For class-based views
class VerifiedUserRequiredMixin(LoginRequiredMixin):
    """
    Mixin for class-based views that requires login and conditionally requires
    email verification based on the EMAIL_VERIFICATION setting.

    Behavior:
    - When EMAIL_VERIFICATION = 'mandatory': Requires both login and email verification
    - When EMAIL_VERIFICATION = 'optional' or 'skip': Only requires login

    Usage:
        class PaymentView(VerifiedUserRequiredMixin, View):
            verification_redirect_url = 'resend_verification_email'
            verification_message = 'Verify your email to access payments.'
            ...
    """
    verification_redirect_url = 'resend_verification_email'
    verification_message = 'Please verify your email address to access this page.'

    def dispatch(self, request, *args, **kwargs):
        # First check login (handled by LoginRequiredMixin)
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Only check email verification if it's mandatory
        if auth_settings.EMAIL_VERIFICATION == 'mandatory':
            if not request.user.is_email_verified:
                messages.warning(request, self.verification_message)
                return redirect(self.verification_redirect_url)

        return super().dispatch(request, *args, **kwargs)


class EmailVerifiedRequiredMixin:
    """
    Standalone mixin for email verification (use with LoginRequiredMixin).

    Usage:
        class PaymentView(LoginRequiredMixin, EmailVerifiedRequiredMixin, View):
            ...
    """
    verification_redirect_url = 'resend_verification_email'
    verification_message = 'Please verify your email address to access this page.'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_email_verified:
            messages.warning(request, self.verification_message)
            return redirect(self.verification_redirect_url)
        return super().dispatch(request, *args, **kwargs)