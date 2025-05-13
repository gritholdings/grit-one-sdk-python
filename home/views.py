import os
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from customauth.models import CustomUser
from core.utils.env_config import get_platform_url
from core_payments.utils import get_credits_remaining
from core_sales.models import Lead

from .forms import CustomContactForm


def _get_platform_url(request):
    # Make sure user has completed onboarding before redirecting to platform
    if hasattr(request.user, 'metadata') and request.user.metadata.get('has_completed_onboarding', False) is False:
        return reverse('onboarding', kwargs={'step': 1})
    platform_url = get_platform_url()
    return platform_url

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

    agent_config_tag_options = [
        ('public', 'Public'),
        ('private', 'Private')
    ]

    industry_options = [
        ('tech', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('retail', 'Retail'),
        ('other', 'Other')
    ]
    # Add dependent field options
    tech_product_type_options = [
        ('software', 'Software'),
        ('hardware', 'Hardware')
    ]

    finance_service_options = [
        ('digital', 'Digital Banking'),
        ('physical', 'Physical Services')
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
        'agent_config_tag_options': agent_config_tag_options,
        'industry_options': industry_options,
        'team_size_options': team_size_options,
        'tech_product_type_options': tech_product_type_options,
        'finance_service_options': finance_service_options
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
        elif current_step == TOTAL_STEPS:
            platform_url = get_platform_url()
            return redirect(platform_url)

    return redirect('index')

def profile(request):
    user_id = request.user.id
    context = {}
    credits_remaining = get_credits_remaining(user_id)
    context['credits_remaining'] = credits_remaining

    return render(request, "home/profile.html", context)

def contact_us(request):
    context = {}
    if request.method == 'POST':
        filled_form = CustomContactForm(request.POST)
        if filled_form.is_valid():
            first_name = filled_form.cleaned_data['first_name']
            last_name = filled_form.cleaned_data['last_name']
            email = filled_form.cleaned_data['email']
            phone = filled_form.cleaned_data['phone'] # '' if not provided
            company = filled_form.cleaned_data['company']
            message = filled_form.cleaned_data['message']
            Lead.objects.create_with_metadata(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                company=company,
                message=message
            )
            # For example, you could redirect to a thank you page:
            return redirect('contact_us_complete')
    else:
        empty_form = CustomContactForm()
        context['form'] = empty_form
        return render(request, "home/contact-us.html", context)