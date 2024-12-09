import os
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.conf import settings
from customauth.models import CustomUser

def _get_platform_url(request):
    django_env = os.getenv('DJANGO_ENV', 'DEV')
    # Make sure user has completed onboarding before redirecting to platform
    if hasattr(request.user, 'metadata') and request.user.metadata.get('has_completed_onboarding', False) is False:
        return reverse('onboarding', kwargs={'step': 1})
    platform_url = f'https://platform.{settings.DOMAIN_NAME}/' if django_env == 'PROD' else 'http://127.0.0.1:3000'
    return platform_url

def index(request):
    platform_url = _get_platform_url(request)
    context = {
        'platform_url': platform_url
    }
    return render(request, "home/index.html", context)

def pricing(request):
    platform_url = _get_platform_url(request)
    context = {
        'platform_url': platform_url 
    }
    return render(request, "home/pricing.html", context)

TOTAL_STEPS = 3

def update_user_metadata(user, form_data):
    """
    Helper function to update user metadata based on form fields
    Preserves existing metadata and updates with new form data
    Supports both flat and categorized structures dynamically
    """
    if user.metadata is None:
        user.metadata = {}

    # Get all checkbox fields from the form (by looking at fields with value 'true')
    checkbox_fields = {field for field, value in form_data.items() if value == 'true'}

    # Update all form fields except checkboxes
    for field, value in form_data.items():
        if field not in checkbox_fields:
            user.metadata[field] = value

    # Handle all checkbox fields
    for field in checkbox_fields:
        user.metadata[field] = form_data[field] == 'true'
        
    # Set any missing checkbox fields to False
    # This handles unchecked boxes which won't appear in form_data
        seen_checkboxes = {field for field in user.metadata if isinstance(user.metadata[field], bool)}
        for checkbox in seen_checkboxes:
            if checkbox not in form_data:
                user.metadata[checkbox] = False

@login_required
def onboarding(request, step):
    try:
        step = int(step)
    except (TypeError, ValueError):
        return redirect('onboarding', step=1)

    platform_url = _get_platform_url(request)

    if step < 1 or step > TOTAL_STEPS:
        return redirect('onboarding', step=1)

    if request.method == 'POST':
        # Convert QueryDict to regular dict and remove CSRF token
        form_data = request.POST.dict()
        form_data.pop('csrfmiddlewaretoken', None)

        # Remove navigation buttons from form data
        for btn in ['next', 'previous', 'save']:
            form_data.pop(btn, None)

        try:
            # Update user metadata
            update_user_metadata(request.user, form_data)
            request.user.save()
        except ValidationError as e:
            context = {
                'step': step,
                'total_steps': TOTAL_STEPS,
                'saved_data': form_data,
                'show_previous': step > 1,
                'is_last_step': step == TOTAL_STEPS,
                'platform_url': platform_url,
                'error': str(e)
            }
            return render(request, "home/onboarding.html", context)

        # Handle navigation
        if 'next' in request.POST and step < TOTAL_STEPS:
            return redirect('onboarding', step=step + 1)
        elif 'previous' in request.POST and step > 1:
            return redirect('onboarding', step=step - 1)
        elif ('next' in request.POST and step == TOTAL_STEPS) or 'save' in request.POST:
            return redirect('index')

    # Get previously saved data for this step
    saved_data = CustomUser.objects.get(id=request.user.id).metadata

    industry_options = [
        ('tech', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('retail', 'Retail'),
        ('other', 'Other')
    ]

    team_size_options = [
        ('1-10', '1-10'),
        ('11-50', '11-50'),
        ('51-100', '51-100'),
        ('101-500', '101-500'),
        ('501-1000', '501-1000'),
        ('1001+', '1001+')
    ]

    context = {
        'step': step,
        'total_steps': TOTAL_STEPS,
        'saved_data': saved_data,
        'show_previous': step > 1,
        'is_last_step': step == TOTAL_STEPS,
        'platform_url': platform_url,
        'industry_options': industry_options,
        'team_size_options': team_size_options
    }
    return render(request, "home/onboarding.html", context)

@login_required
def save_onboarding_progress(request):
    if request.method == 'POST':
        try:
            current_step = int(request.POST.get('step', 1))
        except ValueError:
            current_step = 1

        # if last step, change value to True
        if int(request.POST.get('step', 1)) == TOTAL_STEPS:
            update_user_metadata(request.user, {'has_completed_onboarding': True})

        # Convert QueryDict to regular dict and remove CSRF token
        form_data = request.POST.dict()
        form_data.pop('csrfmiddlewaretoken', None)
        form_data.pop('step', None)

        # Remove navigation buttons from form data
        for btn in ['next', 'previous', 'save']:
            form_data.pop(btn, None)

        try:
            # Update user metadata
            update_user_metadata(request.user, form_data)
            request.user.save()
        except ValidationError as e:
            return redirect('onboarding', step=current_step)

        if 'save' in request.POST:
            return redirect('index')
        elif 'next' in request.POST and current_step < TOTAL_STEPS:
            return redirect('onboarding', step=current_step + 1)
        elif 'previous' in request.POST and current_step > 1:
            return redirect('onboarding', step=current_step - 1)

    return redirect('index')

def about_us(request):
    platform_url = _get_platform_url(request)
    context = {
        'platform_url': platform_url 
    }
    return render(request, "home/about-us.html", context)

def terms_and_conditions(request):
    platform_url = _get_platform_url(request)
    context = {
        'platform_url': platform_url 
    }
    return render(request, "home/terms-and-conditions.html", context)

def profile(request):
    platform_url = _get_platform_url(request)
    context = {
        'platform_url': platform_url 
    }
    return render(request, "home/profile.html", context)