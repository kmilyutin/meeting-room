from django.shortcuts import render

def index(request):
    context = {
        'title': 'Поиск переговорной - Booked!',
    }
    return render(request, 'rooms/index.html', context)
