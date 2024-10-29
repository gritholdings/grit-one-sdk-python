from django.urls import path
from django.contrib.auth import views as auth_views
from .forms import EmailAuthenticationForm
from .views import custom_logout_view


urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='customauth/login.html',
        authentication_form=EmailAuthenticationForm
    ), name='login'),
    path('logout/', custom_logout_view, name='logout')
]