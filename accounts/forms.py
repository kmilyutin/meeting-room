from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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

class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(label="Имя пользователя", widget=forms.TextInput(attrs={
        'class': "form-control",
        'placeholder': "Введите имя пользователя",
    }))
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
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


class ProfileForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Новый пароль',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Оставьте пустым, если не меняете',
        }),
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите новый пароль',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        labels = {
            'username': 'Логин',
            'email': 'Email',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1:
            if password1 != password2:
                self.add_error('password2', 'Пароли не совпадают.')
            try:
                validate_password(password1)
            except ValidationError as e:
                self.add_error('password1', e.messages)
                
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
