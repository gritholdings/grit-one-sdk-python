from django.urls import path
from home import views as home_views
from django.views.generic import TemplateView


urlpatterns = [
    path('contact-us/', home_views.contact_us, name='contact_us'),
    path('contact-us/complete/', TemplateView.as_view(template_name="home/contact-us-complete.html"), name='contact_us_complete'),
    path('about-us/', TemplateView.as_view(template_name="home/about-us.html"), name='about_us'),
    path('pricing/', TemplateView.as_view(template_name="home/pricing.html"), name='pricing'),
    path('terms-and-conditions/', TemplateView.as_view(template_name="home/terms-and-conditions.html"), name='terms-and-conditions'),
    path('', TemplateView.as_view(template_name="home/index.html"), name='index'),
]