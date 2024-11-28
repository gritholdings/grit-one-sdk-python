import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

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

def update_user_metadata(user, form_data):
    """
    Helper function to update user metadata based on form fields
    """
    print("Form data received in update_user_metadata:", form_data)
    
    if user.metadata is None:
        user.metadata = {}

    # Update mappings to match your form fields
    metadata_mappings = {
        'company_name': {
            'category': 'company',
            'field': 'name'
        },
        'business_description': {
            'category': 'company',
            'field': 'description'
        },
        'industry': {
            'category': 'company',
            'field': 'industry'
        },
        'newsletter': {
            'category': 'preferences',
            'field': 'newsletter'
        },
        'goals': {
            'category': 'company',
            'field': 'goals'
        },
        'team_size': {
            'category': 'company',
            'field': 'team_size'
        }
    }

    # Process each form field
    for field, value in form_data.items():
        print(f"Processing field: {field} with value: {value}")
        if field in metadata_mappings:
            mapping = metadata_mappings[field]
            category = mapping['category']
            field_name = mapping['field']

            # Initialize category if it doesn't exist
            if category not in user.metadata:
                user.metadata[category] = {}
            
            # Handle checkbox value for newsletter
            if field == 'newsletter':
                value = bool(value == '1')
            
            # Update the field value
            user.metadata[category][field_name] = value.lower() if isinstance(value, str) else value
            print(f"Updated metadata: {user.metadata}")

@login_required
def onboarding(request, step):
    try:
        step = int(step)
    except (TypeError, ValueError):
        return redirect('onboarding', step=1)

    django_env = os.getenv('DJANGO_ENV', 'DEV')
    platform_url = 'https://platform.meetgrit.com/' if django_env == 'PROD' else 'http://127.0.0.1:3000'

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
        try:
            current_step = int(request.POST.get('step', 1))
        except ValueError:
            current_step = 1
        
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