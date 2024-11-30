from django.urls import path
from .views import custom_logout_view, is_authenticated, signup, CustomLoginView


urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('signup/', signup, name='signup'),
    path('is-authenticated/', is_authenticated, name='is_authenticated')
]