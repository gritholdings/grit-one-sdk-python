from django.contrib.auth.signals import user_logged_in
from django.utils import timezone


def create_user_session(sender, request, user, **kwargs):
    from .models import UserSession
    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key
    UserSession.objects.update_or_create(
        session_key=session_key,
        defaults={
            'user': user,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:512],
            'ip': request.META.get('REMOTE_ADDR'),
            'status': UserSession.Status.ACTIVE,
            'last_active_at': timezone.now(),
            'signed_out_at': None,
        },
    )
user_logged_in.connect(create_user_session)
