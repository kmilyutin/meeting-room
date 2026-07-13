from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView
from django.views.decorators.http import require_POST

from rooms.forms import BookingForm
from rooms.models import Booking, Equipment, Room


WORKDAY_START = time(hour=9)
WORKDAY_END = time(hour=20)
MIN_FREE_SLOT = timedelta(minutes=30)


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
    elif room_has_conflict(room, start_at, end_at):
        room.display_status = 'busy'
        room.display_status_label = 'Занято'
        room.can_book = False
    else:
        room.display_status = 'available'
        room.display_status_label = 'Свободно'
        room.can_book = True
    return room


def get_equipment_choices():
    return Equipment.objects.order_by('name')


def day_bounds(day):
    start_at = timezone.make_aware(datetime.combine(day, time.min), timezone.get_current_timezone())
    return start_at, start_at + timedelta(days=1)


def workday_bounds(day):
    current_timezone = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(day, WORKDAY_START), current_timezone),
        timezone.make_aware(datetime.combine(day, WORKDAY_END), current_timezone),
    )


def get_room_schedule(room, day):
    workday_start, workday_end = workday_bounds(day)
    bookings = list(Booking.objects.filter(
        room=room,
        start_time__lt=workday_end,
        end_time__gt=workday_start,
    ).order_by('start_time'))
    rows = []
    cursor = workday_start

    for booking in bookings:
        busy_start = max(booking.start_time, workday_start)
        busy_end = min(booking.end_time, workday_end)
        if busy_start - cursor >= MIN_FREE_SLOT:
            rows.append({
                'start': cursor,
                'end': busy_start,
                'range': f'{timezone.localtime(cursor):%H:%M}–{timezone.localtime(busy_start):%H:%M}',
                'title': 'Свободно',
                'status': 'available',
                'status_label': 'Свободно',
            })
        rows.append({
            'start': busy_start,
            'end': busy_end,
            'range': f'{timezone.localtime(busy_start):%H:%M}–{timezone.localtime(busy_end):%H:%M}',
            'title': booking.name,
            'status': 'busy',
            'status_label': 'Занято',
            'booking': booking,
        })
        cursor = max(cursor, busy_end)

    if workday_end - cursor >= MIN_FREE_SLOT:
        rows.append({
            'start': cursor,
            'end': workday_end,
            'range': f'{timezone.localtime(cursor):%H:%M}–{timezone.localtime(workday_end):%H:%M}',
            'title': 'Свободно',
            'status': 'available',
            'status_label': 'Свободно',
        })
    return rows


def get_nearest_slots(rooms, day, requested_start, requested_end, limit=3):
    required_duration = requested_end - requested_start
    candidates = []
    for room in rooms:
        for row in get_room_schedule(room, day):
            if row['status'] != 'available':
                continue
            candidate_start = max(row['start'], requested_start)
            candidate_end = candidate_start + required_duration
            if candidate_end <= row['end']:
                candidates.append({
                    'room': room,
                    'start': candidate_start,
                    'end': candidate_end,
                    'range': (
                        f'{timezone.localtime(candidate_start):%H:%M}–'
                        f'{timezone.localtime(candidate_end):%H:%M}'
                    ),
                })
                break
    return sorted(candidates, key=lambda item: (item['start'], item['room'].name))[:limit]


def get_timeline(day):
    start_at, end_at = day_bounds(day)
    bookings = Booking.objects.select_related('room').filter(
        start_time__lt=end_at,
        end_time__gt=start_at,
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
            'time': '—',
            'title': 'Свободный день',
            'room': 'Все доступные переговорные',
            'range': 'весь день',
            'status': 'available',
            'status_label': 'Свободно',
        })
    return rows


