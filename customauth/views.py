from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response


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