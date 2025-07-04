from typing import Callable
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect


def auth_redirect(authenticated_view_name: str, unauthenticated_view_name: str) -> Callable[[HttpRequest], HttpResponseRedirect]:
    """
    Higher-order function that returns a view function to redirect users 
    based on authentication status.
    
    Args:
        authenticated_view_name: View name to redirect authenticated users to
        unauthenticated_view_name: View name to redirect unauthenticated users to
    
    Returns:
        A view function that handles the redirect logic
    """
    def view(request: HttpRequest) -> HttpResponseRedirect:
        if request.user.is_authenticated:
            return redirect(authenticated_view_name)
        return redirect(unauthenticated_view_name)
    return view