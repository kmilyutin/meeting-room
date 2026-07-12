from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse

from accounts.models import User


class Equipment(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Room(models.Model):
    ROOM_STATUS_CHOICES = [
        ('available', 'Свободно'),
        ('busy', 'Занято'),
        ('unavailable', 'Недоступно'),
    ]

    name = models.CharField(max_length=128, unique=True)
    capacity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    description = models.TextField(default="Нет описания")
    image = models.ImageField(upload_to="rooms_images")
    equipment = models.ManyToManyField(to=Equipment, blank=True)
    status = models.CharField(max_length=32, choices=ROOM_STATUS_CHOICES, default='available')

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name='room_capacity_positive'),
        ]

    def __str__(self):
        return f'Комната {self.name}'

    def get_absolute_url(self):
        return reverse('rooms:detail', kwargs={'pk': self.pk})


class Booking(models.Model):
    name = models.CharField(max_length=128)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    participants = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    description = models.TextField(null=True, blank=True)
    organizer = models.ForeignKey(to=User, on_delete=models.CASCADE)
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=F('start_time')), name='booking_end_after_start'),
        ]

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError('Время окончания должно быть позже времени начала.')

    def __str__(self):
        return self.name