def index(request):
    selected_date = parse_date(request.GET.get('date'))
    start_raw = request.GET.get('start_time', '').strip()
    end_raw = request.GET.get('end_time', '').strip()
    participants_raw = request.GET.get('participants', '').strip()
    selected_equipment = request.GET.getlist('equipment')
    custom_equipment = request.GET.get('equipment_other', '').strip()

    errors = []
    start_at = None
    end_at = None
    if start_raw or end_raw:
        if not (start_raw and end_raw):
            errors.append('Укажите и время начала, и время окончания.')
        else:
            start_at = make_dt(selected_date, start_raw)
            end_at = make_dt(selected_date, end_raw)
            if start_at is None or end_at is None:
                errors.append('Время указано в неверном формате.')
            elif end_at <= start_at:
                errors.append('Время окончания должно быть позже времени начала.')

    participants = None
    if participants_raw:
        if participants_raw.isdigit() and int(participants_raw) > 0:
            participants = int(participants_raw)
        else:
            errors.append('Количество участников должно быть положительным числом.')

    if errors:
        for error in errors:
            messages.error(request, error)
        decorated_rooms = []
        alternative_rooms = []
        nearest_slots = []
    else:
        rooms = Room.objects.prefetch_related('equipment').filter(status='available')
        if participants:
            rooms = rooms.filter(capacity__gte=participants)
        for item_name in selected_equipment:
            rooms = rooms.filter(equipment__name__iexact=item_name)
        if custom_equipment:
            rooms = rooms.filter(equipment__name__icontains=custom_equipment)

        rooms = rooms.distinct().order_by('capacity', 'name')
        decorated_rooms = [decorate_room(room, start_at, end_at) for room in rooms]
        if start_at and end_at:
            decorated_rooms = [room for room in decorated_rooms if room.can_book]

        alternative_rooms = []
        nearest_slots = []
        if start_at and end_at and not decorated_rooms:
            compatible_rooms = Room.objects.prefetch_related('equipment').filter(
                status='available'
            )
            if participants:
                compatible_rooms = compatible_rooms.filter(capacity__gte=participants)
            compatible_rooms = list(compatible_rooms.distinct())
            available_rooms = [
                decorate_room(room, start_at, end_at)
                for room in compatible_rooms
                if not room_has_conflict(room, start_at, end_at)
            ]
            requested_equipment = {name.casefold() for name in selected_equipment}
            if custom_equipment:
                requested_equipment.add(custom_equipment.casefold())
            for room in available_rooms:
                equipment_names = {item.name.casefold() for item in room.equipment.all()}
                room.matched_equipment = sum(
                    any(requested in name for name in equipment_names)
                    for requested in requested_equipment
                )
            alternative_rooms = sorted(
                available_rooms,
                key=lambda room: (-room.matched_equipment, room.capacity, room.name),
            )[:3]
            if not alternative_rooms:
                nearest_slots = get_nearest_slots(
                    compatible_rooms,
                    selected_date,
                    start_at,
                    end_at,
                )

    context = {
        'title': 'Поиск переговорной - Booked!',
        'rooms': decorated_rooms,
        'equipment_choices': get_equipment_choices(),
        'selected_equipment': selected_equipment,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'timeline_day': selected_date,
        'timeline_rows': get_timeline(selected_date),
        'alternative_rooms': alternative_rooms,
        'nearest_slots': nearest_slots,
    }
    return render(request, 'rooms/index.html', context)


class RoomListView(ListView):
    model = Room
    template_name = 'rooms/list.html'
    context_object_name = 'rooms'
    paginate_by = 6

    def get_queryset(self):
        rooms = Room.objects.prefetch_related('equipment').all().order_by('name')
        query = self.request.GET.get('q', '').strip()
        capacity = self.request.GET.get('capacity', '').strip()
        status = self.request.GET.get('status', '').strip()
        if query:
            rooms = rooms.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(equipment__name__icontains=query)
            )
        if capacity:
            try:
                rooms = rooms.filter(capacity__gte=int(capacity))
            except ValueError:
                pass
        if status:
            rooms = rooms.filter(status=status)
        return rooms.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for room in context['rooms']:
            decorate_room(room)
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context.update({
            'title': 'Переговорные - Booked!',
            'status_choices': Room.ROOM_STATUS_CHOICES,
            'pagination_query': query_params.urlencode(),
        })
        return context


