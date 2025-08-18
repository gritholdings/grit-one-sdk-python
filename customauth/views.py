from django.contrib.auth import logout, login, authenticate, views as auth_views
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.utils.env_config import get_base_url
from .forms import (
    SignUpForm, EmailAuthenticationForm, CustomPasswordChangeForm, CustomPasswordResetForm,
    CustomSetPasswordForm
)


def custom_logout_view(request):
    logout(request)
    return redirect('index')

@api_view(['POST'])
def is_authenticated(request):
    # check if user is authenticated
    user = request.user
    if user.is_authenticated:
        return Response({'is_authenticated': True, 'user_id': user.id, 'email': user.email})
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
            messages.success(request, 'Account created successfully!')
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