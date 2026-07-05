from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import RegisterView

urlpatterns = [
    path('login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