class RoomDetailView(DetailView):
    model = Room
    template_name = 'rooms/detail.html'
    context_object_name = 'room'

    def get_queryset(self):
        return Room.objects.prefetch_related('equipment')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = decorate_room(context['room'])
        day = parse_date(self.request.GET.get('date'))
        start_at, end_at = day_bounds(day)
        bookings = Booking.objects.filter(
            room=room,
            start_time__lt=end_at,
            end_time__gt=start_at,
        ).order_by('start_time')
        context.update({
            'title': f'{room.name} - Booked!',
            'room': room,
            'bookings': bookings,
            'timeline_day': day,
            'selected_date': day.strftime('%Y-%m-%d'),
            'schedule_rows': get_room_schedule(room, day),
        })
        return context


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
                locked_room = Room.objects.select_for_update().get(pk=room.pk)
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']
                if locked_room.status != 'available':
                    form.add_error(None, 'Эта комната недоступна для бронирования.')
                elif form.cleaned_data['participants'] > locked_room.capacity:
                    form.add_error(
                        'participants',
                        f'Комната вмещает не более {locked_room.capacity} участников.',
                    )
                elif room_has_conflict(locked_room, start_time, end_time):
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
        form = BookingForm(
            request.POST,
            instance=booking,
            room=room,
            allow_room_change=True,
        )
        if form.is_valid():
            with transaction.atomic():
                selected_room = form.cleaned_data['room']
                room_ids = sorted({room.pk, selected_room.pk})
                locked_rooms = {
                    item.pk: item
                    for item in Room.objects.select_for_update().filter(
                        pk__in=room_ids
                    ).order_by('pk')
                }
                locked_room = locked_rooms[selected_room.pk]
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']
                if locked_room.status != 'available':
                    form.add_error(None, 'Эта комната недоступна для бронирования.')
                elif form.cleaned_data['participants'] > locked_room.capacity:
                    form.add_error(
                        'participants',
                        f'Комната вмещает не более {locked_room.capacity} участников.',
                    )
                elif room_has_conflict(
                    locked_room,
                    start_time,
                    end_time,
                    exclude_booking=booking,
                ):
                    form.add_error(None, 'Комната уже забронирована на выбранное время.')
                else:
                    form.save()
                    messages.success(request, 'Бронь обновлена.')
                    return redirect('rooms:my_bookings')
    else:
        form = BookingForm(instance=booking, room=room, allow_room_change=True)

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


_UNSET = object()


def get_next_booking(booking):
    return Booking.objects.filter(
        room=booking.room,
        start_time__gte=booking.end_time,
    ).exclude(pk=booking.pk).order_by('start_time').first()


def can_extend(booking, next_booking=_UNSET):
    if booking.end_time <= timezone.now():
        return False
    if next_booking is _UNSET:
        next_booking = get_next_booking(booking)
    target_end = booking.end_time + timedelta(minutes=30)
    return next_booking is None or next_booking.start_time >= target_end


@login_required
def my_bookings(request):
    bookings = Booking.objects.select_related('room').filter(organizer=request.user).order_by('start_time')
    booking_rows = []
    for booking in bookings:
        next_booking = get_next_booking(booking)
        booking_rows.append({
            'booking': booking,
            'can_extend': can_extend(booking, next_booking),
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
    booking_ref = get_object_or_404(Booking, pk=pk, organizer=request.user)
    with transaction.atomic():
        Room.objects.select_for_update().get(pk=booking_ref.room_id)
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=pk,
            organizer=request.user,
        )
        if booking.end_time <= timezone.now():
            messages.warning(request, 'Нельзя продлить уже завершившуюся встречу.')
        elif can_extend(booking):
            booking.end_time = booking.end_time + timedelta(minutes=30)
            booking.save(update_fields=['end_time'])
            messages.success(request, 'Бронь продлена на 30 минут.')
        else:
            messages.warning(request, 'После этой брони нет свободного окна для продления.')
    return redirect('rooms:my_bookings')
