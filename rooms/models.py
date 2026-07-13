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
        errors = {}
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            errors['end_time'] = 'Время окончания должно быть позже времени начала.'

        if self.room_id:
            if self.room.status != 'available':
                errors['room'] = 'Эта комната недоступна для бронирования.'
            if self.participants and self.participants > self.room.capacity:
                errors['participants'] = (
                    f'Комната вмещает не более {self.room.capacity} участников.'
                )
            if self.start_time and self.end_time and self.end_time > self.start_time:
                conflicts = Booking.objects.filter(
                    room_id=self.room_id,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time,
                )
                if self.pk:
                    conflicts = conflicts.exclude(pk=self.pk)
                if conflicts.exists():
                    errors['__all__'] = 'Комната уже забронирована на выбранное время.'

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name
