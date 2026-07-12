from django import forms
from django.utils import timezone

from rooms.models import Booking


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['name', 'description', 'start_time', 'end_time', 'participants']
        labels = {
            'name': 'Название встречи',
            'description': 'Описание',
            'start_time': 'Начало',
            'end_time': 'Окончание',
            'participants': 'Количество участников',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, room=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room or getattr(self.instance, 'room', None)
        self.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S']
        self.fields['end_time'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S']

    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']
        if start_time < timezone.now():
            raise forms.ValidationError('Нельзя бронировать на прошедшее время.')
        return start_time

    def clean_participants(self):
        participants = self.cleaned_data['participants']
        if participants < 1:
            raise forms.ValidationError('Укажите хотя бы одного участника.')
        if self.room and participants > self.room.capacity:
            raise forms.ValidationError(
                f'Комната вмещает не более {self.room.capacity} участников.'
            )
        return participants

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', 'Время окончания должно быть позже времени начала.')
            return cleaned_data

        if self.room and self.room.status != 'available':
            raise forms.ValidationError('Эта комната недоступна для бронирования.')

        if self.room and start_time and end_time:
            conflicts = Booking.objects.filter(
                room=self.room,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            if conflicts.exists():
                raise forms.ValidationError('Комната уже забронирована на выбранное время.')

        return cleaned_data

    def save(self, commit=True):
        booking = super().save(commit=False)
        if self.room:
            booking.room = self.room
        if commit:
            booking.save()
        return booking
