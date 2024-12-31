from django.shortcuts import redirect
from django.contrib.auth import logout


def custom_csrf_failure_view(request, reason=""):
    """
    Custom view for handling CSRF failures.
    Clears the session (or logs out the user) before redirecting
    to a safe page, like the login page or a 'csrf-error' page.
    """
    # Completely flush the session
    if request.session:
        request.session.flush()

    # Log out the user (if they are authenticated)
    logout(request)

    return redirect("login")