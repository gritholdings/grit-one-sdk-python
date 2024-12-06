from django.urls import path
from .views import custom_logout_view, is_authenticated, signup, CustomLoginView, CustomPasswordChangeView
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('signup/', signup, name='signup'),
    path('is-authenticated/', is_authenticated, name='is_authenticated'),
    path('password/reset/', 
         PasswordResetView.as_view(template_name='customauth/password_reset_form.html'),
         name='password_reset'),
    path('password/reset/done/', 
         PasswordResetDoneView.as_view(template_name='customauth/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(template_name='customauth/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         PasswordResetCompleteView.as_view(template_name='customauth/password_reset_complete.html'),
         name='password_reset_complete'),
]
