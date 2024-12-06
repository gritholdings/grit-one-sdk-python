from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

from django.contrib.auth.forms import PasswordChangeForm

class SignUpForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove colons from labels
        self.label_suffix = ''
        # Add label class to all fields
        for field in self.fields.values():
            field.label_attrs = {'class': 'block text-sm font-medium text-gray-700 mb-1'}

    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control w-full mt-1 px-3 py-2 border rounded-lg'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control w-full mt-1 px-3 py-2 border rounded-lg'}),
        label="Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control w-full mt-1 px-3 py-2 border rounded-lg'}),
        label="Confirm Password"
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'password1', 'password2')

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users."""
    class Meta:
        model = CustomUser
        fields = ('email',)

class CustomUserChangeForm(UserChangeForm):
    """Form for updating users."""
    class Meta:
        model = CustomUser
        fields = ('email',)

class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Password', strip=False, widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        super(EmailAuthenticationForm, self).__init__(*args, **kwargs)
        self.request = request
        self.user_cache = None

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Invalid email or password.")
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError("This account is inactive.")

    def get_user(self):
        return self.user_cache

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current Password'}),
        label='Current Password'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        label='New Password'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
        label='Confirm New Password'
    )