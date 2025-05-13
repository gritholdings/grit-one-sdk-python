from django import forms


class CustomContactForm(forms.Form):
    first_name = forms.CharField(
        label='First Name', max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'border py-2.5 sm:py-3 px-4 block w-full border-gray-200 rounded-lg sm:text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none',
        })
    )
    last_name = forms.CharField(
        label='Last Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'border py-2.5 sm:py-3 px-4 block w-full border-gray-200 rounded-lg sm:text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none',
        })
    )
    email = forms.EmailField(
        label='Business Email',
        widget=forms.EmailInput(attrs={
            'class': 'border py-2.5 sm:py-3 px-4 block w-full border-gray-200 rounded-lg sm:text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none'
        })
    )
    phone = forms.CharField(
        label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'border py-2.5 sm:py-3 px-4 block w-full border-gray-200 rounded-lg sm:text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none'
        }),
        required=False
    )
    company = forms.CharField(
        label='Company Name',
        widget=forms.TextInput(attrs={
            'class': 'border py-2.5 sm:py-3 px-4 block w-full border-gray-200 rounded-lg sm:text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none'
        })
    )
    message = forms.CharField(
        label='What would you like to discuss?',
        widget=forms.Textarea(attrs={
            'class': 'border py-2.5 sm:py-3 px-4 block w-full border-gray-200 rounded-lg sm:text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none'
        })
    )