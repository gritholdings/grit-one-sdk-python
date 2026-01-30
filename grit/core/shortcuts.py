from typing import Callable
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect


def auth_redirect(authenticated_view_name: str, unauthenticated_view_name: str) -> Callable[[HttpRequest], HttpResponseRedirect]:
    def view(request: HttpRequest) -> HttpResponseRedirect:
        if request.user.is_authenticated:
            return redirect(authenticated_view_name)
        return redirect(unauthenticated_view_name)
    return view