from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django import forms

from accounts.models import User

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(label="Имя пользователя", widget=forms.TextInput(attrs={
        'class': "form-control",
        'placeholder': "Введите имя пользователя",
    }))
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput(attrs={
        'class': "form-control",
        'placeholder': "Введите пароль",
    }))

    class Meta:
        model = User,
        fields = ('username', 'password')

class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(label="Имя пользователя", widget=forms.TextInput(attrs={
        'class': "form-control",
        'placeholder': "Введите имя пользователя",
    }))
    email = forms.CharField(label="Email", widget=forms.EmailInput(attrs={
        'class': "form-control",
        'placeholder': "name@example.com",
    }))
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput(attrs={
        'class': "form-control",
        'placeholder': "Придумайте пароль",
    }))
    password2 = forms.CharField(label="Подтверждение пароля", widget=forms.PasswordInput(attrs={
        'class': "form-control",
        'placeholder': "Повторите пароль",
    }))
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
