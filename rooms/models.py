from django.db import models

from accounts.models import User

class Equipment(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Room(models.Model):
    ROOM_STATUS_CHOICES = [
        ('available', 'Свободна'),
        ('busy', 'Занята'),
        ('maintenance', 'На ремонте'),
        ('closed', 'Закрыта'),
    ]
    
    name = models.CharField(max_length=128, unique=True)
    capacity = models.PositiveIntegerField(default=0)
    description = models.TextField(default="Нет описания")
    image = models.ImageField(upload_to="rooms_images")
    equipment = models.ManyToManyField(to=Equipment, blank=True)
    status = models.CharField(max_length=32, choices=ROOM_STATUS_CHOICES, default='avaliable')

    def __str__(self):
        return f'Комната {self.name}'

class Booking(models.Model):
    name = models.CharField(max_length=128, unique=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField(null=True, blank=True)
    # status
    organizer = models.ForeignKey(to=User, on_delete=models.CASCADE)
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE)
