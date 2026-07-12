from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from rooms.forms import BookingForm
from rooms.models import Booking, Equipment, Room


def parse_date(value):
    if not value:
        return timezone.localdate() + timedelta(days=1)
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return timezone.localdate() + timedelta(days=1)


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%H:%M').time()
    except ValueError:
        return None


def make_dt(day, value):
    parsed = parse_time(value)
    if not parsed:
        return None
    return timezone.make_aware(datetime.combine(day, parsed), timezone.get_current_timezone())


def room_has_conflict(room, start_at, end_at, exclude_booking=None):
    if not start_at or not end_at or end_at <= start_at:
        return False
    conflicts = Booking.objects.filter(
        room=room,
        start_time__lt=end_at,
        end_time__gt=start_at,
    )
    if exclude_booking is not None:
        conflicts = conflicts.exclude(pk=exclude_booking.pk)
    return conflicts.exists()


def decorate_room(room, start_at=None, end_at=None):
    if room.status == 'unavailable':
        room.display_status = 'unavailable'
        room.display_status_label = 'Недоступно'
        room.can_book = False
    elif room_has_conflict(room, start_at, end_at) or room.status == 'busy':
        room.display_status = 'busy'
        room.display_status_label = 'Занято'
        room.can_book = False
    else:
        room.display_status = 'available'
        room.display_status_label = 'Свободно'
        room.can_book = True
    return room


def get_equipment_choices():
    return Equipment.objects.exclude(name__iexact='Видеосвязь').order_by('name')


def get_timeline(day):
    start_at = timezone.make_aware(datetime.combine(day, time.min), timezone.get_current_timezone())
    end_at = start_at + timedelta(days=1)
    bookings = Booking.objects.select_related('room', 'organizer').filter(
        start_time__gte=start_at,
        start_time__lt=end_at,
    ).order_by('start_time')
    rows = []
    for booking in bookings:
        rows.append({
            'time': timezone.localtime(booking.start_time).strftime('%H:%M'),
            'title': booking.name,
            'room': booking.room.name,
            'range': f'{timezone.localtime(booking.start_time).strftime("%H:%M")}-{timezone.localtime(booking.end_time).strftime("%H:%M")}',
            'status': 'busy',
            'status_label': 'Занято',
        })
    if not rows:
        rows.append({
            'time': '09:00',
            'title': 'Свободный день',
            'room': 'Все доступные переговорные',
            'range': '09:00-18:00',
            'status': 'available',
            'status_label': 'Свободно',
        })
    rows.append({
        'time': '16:00',
        'title': 'Техобслуживание',
        'room': 'Север',
        'range': 'до конца дня',
        'status': 'unavailable',
        'status_label': 'Недоступно',
    })
    return rows


def index(request):
    selected_date = parse_date(request.GET.get('date'))
    start_at = make_dt(selected_date, request.GET.get('start_time'))
    end_at = make_dt(selected_date, request.GET.get('end_time'))
    selected_equipment = request.GET.getlist('equipment')
    custom_equipment = request.GET.get('equipment_other', '').strip()
    participants = request.GET.get('participants')

    rooms = Room.objects.prefetch_related('equipment').all().order_by('name')
    if participants:
        try:
            rooms = rooms.filter(capacity__gte=int(participants))
        except ValueError:
            pass
    if selected_equipment:
        for item_name in selected_equipment:
            rooms = rooms.filter(equipment__name__iexact=item_name)
    if custom_equipment:
        rooms = rooms.filter(equipment__name__icontains=custom_equipment)

    rooms = list(rooms.distinct())
    decorated_rooms = [decorate_room(room, start_at, end_at) for room in rooms]

    context = {
        'title': 'Поиск переговорной - Booked!',
        'rooms': decorated_rooms,
        'equipment_choices': get_equipment_choices(),
        'selected_equipment': selected_equipment,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'timeline_day': selected_date,
        'timeline_rows': get_timeline(selected_date),
    }
    return render(request, 'rooms/index.html', context)


