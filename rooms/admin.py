from django.contrib import admin

from rooms.models import Room, Equipment, Booking

admin.site.register(Room)
admin.site.register(Equipment)
admin.site.register(Booking)
