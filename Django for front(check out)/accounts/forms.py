from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


def _append_css_class(widget, class_name):
    classes = widget.attrs.get('class', '').split()
    if class_name not in classes:
        classes.append(class_name)
    widget.attrs['class'] = ' '.join(classes)


def _mark_invalid_fields(form, extra_fields=()):
    if not form.is_bound:
        return

    invalid_fields = set(form.errors)
    invalid_fields.update(extra_fields)
    for name in invalid_fields:
        field = form.fields.get(name)
        if field:
            _append_css_class(field.widget, 'is-invalid')
            field.widget.attrs['aria-invalid'] = 'true'


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)
        labels = {
            'username': 'Имя пользователя',
            'email': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Введите имя пользователя',
            'email': 'name@example.com',
            'password1': 'Придумайте пароль',
            'password2': 'Повторите пароль',
        }
        labels = {
            'password1': 'Пароль',
            'password2': 'Подтверждение пароля',
        }

        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': placeholders.get(name, ''),
            })
            if name in labels:
                field.label = labels[name]
        _mark_invalid_fields(self)

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя пользователя',
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        label='Пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль',
            'autocomplete': 'current-password',
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        extra_fields = ('username', 'password') if self.is_bound and self.non_field_errors() else ()
        _mark_invalid_fields(self, extra_fields)
