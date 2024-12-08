"""
Components for rendering form fields in Django templates.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def input_field(name, label=None, value=None, required=False, input_type="text", **kwargs):
    """
    Renders a styled input field with label.
    Example usage:
    {% input_field name="company_name" required=True value=saved_data.company_name %}
    """
    label_text = label or name.replace('_', ' ').title()
    required_mark = ' *' if required else ''

    html = f"""
        <div>
            <label for="{name}" class="block text-sm font-medium text-gray-700 mb-1">
                {label_text}{required_mark}
            </label>
            <input type="{input_type}" 
                   id="{name}" 
                   name="{name}"
                   value="{value or ''}"
                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                   {"required" if required else ""}
                   {' '.join(f'{k}="{v}"' for k, v in kwargs.items())}
            >
        </div>
    """
    return mark_safe(html)

@register.simple_tag
def textarea_field(name, label=None, value=None, required=False, min_height="120px", **kwargs):
    """
    Renders a styled textarea field with label.
    
    Example usage:
    {% textarea_field name="business_description" label="Tell us about your business" value=saved_data.business_description %}
    """
    label_text = label or name.replace('_', ' ').title()
    required_mark = ' *' if required else ''

    # Handle optional indicator in label
    if not required and '(Optional)' not in label_text:
        label_text += ' (Optional)'

    html = f"""
        <div>
            <label for="{name}" class="block text-sm font-medium text-gray-700 mb-1">
                {label_text}{required_mark}
            </label>
            <textarea
                id="{name}"
                name="{name}"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                style="min-height: {min_height};"
                {"required" if required else ""}
                {' '.join(f'{k}="{v}"' for k, v in kwargs.items())}
            >{value or ''}</textarea>
        </div>
    """
    return mark_safe(html)

@register.simple_tag
def select_field(name, options, value=None, label=None, required=False, placeholder="Select an option...", **kwargs):
    """
    Renders a styled select field with label and options.
    
    Example usage:
    {% select_field 
        name="industry" 
        label="Select your industry"
        options=industry_options
        value=saved_data.industry 
        required=True 
    %}
    
    Where options is a list of tuples [(value, label)] or a dict {value: label}
    """
    label_text = label or name.replace('_', ' ').title()
    required_mark = ' *' if required else ''

    # Convert dict to list of tuples if necessary
    if isinstance(options, dict):
        options = options.items()

    # Build options HTML
    options_html = f'<option value="">{placeholder}</option>'
    for opt_value, opt_label in options:
        selected = 'selected' if str(value) == str(opt_value) else ''
        options_html += f'<option value="{opt_value}" {selected}>{opt_label}</option>'

    html = f"""
        <div>
            <label for="{name}" class="block text-sm font-medium text-gray-700 mb-1">
                {label_text}{required_mark}
            </label>
            <select
                id="{name}"
                name="{name}"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                {"required" if required else ""}
                {' '.join(f'{k}="{v}"' for k, v in kwargs.items())}
            >
                {options_html}
            </select>
        </div>
    """
    return mark_safe(html)

@register.simple_tag
def checkbox_field(name, label, value=None, **kwargs):
    """
    Renders a styled checkbox field with label.
    
    Example usage:
    {% checkbox_field 
        name="newsletter_subscription" 
        label="Keep me updated with new features and improvements"
        checked=saved_data.newsletter_subscription
    %}
    """
    # Convert Python boolean to string for HTML attribute
    is_checked = value in [True, 'true', 'True', '1', 'on']
    html = f"""
        <div class="inline-flex items-center">
            <input type="hidden" name="{name}" value="false">
            <input
                type="checkbox"
                name="{name}"
                value="true"
                class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                {' checked' if is_checked else ''}
                {' '.join(f'{k}="{v}"' for k, v in kwargs.items())}
            >
            <label for="{name}" class="ml-2 text-sm text-gray-700">
                {label}
            </label>
        </div>
    """
    return mark_safe(html)