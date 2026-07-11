from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy

from .forms import RegisterForm, LoginForm

def register_form(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})    

def login_view(request):
    pass

class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        self.object = form.save()
        group, created = Group.objects.get_or_create(name='registered_users')
        self.object.groups.add(group)
        login(self.request, self.object)
        return redirect(self.get_success_url())
