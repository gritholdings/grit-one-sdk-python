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
from datetime import datetime, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from grit.core.utils.env_config import get_base_url
from grit.core.utils.time_utils import get_cooldown_remaining_seconds, format_remaining_time
from django.contrib.auth.hashers import make_password, check_password as check_password_hash
from .forms import (
    SignUpForm, EmailAuthenticationForm, CustomPasswordChangeForm, CustomPasswordResetForm,
    CustomSetPasswordForm, MFAVerifyForm, MFADisableForm
)
from .tokens import email_verification_token
from .models import CustomUser, UserSession, MFADevice, BackupCode
from .settings import auth_settings
from .mfa import generate_otp_code, send_mfa_email, generate_backup_codes, hash_backup_code, check_backup_code
logger = logging.getLogger(__name__)


def custom_logout_view(request):
    logout(request)
    return redirect('index')
@api_view(['POST'])


def is_authenticated(request):
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
            try:
                send_verification_email(user)
                messages.success(
                    request,
                    'Account created successfully! Please check your email to verify your address.'
                )
            except Exception as e:
                messages.warning(
                    request,
                    'Account created successfully! However, we could not send the verification email. '
                    'Please use the resend option to get a new verification link.'
                )
            return redirect(auth_settings.SIGNUP_REDIRECT_URL)
    else:
        form = SignUpForm()
    return render(request, 'customauth/signup.html', {'form': form})


def custom_login_view(request):
    if request.method != 'POST':
        form = EmailAuthenticationForm()
        return render(request, 'customauth/login.html', {'form': form})
    form = EmailAuthenticationForm(request, data=request.POST)
    if not form.is_valid():
        return render(request, 'customauth/login.html', {'form': form})
    user = form.get_user()
    if user.mfa_devices.filter(is_active=True).exists():
        request.session['_mfa_user_id'] = str(user.pk)
        request.session['_mfa_backend'] = 'grit.auth.backends.EmailBackend'
        code = generate_otp_code()
        request.session['_mfa_code_hash'] = make_password(code)
        request.session['_mfa_code_expires'] = (
            timezone.now() + timedelta(seconds=auth_settings.MFA_CODE_EXPIRY_SECONDS)
        ).isoformat()
        send_mfa_email(user.email, code)
        return redirect('mfa_verify')
    login(request, user)
    return redirect(settings.LOGIN_REDIRECT_URL)


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
    token = email_verification_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    base_url = get_base_url()
    verification_url = f"{base_url}{reverse('verify_email', kwargs={'uidb64': uid, 'token': token})}"
    subject = 'Please Confirm Your Email Address'
    context = {
        'user': user,
        'activate_url': verification_url,
        'base_url': base_url,
    }
    html_message = render_to_string('customauth/email_verification_message.html', context)
    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=['email_verification_sent_at'])


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and email_verification_token.check_token(user, token):
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
            if not request.user.is_authenticated:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return render(request, 'customauth/email_verification_complete.html', {'user': user})
        else:
            messages.info(request, 'Your email is already verified.')
            return redirect('index')
    else:
        messages.error(request, 'The verification link is invalid or has expired. Please request a new verification email.')
        return render(request, 'customauth/email_verification_invalid.html')
@login_required


def send_verification_email_view(request):
    user = request.user
    context = {}
    if user.is_email_verified:
        messages.info(request, 'Your email is already verified.')
        context['email_verified'] = True
        return render(request, 'customauth/email_verification_send.html', context)
    remaining_seconds = get_cooldown_remaining_seconds(
        user.email_verification_sent_at,
        auth_settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
    )
    if remaining_seconds > 0:
        formatted_time = format_remaining_time(remaining_seconds)
        messages.warning(
            request,
            f'Please wait {formatted_time} before requesting another verification email.'
        )
        context['cooldown_active'] = True
        context['remaining_seconds'] = remaining_seconds
        return render(request, 'customauth/email_verification_send.html', context)
    try:
        send_verification_email(user)
        messages.success(request, 'Verification email has been sent. Please check your inbox.')
        context['cooldown_active'] = True
        context['remaining_seconds'] = auth_settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
    except (SMTPException, BadHeaderError) as e:
        log_level = logging.CRITICAL if not isinstance(e, (SMTPException, BadHeaderError)) else logging.ERROR
        error_type = type(e).__name__
        logger.log(
            log_level,
            f"{error_type} when sending verification email to {user.email} (user_id: {user.id}): {str(e)}",
            exc_info=True,
            extra={'user_id': user.id, 'email': user.email, 'error_type': error_type}
        )
        messages.error(request, 'Failed to send verification email. Please try again later or contact support if this persists.')
    except Exception as e:
        logger.critical(
            f"Unexpected error when sending verification email to {user.email} (user_id: {user.id}): {str(e)}",
            exc_info=True,
            extra={'user_id': user.id, 'email': user.email, 'error_type': type(e).__name__}
        )
        messages.error(request, 'An unexpected error occurred. Please contact support if this persists.')
    return render(request, 'customauth/email_verification_send.html', context)


