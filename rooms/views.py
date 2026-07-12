from django.shortcuts import render

from rooms.models import Room

def index(request):
    context = {
        'title': 'Поиск переговорной - Booked!',
        'rooms': Room.objects.all(),
    }
    return render(request, 'rooms/index.html', context)

