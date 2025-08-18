from django.urls import path
from django.contrib.auth.views import (
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.utils.module_loading import import_string
from .views import (
     custom_logout_view, is_authenticated, signup,
     CustomPasswordResetView, CustomPasswordResetConfirmView
)
from .settings import auth_settings


urlpatterns = [
    path('login/', import_string(auth_settings.LOGIN_VIEW), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('signup/', signup, name='signup'),
    path('is-authenticated/', is_authenticated, name='is_authenticated'),
    path('password-reset/',
         CustomPasswordResetView.as_view(),
         name='password_reset'),
    path('password-reset-done/',
         PasswordResetDoneView.as_view(template_name='customauth/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         PasswordResetCompleteView.as_view(template_name='customauth/password_reset_complete.html'),
         name='password_reset_complete'),
]
