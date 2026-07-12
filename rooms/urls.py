from django.urls import path

from rooms.views import index

app_name = 'rooms'

urlpatterns = [
    path('', index, name='index'),
    path('search', index, name='search'),
]
