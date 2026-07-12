from django.shortcuts import render, HttpResponseRedirect
from django.contrib import auth, messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse

from accounts.forms import ProfileForm, UserLoginForm, UserRegistrationForm


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = UserLoginForm
    extra_context = {
        'title': 'Вход - Booked!',
    }

    def form_valid(self, form):
        messages.success(self.request, 'Поздравляем! Вы успешно вошли в аккаунт!')
        return super().form_valid(form)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Вы успешно зарегистрировались! Теперь войдите в аккаунт')
            return HttpResponseRedirect(reverse('accounts:login'))
    else:
        form = UserRegistrationForm()
    
    context = {
        'title': 'Регистрация - Booked!',
        'form': form
    }
    return render(request, 'accounts/register.html', context)

def logout(request):
    auth.logout(request)

    context = {
        'title': 'Выход - Booked!',
    }
    return render(request, 'accounts/logged-out.html', context)


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Профиль обновлен.')
            return HttpResponseRedirect(reverse('accounts:profile'))
    else:
        form = ProfileForm(instance=request.user)

    context = {
        'title': 'Мой профиль - Booked!',
        'form': form,
    }
    return render(request, 'accounts/profile.html', context)