def verification_email_sent(request):
    return render(request, 'customauth/email_verification_sent.html')


def _parse_device_info(user_agent):
    ua = user_agent.lower()
    if 'macintosh' in ua or 'mac os' in ua:
        os_name = 'macOS'
    elif 'windows' in ua:
        os_name = 'Windows'
    elif 'linux' in ua:
        os_name = 'Linux'
    elif 'android' in ua:
        os_name = 'Android'
    elif 'iphone' in ua or 'ipad' in ua:
        os_name = 'iOS'
    else:
        os_name = 'Unknown OS'
    if 'edg/' in ua:
        browser = 'Edge'
    elif 'chrome' in ua and 'chromium' not in ua:
        browser = 'Chrome'
    elif 'firefox' in ua:
        browser = 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        browser = 'Safari'
    else:
        browser = 'Unknown browser'
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        device_type = 'phone'
    elif 'ipad' in ua or 'tablet' in ua:
        device_type = 'tablet'
    else:
        device_type = 'computer'
    return {
        'os': os_name,
        'browser': browser,
        'device_type': device_type,
        'label': f"{browser} on {os_name}",
    }
@login_required


def device_list(request):
    current_session_key = request.session.session_key
    sessions = UserSession.objects.filter(user=request.user).order_by('-last_active_at')
    now = timezone.now()
    session_data = []
    for session in sessions:
        info = _parse_device_info(session.user_agent)
        is_current = session.session_key == current_session_key
        session_data.append({
            'session': session,
            'is_current': is_current,
            'device_info': info,
            'inactive_days': (now - session.last_active_at).days if session.last_active_at else None,
        })
    groups = {}
    for item in session_data:
        key = f"{item['device_info']['device_type']}_{item['device_info']['os']}"
        groups.setdefault(key, {
            'device_type': item['device_info']['device_type'],
            'os': item['device_info']['os'],
            'sessions': [],
        })
        groups[key]['sessions'].append(item)
    mfa_enabled = request.user.mfa_devices.filter(is_active=True).exists()
    return render(request, 'customauth/devices.html', {
        'groups': groups.values(),
        'session_data': session_data,
        'mfa_enabled': mfa_enabled,
    })
@login_required


def sign_out_session(request, session_id):
    if request.method != 'POST':
        return redirect('device_list')
    try:
        session = UserSession.objects.get(
            id=session_id,
            user=request.user,
            status=UserSession.Status.ACTIVE,
        )
    except UserSession.DoesNotExist:
        messages.error(request, 'Session not found.')
        return redirect('device_list')
    if session.session_key == request.session.session_key:
        messages.warning(request, 'Use the regular sign-out to end your current session.')
        return redirect('device_list')
    session.sign_out()
    messages.success(request, 'Session signed out successfully.')
    return redirect('device_list')
@login_required


def sign_out_all_other_sessions(request):
    if request.method != 'POST':
        return redirect('device_list')
    current_session_key = request.session.session_key
    other_sessions = UserSession.objects.filter(
        user=request.user,
        status=UserSession.Status.ACTIVE,
    ).exclude(session_key=current_session_key)
    count = 0
    for session in other_sessions:
        session.sign_out()
        count += 1
    if count:
        messages.success(request, f'Signed out {count} other session(s).')
    else:
        messages.info(request, 'No other active sessions to sign out.')
    return redirect('device_list')
@login_required


def mfa_setup_view(request):
    if request.user.mfa_devices.filter(is_active=True).exists():
        messages.info(request, 'MFA is already enabled.')
        return redirect('device_list')
    if request.method == 'GET':
        code = generate_otp_code()
        request.session['_mfa_setup_code_hash'] = make_password(code)
        request.session['_mfa_setup_code_expires'] = (
            timezone.now() + timedelta(seconds=auth_settings.MFA_CODE_EXPIRY_SECONDS)
        ).isoformat()
        send_mfa_email(request.user.email, code)
        form = MFAVerifyForm()
        return render(request, 'customauth/mfa_setup.html', {'form': form})
    form = MFAVerifyForm(request.POST)
    if not form.is_valid():
        return render(request, 'customauth/mfa_setup.html', {'form': form})
    code = form.cleaned_data['code']
    expires = request.session.get('_mfa_setup_code_expires')
    if expires and timezone.now() > datetime.fromisoformat(expires):
        messages.error(request, 'Code has expired. Please try again.')
        return redirect('mfa_setup')
    code_hash = request.session.get('_mfa_setup_code_hash')
    if code_hash and check_password_hash(code, code_hash):
        MFADevice.objects.create(
            user=request.user, is_active=True, method='email', name='Email OTP',
        )
        plaintext_codes = generate_backup_codes(count=auth_settings.MFA_BACKUP_CODE_COUNT)
        for c in plaintext_codes:
            BackupCode.objects.create(user=request.user, code_hash=hash_backup_code(c))
        request.session.pop('_mfa_setup_code_hash', None)
        request.session.pop('_mfa_setup_code_expires', None)
        messages.success(request, 'MFA has been enabled. Save your backup codes below.')
        return render(request, 'customauth/mfa_backup_codes.html', {'codes': plaintext_codes})
    messages.error(request, 'Invalid code. Please try again.')
    return redirect('mfa_setup')
