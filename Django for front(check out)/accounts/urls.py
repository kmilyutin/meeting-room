from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .forms import LoginForm
from .views import RegisterView

urlpatterns = [
    path('login/', LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=LoginForm,
    ), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(template_name='accounts/logged_out.html'), name='logout'),
]
