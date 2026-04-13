from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from .settings import auth_settings
ACTIVITY_THROTTLE = timedelta(minutes=15)
MFA_EXEMPT_PATHS = ['/auth/mfa/', '/auth/login/', '/auth/logout/', '/auth/signup/']


class SessionActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        session_key = request.session.session_key
        if not session_key:
            return response
        last_update = request.session.get('_session_activity_updated')
        now = timezone.now()
        if last_update:
            from django.utils.dateparse import parse_datetime
            last_update_dt = parse_datetime(last_update)
            if last_update_dt and (now - last_update_dt) < ACTIVITY_THROTTLE:
                return response
        from .models import UserSession
        UserSession.objects.filter(
            session_key=session_key,
            status=UserSession.Status.ACTIVE,
        ).update(last_active_at=now)
        request.session['_session_activity_updated'] = now.isoformat()
        return response


class MFAEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        path = request.path
        if any(path.startswith(p) for p in MFA_EXEMPT_PATHS):
            return self.get_response(request)
        if request.session.get('_mfa_user_id') and not request.user.is_authenticated:
            return redirect('mfa_verify')
        if (request.user.is_authenticated
                and auth_settings.MFA_ENFORCEMENT == 'mandatory'
                and not request.user.mfa_devices.filter(is_active=True).exists()):
            return redirect('mfa_setup')
        return self.get_response(request)