def room_list(request):
    rooms = Room.objects.prefetch_related('equipment').all().order_by('name')
    query = request.GET.get('q', '').strip()
    capacity = request.GET.get('capacity', '').strip()
    status = request.GET.get('status', '').strip()

    if query:
        rooms = rooms.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(equipment__name__icontains=query))
    if capacity:
        try:
            rooms = rooms.filter(capacity__gte=int(capacity))
        except ValueError:
            pass
    if status:
        rooms = rooms.filter(status=status)

    paginator = Paginator(rooms.distinct(), 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    for room in page_obj:
        decorate_room(room)

    context = {
        'title': 'Переговорные - Booked!',
        'page_obj': page_obj,
        'rooms': page_obj.object_list,
        'status_choices': Room.ROOM_STATUS_CHOICES,
    }
    return render(request, 'rooms/list.html', context)


def room_detail(request, pk):
    room = decorate_room(get_object_or_404(Room.objects.prefetch_related('equipment'), pk=pk))
    day = parse_date(request.GET.get('date'))
    start_at = timezone.make_aware(datetime.combine(day, time.min), timezone.get_current_timezone())
    end_at = start_at + timedelta(days=1)
    bookings = Booking.objects.filter(room=room, start_time__gte=start_at, start_time__lt=end_at)

    context = {
        'title': f'{room.name} - Booked!',
        'room': room,
        'bookings': bookings,
        'timeline_day': day,
    }
    return render(request, 'rooms/detail.html', context)


def build_booking_initial(request):
    initial = {}
    day = parse_date(request.GET.get('date'))
    start_at = make_dt(day, request.GET.get('start_time'))
    end_at = make_dt(day, request.GET.get('end_time'))
    if start_at:
        initial['start_time'] = timezone.localtime(start_at).strftime('%Y-%m-%dT%H:%M')
    if end_at:
        initial['end_time'] = timezone.localtime(end_at).strftime('%Y-%m-%dT%H:%M')
    participants = request.GET.get('participants', '')
    if participants.isdigit() and int(participants) > 0:
        initial['participants'] = int(participants)
    return initial


@login_required
def book_room(request, pk):
    room = get_object_or_404(Room, pk=pk)

    if request.method == 'POST':
        form = BookingForm(request.POST, room=room)
        if form.is_valid():
            with transaction.atomic():
                Room.objects.select_for_update().get(pk=room.pk)
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']
                if room_has_conflict(room, start_time, end_time):
                    form.add_error(None, 'Комната уже забронирована на выбранное время.')
                else:
                    booking = form.save(commit=False)
                    booking.organizer = request.user
                    booking.save()
                    messages.success(request, f'Переговорная {room.name} забронирована.')
                    return redirect('rooms:my_bookings')
    else:
        form = BookingForm(room=room, initial=build_booking_initial(request))

    context = {
        'title': f'Бронирование {room.name} - Booked!',
        'room': room,
        'form': form,
        'heading': f'Бронирование переговорной {room.name}',
        'submit_label': 'Забронировать',
    }
    return render(request, 'rooms/booking_form.html', context)


@login_required
def edit_booking(request, pk):
    booking = get_object_or_404(Booking.objects.select_related('room'), pk=pk, organizer=request.user)
    room = booking.room

    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking, room=room)
        if form.is_valid():
            with transaction.atomic():
                Room.objects.select_for_update().get(pk=room.pk)
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']
                if room_has_conflict(room, start_time, end_time, exclude_booking=booking):
                    form.add_error(None, 'Комната уже забронирована на выбранное время.')
                else:
                    form.save()
                    messages.success(request, 'Бронь обновлена.')
                    return redirect('rooms:my_bookings')
    else:
        form = BookingForm(instance=booking, room=room)

    context = {
        'title': 'Изменение брони - Booked!',
        'room': room,
        'form': form,
        'heading': f'Изменение брони «{booking.name}»',
        'submit_label': 'Сохранить изменения',
    }
    return render(request, 'rooms/booking_form.html', context)


@login_required
def delete_booking(request, pk):
    booking = get_object_or_404(Booking.objects.select_related('room'), pk=pk, organizer=request.user)

    if request.method == 'POST':
        booking.delete()
        messages.success(request, 'Бронь удалена.')
        return redirect('rooms:my_bookings')

    context = {
        'title': 'Удаление брони - Booked!',
        'booking': booking,
    }
    return render(request, 'rooms/booking_confirm_delete.html', context)


def can_extend(booking):
    next_booking = Booking.objects.filter(
        room=booking.room,
        start_time__gte=booking.end_time,
    ).exclude(pk=booking.pk).order_by('start_time').first()
    target_end = booking.end_time + timedelta(minutes=30)
    return next_booking is None or next_booking.start_time >= target_end


@login_required
def my_bookings(request):
    bookings = Booking.objects.select_related('room').filter(organizer=request.user).order_by('start_time')
    booking_rows = []
    for booking in bookings:
        next_booking = Booking.objects.filter(
            room=booking.room,
            start_time__gte=booking.end_time,
        ).exclude(pk=booking.pk).order_by('start_time').first()
        booking_rows.append({
            'booking': booking,
            'can_extend': can_extend(booking),
            'free_until': next_booking.start_time if next_booking else None,
        })
    context = {
        'title': 'Мои бронирования - Booked!',
        'booking_rows': booking_rows,
    }
    return render(request, 'rooms/my_bookings.html', context)


@require_POST
@login_required
def extend_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, organizer=request.user)
    if can_extend(booking):
        booking.end_time = booking.end_time + timedelta(minutes=30)
        booking.save(update_fields=['end_time'])
        messages.success(request, 'Бронь продлена на 30 минут.')
    else:
        messages.warning(request, 'После этой брони нет свободного окна для продления.')
    return redirect('rooms:my_bookings')
