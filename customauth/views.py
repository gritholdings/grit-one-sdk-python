import logging
from smtplib import SMTPException, SMTPAuthenticationError, SMTPServerDisconnected, SMTPRecipientsRefused
from django.contrib.auth import logout, login, authenticate, views as auth_views
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.utils.env_config import get_base_url
from core.utils.time_utils import get_cooldown_remaining_seconds, format_remaining_time
from .forms import (
    SignUpForm, EmailAuthenticationForm, CustomPasswordChangeForm, CustomPasswordResetForm,
    CustomSetPasswordForm
)
from .tokens import email_verification_token
from .models import CustomUser
from .settings import auth_settings

# Configure logger for this module
logger = logging.getLogger(__name__)


def custom_logout_view(request):
    logout(request)
    return redirect('index')

@api_view(['POST'])
def is_authenticated(request):
    # check if user is authenticated
    user = request.user
    if user.is_authenticated:
        return Response({
            'is_authenticated': True,
            'user_id': user.id,
            'email': user.email,
            'is_email_verified': user.is_email_verified
        })
    else:
        return Response({'is_authenticated': False})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(email=user.email, password=raw_password)
            login(request, user)

            # Send verification email
            try:
                send_verification_email(user)
                messages.success(
                    request,
                    'Account created successfully! Please check your email to verify your address.'
                )
            except Exception as e:
                # Log the error but don't prevent signup
                messages.warning(
                    request,
                    'Account created successfully! However, we could not send the verification email. '
                    'Please use the resend option to get a new verification link.'
                )

            return redirect('index')
    else:
        form = SignUpForm()
    return render(request, 'customauth/signup.html', {'form': form})


class CustomLoginView(auth_views.LoginView):
    template_name = 'customauth/login.html'
    form_class = EmailAuthenticationForm


def custom_login_view(request):
    return CustomLoginView.as_view()(request)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'account/password_change.html'
    success_url = reverse_lazy('password_change_done')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password was successfully updated!')
        return super().form_valid(form)


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'customauth/password_reset_form.html'
    form_class = CustomPasswordResetForm
    html_email_template_name = 'customauth/password_reset_email.html'
    extra_email_context = {'base_url': get_base_url()}

    def form_valid(self, form):
        messages.success(self.request, 'Password reset email sent successfully!')
        return super().form_valid(form)


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'customauth/password_reset_confirm.html'
    form_class = CustomSetPasswordForm

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been set successfully!')
        return super().form_valid(form)


def send_verification_email(user):
    """
    Send email verification link to the user.

    This function generates a verification token and sends an email
    with a link to verify the user's email address.
    """
    # Generate verification token
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Build verification URL
    base_url = get_base_url()
    verification_url = f"{base_url}{reverse('verify_email', kwargs={'uidb64': uid, 'token': token})}"

    # Prepare email content
    subject = 'Please Confirm Your Email Address'
    context = {
        'user': user,
        'activate_url': verification_url,  # Use activate_url to match existing template
        'base_url': base_url,
    }

    # Render HTML email template
    html_message = render_to_string('customauth/email_verification_message.html', context)

    # Send email (empty string for plain text since we're only using HTML)
    send_mail(
        subject=subject,
        message='',  # Empty plain text message
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )

    # Update user's email verification sent timestamp
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=['email_verification_sent_at'])


def verify_email(request, uidb64, token):
    """
    Verify user's email address using the token from the verification link.

    This view handles the verification link clicks and validates the token.
    """
    try:
        # Decode user ID from base64
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        # Token is valid - verify the email
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])

            # Auto-login the user if they're not already logged in
            if not request.user.is_authenticated:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Render the success page
            return render(request, 'customauth/email_verification_complete.html', {'user': user})
        else:
            # Email is already verified
            messages.info(request, 'Your email is already verified.')
            return redirect('index')
    else:
        # Invalid token
        messages.error(request, 'The verification link is invalid or has expired. Please request a new verification email.')
        return render(request, 'customauth/email_verification_invalid.html')


@login_required
def send_verification_email_view(request):
    """
    Send verification email to the logged-in user.

    Includes rate limiting to prevent spam.
    """
    user = request.user
    context = {}

    # Check if email is already verified
    if user.is_email_verified:
        messages.info(request, 'Your email is already verified.')
        context['email_verified'] = True
        return render(request, 'customauth/email_verification_send.html', context)

    # Calculate remaining cooldown time
    remaining_seconds = get_cooldown_remaining_seconds(
        user.email_verification_sent_at,
        auth_settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
    )

    # Rate limiting: Check if we can send another email
    if remaining_seconds > 0:
        formatted_time = format_remaining_time(remaining_seconds)
        messages.warning(
            request,
            f'Please wait {formatted_time} before requesting another verification email.'
        )
        context['cooldown_active'] = True
        context['remaining_seconds'] = remaining_seconds
        return render(request, 'customauth/email_verification_send.html', context)

    # Send verification email
    try:
        send_verification_email(user)
        messages.success(request, 'Verification email has been sent. Please check your inbox.')
        # After sending, cooldown will be active based on configured setting
        context['cooldown_active'] = True
        context['remaining_seconds'] = auth_settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
    except (SMTPException, BadHeaderError) as e:
        # Log the specific error with appropriate severity
        log_level = logging.CRITICAL if not isinstance(e, (SMTPException, BadHeaderError)) else logging.ERROR
        error_type = type(e).__name__

        logger.log(
            log_level,
            f"{error_type} when sending verification email to {user.email} (user_id: {user.id}): {str(e)}",
            exc_info=True,
            extra={'user_id': user.id, 'email': user.email, 'error_type': error_type}
        )

        # Provide a user-friendly error message
        messages.error(request, 'Failed to send verification email. Please try again later or contact support if this persists.')
    except Exception as e:
        # Catch any other unexpected exceptions
        logger.critical(
            f"Unexpected error when sending verification email to {user.email} (user_id: {user.id}): {str(e)}",
            exc_info=True,
            extra={'user_id': user.id, 'email': user.email, 'error_type': type(e).__name__}
        )
        messages.error(request, 'An unexpected error occurred. Please contact support if this persists.')

    return render(request, 'customauth/email_verification_send.html', context)


def verification_email_sent(request):
    """
    Display a page confirming that verification email has been sent.
    """
    return render(request, 'customauth/email_verification_sent.html')