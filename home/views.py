import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def index(request):
    django_env = os.getenv('DJANGO_ENV', 'DEV')
    platform_url = 'https://platform.meetgrit.com/' if django_env == 'PROD' else 'http://127.0.0.1:3000'
    context = {
        'platform_url': platform_url
    }
    return render(request, "home/index.html", context)

def pricing(request):
    django_env = os.getenv('DJANGO_ENV', 'DEV')
    platform_url = 'https://platform.meetgrit.com/' if django_env == 'PROD' else 'http://127.0.0.1:3000'
    context = {
        'platform_url': platform_url
    }
    return render(request, "home/pricing.html", context)

TOTAL_STEPS = 3

@login_required
def onboarding(request, step):
    django_env = os.getenv('DJANGO_ENV', 'DEV')
    platform_url = 'https://platform.meetgrit.com/' if django_env == 'PROD' else 'http://127.0.0.1:3000'

    if step < 1 or step > TOTAL_STEPS:
        return redirect('onboarding', step=1)
    
    if request.method == 'POST':
        form_data = request.POST
        request.session[f'onboarding_step_{step}'] = form_data.dict()
        
        if 'next' in request.POST:
            if step < TOTAL_STEPS:
                return redirect('onboarding', step=step + 1)
            else:
                return redirect('index')
        elif 'previous' in request.POST:
            return redirect('onboarding', step=step - 1)
    
    saved_data = request.session.get(f'onboarding_step_{step}', {})
    
    context = {
        'step': step,
        'total_steps': TOTAL_STEPS,
        'saved_data': saved_data,
        'show_previous': step > 1,
        'is_last_step': step == TOTAL_STEPS,
        'platform_url': platform_url
    }
    return render(request, "home/onboarding.html", context)

@login_required
def save_onboarding_progress(request):
    if request.method == 'POST':
        current_step = int(request.POST.get('step', 1))
        request.session[f'onboarding_step_{current_step}'] = request.POST.dict()
        if 'save' in request.POST:
            return redirect('index')
        elif 'next' in request.POST:
            if current_step < TOTAL_STEPS:
                return redirect('onboarding', step=current_step + 1)
            else:
                return redirect('index')
        elif 'previous' in request.POST:
            return redirect('onboarding', step=current_step - 1)
    return redirect('index')