@login_required


def mfa_disable_view(request):
    if request.method != 'POST':
        form = MFADisableForm()
        return render(request, 'customauth/mfa_disable.html', {'form': form})
    form = MFADisableForm(request.POST)
    if not form.is_valid():
        return render(request, 'customauth/mfa_disable.html', {'form': form})
    if request.user.check_password(form.cleaned_data['password']):
        request.user.mfa_devices.all().delete()
        request.user.backup_codes.all().delete()
        messages.success(request, 'MFA has been disabled.')
        return redirect('device_list')
    messages.error(request, 'Incorrect password.')
    return render(request, 'customauth/mfa_disable.html', {'form': form})
@login_required


def mfa_backup_codes_view(request):
    if request.method != 'POST':
        form = MFADisableForm()
        return render(request, 'customauth/mfa_regenerate_backup_codes.html', {'form': form})
    form = MFADisableForm(request.POST)
    if not form.is_valid():
        return render(request, 'customauth/mfa_regenerate_backup_codes.html', {'form': form})
    if request.user.check_password(form.cleaned_data['password']):
        request.user.backup_codes.all().delete()
        plaintext_codes = generate_backup_codes(count=auth_settings.MFA_BACKUP_CODE_COUNT)
        for c in plaintext_codes:
            BackupCode.objects.create(user=request.user, code_hash=hash_backup_code(c))
        messages.success(request, 'New backup codes generated. Save them now.')
        return render(request, 'customauth/mfa_backup_codes.html', {'codes': plaintext_codes})
    messages.error(request, 'Incorrect password.')
    return render(request, 'customauth/mfa_regenerate_backup_codes.html', {'form': form})


def mfa_verify_view(request):
    user_id = request.session.get('_mfa_user_id')
    if not user_id:
        return redirect('login')
    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return redirect('login')
    if request.method != 'POST':
        form = MFAVerifyForm()
        return render(request, 'customauth/mfa_verify.html', {'form': form})
    form = MFAVerifyForm(request.POST)
    if not form.is_valid():
        return render(request, 'customauth/mfa_verify.html', {'form': form})
    code = form.cleaned_data['code']
    expires = request.session.get('_mfa_code_expires')
    if expires and timezone.now() > datetime.fromisoformat(expires):
        messages.error(request, 'Code has expired. Please request a new one.')
        return render(request, 'customauth/mfa_verify.html', {'form': MFAVerifyForm()})
    code_hash = request.session.get('_mfa_code_hash')
    if code_hash and check_password_hash(code, code_hash):
        backend = request.session.pop('_mfa_backend')
        request.session.pop('_mfa_user_id')
        request.session.pop('_mfa_code_hash', None)
        request.session.pop('_mfa_code_expires', None)
        login(request, user, backend=backend)
        _store_mfa_session_metadata(request, 'email')
        return redirect(settings.LOGIN_REDIRECT_URL)
    for backup in user.backup_codes.filter(is_used=False):
        if check_backup_code(code, backup.code_hash):
            backup.is_used = True
            backup.save(update_fields=['is_used'])
            remaining = user.backup_codes.filter(is_used=False).count()
            backend = request.session.pop('_mfa_backend')
            request.session.pop('_mfa_user_id')
            request.session.pop('_mfa_code_hash', None)
            request.session.pop('_mfa_code_expires', None)
            login(request, user, backend=backend)
            _store_mfa_session_metadata(request, 'backup_code')
            messages.warning(request, f'Backup code used. You have {remaining} codes left.')
            return redirect(settings.LOGIN_REDIRECT_URL)
    messages.error(request, 'Invalid code. Please try again.')
    return render(request, 'customauth/mfa_verify.html', {'form': MFAVerifyForm()})


def mfa_resend_view(request):
    user_id = request.session.get('_mfa_user_id')
    if not user_id:
        return redirect('login')
    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return redirect('login')
    code = generate_otp_code()
    request.session['_mfa_code_hash'] = make_password(code)
    request.session['_mfa_code_expires'] = (
        timezone.now() + timedelta(seconds=auth_settings.MFA_CODE_EXPIRY_SECONDS)
    ).isoformat()
    send_mfa_email(user.email, code)
    messages.info(request, 'A new code has been sent to your email.')
    return redirect('mfa_verify')


def _store_mfa_session_metadata(request, method: str):
    session_key = request.session.session_key
    if not session_key:
        return
    try:
        user_session = UserSession.objects.get(session_key=session_key)
        if user_session.metadata is None:
            user_session.metadata = {}
        user_session.metadata['mfa_method_used'] = method
        user_session.metadata['mfa_verified_at'] = timezone.now().isoformat()
        user_session.save(update_fields=['metadata'])
    except UserSession.DoesNotExist:
        pass