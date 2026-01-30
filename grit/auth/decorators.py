from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from grit.auth.settings import auth_settings


def verified_user_required(function=None):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if auth_settings.EMAIL_VERIFICATION == 'mandatory':
                if request.user.is_authenticated and not request.user.is_email_verified:
                    messages.warning(request, 'Please verify your email address to access this page.')
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
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and not request.user.is_email_verified:
                if message:
                    messages.warning(request, message)
                else:
                    messages.warning(request, 'Please verify your email address to access this page.')
                next_url = request.get_full_path()
                redirect_response = redirect(redirect_url)
                redirect_response['Location'] += f'?next={next_url}'
                return redirect_response
            return view_func(request, *args, **kwargs)
        return wrapped_view
    if function:
        return decorator(function)
    return decorator


class VerifiedUserRequiredMixin(LoginRequiredMixin):
    verification_redirect_url = 'resend_verification_email'
    verification_message = 'Please verify your email address to access this page.'
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if auth_settings.EMAIL_VERIFICATION == 'mandatory':
            if not request.user.is_email_verified:
                messages.warning(request, self.verification_message)
                return redirect(self.verification_redirect_url)
        return super().dispatch(request, *args, **kwargs)


class EmailVerifiedRequiredMixin:
    verification_redirect_url = 'resend_verification_email'
    verification_message = 'Please verify your email address to access this page.'
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_email_verified:
            messages.warning(request, self.verification_message)
            return redirect(self.verification_redirect_url)
        return super().dispatch(request, *args, **kwargs)