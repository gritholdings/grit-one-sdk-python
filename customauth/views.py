from django.contrib.auth import logout, login, authenticate
from django.contrib import messages
from django.shortcuts import render, redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.contrib.auth import login
from .forms import SignUpForm


def custom_logout_view(request):
    logout(request)
    return redirect('index')

@api_view(['GET'])
def is_authenticated(request):
    # check if user is authenticated
    if request.user.is_authenticated:
        return Response({'is_authenticated': True, 'email': request.user.email})
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