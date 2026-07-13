from django.urls import path

from rooms import views

app_name = 'rooms'

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.index, name='search'),
    path('rooms/', views.RoomListView.as_view(), name='list'),
    path('rooms/<int:pk>/', views.RoomDetailView.as_view(), name='detail'),
    path('rooms/<int:pk>/book/', views.book_room, name='book_room'),
    path('bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:pk>/edit/', views.edit_booking, name='edit_booking'),
    path('bookings/<int:pk>/delete/', views.delete_booking, name='delete_booking'),
    path('bookings/<int:pk>/extend/', views.extend_booking, name='extend_booking'),
]
