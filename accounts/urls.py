from django.urls import path

from accounts.views import UserLoginView, logout, profile, register

app_name = 'accounts'

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/', register, name='register'),
    path('logout/', logout, name='logout'),
    path('profile/', profile, name='profile'),
]
