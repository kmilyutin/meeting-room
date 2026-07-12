from django.contrib import admin
from .models import Room, Equipment, Booking

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'status')
    list_filter = ('status', 'capacity') # фильтрация по вместимости
    search_fields = ('name',)
    filter_horizontal = ('equipment',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('name', 'room', 'organizer', 'start_time', 'end_time')
    list_filter = ('room', 'start_time')
    search_fields = ('name', 'organizer__username', 'room__name') # Поиск по имени брони, юзеру и комнате
    raw_id_fields = ('organizer', 'room')
