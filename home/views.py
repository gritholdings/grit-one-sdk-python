import os
from django.shortcuts import render


def index(request):
    django_env = os.getenv('DJANGO_ENV', 'DEV')
    platform_url = 'https://main.d3biaxtqk028b8.amplifyapp.com/' if django_env == 'PROD' else 'http://127.0.0.1:3000'
    context = {
        'platform_url': platform_url
    }
    return render(request, "home/index.html", context)
