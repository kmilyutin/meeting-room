from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from rooms.models import Booking, Equipment, Room


ROOM_IMAGES = [
    'rooms_images/room-card-placeholder.png',
    'rooms_images/room-card-placeholder_1DVNKL5.png',
    'rooms_images/room-card-placeholder_4WXfsmj.png',
]


def ensure_demo_data():
    user, created = User.objects.get_or_create(
        username='sonya',
        defaults={'email': 'sonya@example.com'},
    )
    if created or not user.has_usable_password():
        user.set_password('booked12345')
        user.save()

    equipment_names = ['Экран', 'Wi-Fi', 'Проектор', 'Доска', 'HDMI', 'Флипчарт']
    equipment = {
        name: Equipment.objects.get_or_create(name=name, defaults={'description': ''})[0]
        for name in equipment_names
    }

    rooms_data = [
        ('Алтай', 8, 'Комната для встреч, созвонов и командной работы.', 'available', ['Экран', 'Wi-Fi', 'Доска']),
        ('Байкал', 12, 'Просторная комната с проектором для презентаций.', 'busy', ['Проектор', 'Доска', 'HDMI']),
        ('Онега', 4, 'Небольшая комната для быстрых синков и интервью.', 'available', ['Wi-Fi', 'Экран']),
        ('Север', 6, 'Комната временно закрыта на обслуживание.', 'unavailable', ['Wi-Fi', 'HDMI']),
        ('Ладога', 10, 'Тихая переговорная для рабочих сессий и воркшопов.', 'available', ['Флипчарт', 'Доска']),
        ('Кама', 5, 'Компактная комната рядом с open space.', 'available', ['Экран', 'HDMI']),
        ('Енисей', 16, 'Большая переговорная для общих встреч.', 'busy', ['Проектор', 'Экран', 'Wi-Fi']),
    ]

    for index, (name, capacity, description, status, item_names) in enumerate(rooms_data):
        room, _ = Room.objects.get_or_create(
            name=name,
            defaults={
                'capacity': capacity,
                'description': description,
                'status': status,
                'image': ROOM_IMAGES[index % len(ROOM_IMAGES)],
            },
        )
        changed = False
        for field, value in {
            'capacity': capacity,
            'description': description,
            'status': status,
        }.items():
            if getattr(room, field) != value:
                setattr(room, field, value)
                changed = True
        if not room.image:
            room.image = ROOM_IMAGES[index % len(ROOM_IMAGES)]
            changed = True
        if changed:
            room.save()
        room.equipment.set([equipment[item_name] for item_name in item_names])

    day = timezone.localdate() + timedelta(days=1)
    booking_specs = [
        ('Планерка продукта', 'Алтай', time(9, 0), time(10, 0), 'Ежедневная встреча команды.'),
        ('Демо для команды', 'Алтай', time(10, 0), time(11, 0), 'Бронь с доступным продлением.'),
        ('Интервью', 'Байкал', time(12, 30), time(13, 30), 'Встреча с кандидатом.'),
        ('Ретро', 'Онега', time(14, 0), time(15, 0), 'Командная ретроспектива.'),
    ]
    for title, room_name, start, end, description in booking_specs:
        room = Room.objects.get(name=room_name)
        start_at = timezone.make_aware(datetime.combine(day, start), timezone.get_current_timezone())
        end_at = timezone.make_aware(datetime.combine(day, end), timezone.get_current_timezone())
        Booking.objects.get_or_create(
            name=title,
            defaults={
                'start_time': start_at,
                'end_time': end_at,
                'description': description,
                'organizer': user,
                'room': room,
            },
        )


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


def room_has_conflict(room, start_at, end_at):
    if not start_at or not end_at or end_at <= start_at:
        return False
    return Booking.objects.filter(
        room=room,
        start_time__lt=end_at,
        end_time__gt=start_at,
    ).exists()


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
    ensure_demo_data()
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
    ensure_demo_data()
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
    ensure_demo_data()
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


def can_extend(booking):
    next_booking = Booking.objects.filter(
        room=booking.room,
        start_time__gte=booking.end_time,
    ).exclude(pk=booking.pk).order_by('start_time').first()
    target_end = booking.end_time + timedelta(minutes=30)
    return next_booking is None or next_booking.start_time >= target_end


@login_required
def my_bookings(request):
    ensure_demo_data()
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
