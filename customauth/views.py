from django.contrib.auth import logout
from django.shortcuts import render, redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.contrib.auth import login
from .forms import CustomUserCreationForm


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
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  # Adjust this to your home page name
    else:
        form = CustomUserCreationForm()
    return render(request, 'customauth/signup.html', {'form': form})