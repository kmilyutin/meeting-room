from django.urls import path

from rooms import views

app_name = 'rooms'

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.index, name='search'),
    path('rooms/', views.room_list, name='list'),
    path('rooms/<int:pk>/', views.room_detail, name='detail'),
    path('bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:pk>/extend/', views.extend_booking, name='extend_booking'),
]
