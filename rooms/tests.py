from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rooms.forms import BookingForm
from rooms.models import Booking, Equipment, Room

User = get_user_model()


def create_room(name='Тестовая', capacity=10, status='available'):
    return Room.objects.create(
        name=name,
        capacity=capacity,
        status=status,
        image='rooms_images/test.png',
    )


def future_dt(days=1, hour=10, minute=0):
    base = timezone.localtime(timezone.now() + timedelta(days=days))
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def create_booking(room, user, start, end, name='Встреча', participants=2):
    return Booking.objects.create(
        name=name,
        room=room,
        organizer=user,
        start_time=start,
        end_time=end,
        participants=participants,
    )


def form_data(start, end, name='Встреча', participants=2, description=''):
    return {
        'name': name,
        'description': description,
        'start_time': timezone.localtime(start).strftime('%Y-%m-%dT%H:%M'),
        'end_time': timezone.localtime(end).strftime('%Y-%m-%dT%H:%M'),
        'participants': participants,
    }


class BookingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='organizer', password='pass12345')
        self.room = create_room()

    def test_clean_rejects_end_before_start(self):
        booking = Booking(
            name='Встреча',
            room=self.room,
            organizer=self.user,
            start_time=future_dt(hour=12),
            end_time=future_dt(hour=10),
        )
        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_db_constraint_rejects_end_before_start(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_booking(self.room, self.user, future_dt(hour=12), future_dt(hour=10))

    def test_booking_name_is_not_unique(self):
        create_booking(self.room, self.user, future_dt(hour=10), future_dt(hour=11), name='Планёрка')
        other = create_booking(self.room, self.user, future_dt(hour=12), future_dt(hour=13), name='Планёрка')
        self.assertEqual(Booking.objects.filter(name='Планёрка').count(), 2)
        self.assertIsNotNone(other.pk)

    def test_room_zero_capacity_rejected_by_validation(self):
        room = Room(name='Нулевая', capacity=0, image='rooms_images/test.png')
        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_room_zero_capacity_rejected_by_db(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(name='Нулевая', capacity=0, image='rooms_images/test.png')


class BookingFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='organizer', password='pass12345')
        self.room = create_room(capacity=5)

    def test_valid_form(self):
        form = BookingForm(form_data(future_dt(hour=10), future_dt(hour=11)), room=self.room)
        self.assertTrue(form.is_valid(), form.errors)

    def test_end_before_start_rejected(self):
        form = BookingForm(form_data(future_dt(hour=12), future_dt(hour=10)), room=self.room)
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)

    def test_past_time_rejected(self):
        start = timezone.now() - timedelta(hours=3)
        form = BookingForm(form_data(start, start + timedelta(hours=1)), room=self.room)
        self.assertFalse(form.is_valid())
        self.assertIn('start_time', form.errors)

    def test_participants_over_capacity_rejected(self):
        form = BookingForm(
            form_data(future_dt(hour=10), future_dt(hour=11), participants=6),
            room=self.room,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('participants', form.errors)

    def test_unavailable_room_rejected(self):
        room = create_room(name='Закрытая', status='unavailable')
        form = BookingForm(form_data(future_dt(hour=10), future_dt(hour=11)), room=room)
        self.assertFalse(form.is_valid())

    def test_overlap_rejected(self):
        create_booking(self.room, self.user, future_dt(hour=10), future_dt(hour=12))
        form = BookingForm(form_data(future_dt(hour=11), future_dt(hour=13)), room=self.room)
        self.assertFalse(form.is_valid())

    def test_adjacent_bookings_allowed(self):
        create_booking(self.room, self.user, future_dt(hour=10), future_dt(hour=11))
        form = BookingForm(form_data(future_dt(hour=11), future_dt(hour=12)), room=self.room)
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_does_not_conflict_with_itself(self):
        booking = create_booking(self.room, self.user, future_dt(hour=10), future_dt(hour=11))
        form = BookingForm(
            form_data(future_dt(hour=10), future_dt(hour=12)),
            instance=booking,
            room=self.room,
        )
        self.assertTrue(form.is_valid(), form.errors)


class SearchViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='organizer', password='pass12345')

    def search(self, **params):
        return self.client.get(reverse('rooms:index'), params)

    def test_only_available_rooms_shown(self):
        available = create_room(name='Свободная', status='available')
        create_room(name='Занятая', status='busy')
        create_room(name='Закрытая', status='unavailable')
        response = self.search()
        names = [room.name for room in response.context['rooms']]
        self.assertEqual(names, [available.name])

    def test_conflicting_room_hidden_for_requested_time(self):
        room = create_room(name='Конфликтная')
        free_room = create_room(name='Свободная', capacity=12)
        day = future_dt().date()
        create_booking(room, self.user, future_dt(hour=10), future_dt(hour=12))
        response = self.search(date=day.strftime('%Y-%m-%d'), start_time='10:30', end_time='11:30')
        names = [r.name for r in response.context['rooms']]
        self.assertEqual(names, [free_room.name])

    def test_incomplete_time_rejected(self):
        create_room()
        response = self.search(start_time='10:00')
        self.assertEqual(response.context['rooms'], [])
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('время' in m.lower() for m in messages))

    def test_invalid_time_format_rejected(self):
        create_room()
        response = self.search(start_time='abc', end_time='11:00')
        self.assertEqual(response.context['rooms'], [])

    def test_end_before_start_rejected(self):
        create_room()
        response = self.search(start_time='12:00', end_time='10:00')
        self.assertEqual(response.context['rooms'], [])

    def test_rooms_sorted_by_minimal_sufficient_capacity(self):
        create_room(name='Большая', capacity=16)
        create_room(name='Малая', capacity=4)
        create_room(name='Средняя', capacity=8)
        response = self.search(participants='4')
        capacities = [room.capacity for room in response.context['rooms']]
        self.assertEqual(capacities, [4, 8, 16])

    def test_participants_filter(self):
        create_room(name='Малая', capacity=4)
        big = create_room(name='Большая', capacity=12)
        response = self.search(participants='10')
        names = [room.name for room in response.context['rooms']]
        self.assertEqual(names, [big.name])

    def test_invalid_participants_rejected(self):
        create_room()
        response = self.search(participants='-3')
        self.assertEqual(response.context['rooms'], [])

    def test_equipment_filter(self):
        screen = Equipment.objects.create(name='Экран')
        board = Equipment.objects.create(name='Доска')
        with_screen = create_room(name='С экраном')
        with_screen.equipment.add(screen)
        with_board = create_room(name='С доской', capacity=6)
        with_board.equipment.add(board)
        response = self.search(equipment='Экран')
        names = [room.name for room in response.context['rooms']]
        self.assertEqual(names, [with_screen.name])


class BookingCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='organizer', password='pass12345')
        self.room = create_room()
        self.url = reverse('rooms:book_room', kwargs={'pk': self.room.pk})

    def test_login_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_get_shows_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], BookingForm)

    def test_post_creates_booking_with_current_user_as_organizer(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, form_data(future_dt(hour=10), future_dt(hour=11)))
        self.assertRedirects(response, reverse('rooms:my_bookings'))
        booking = Booking.objects.get()
        self.assertEqual(booking.organizer, self.user)
        self.assertEqual(booking.room, self.room)

    def test_post_conflict_does_not_create_booking(self):
        create_booking(self.room, self.user, future_dt(hour=10), future_dt(hour=12))
        self.client.force_login(self.user)
        response = self.client.post(self.url, form_data(future_dt(hour=11), future_dt(hour=13)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 1)

    def test_post_unavailable_room_rejected(self):
        room = create_room(name='Закрытая', status='unavailable')
        self.client.force_login(self.user)
        url = reverse('rooms:book_room', kwargs={'pk': room.pk})
        response = self.client.post(url, form_data(future_dt(hour=10), future_dt(hour=11)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)


class BookingEditViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.room = create_room()
        self.booking = create_booking(self.room, self.owner, future_dt(hour=10), future_dt(hour=11))
        self.url = reverse('rooms:edit_booking', kwargs={'pk': self.booking.pk})

    def test_owner_can_edit(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            form_data(future_dt(hour=14), future_dt(hour=15), name='Новое имя'),
        )
        self.assertRedirects(response, reverse('rooms:my_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.name, 'Новое имя')
        self.assertEqual(timezone.localtime(self.booking.start_time).hour, 14)

    def test_foreign_booking_returns_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        response = self.client.post(self.url, form_data(future_dt(hour=14), future_dt(hour=15)))
        self.assertEqual(response.status_code, 404)

    def test_edit_conflicting_time_rejected(self):
        create_booking(self.room, self.other, future_dt(hour=12), future_dt(hour=13), name='Чужая')
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            form_data(future_dt(hour=12, minute=30), future_dt(hour=13, minute=30)),
        )
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(timezone.localtime(self.booking.start_time).hour, 10)


class BookingDeleteViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.room = create_room()
        self.booking = create_booking(self.room, self.owner, future_dt(hour=10), future_dt(hour=11))
        self.url = reverse('rooms:delete_booking', kwargs={'pk': self.booking.pk})

    def test_get_shows_confirmation_and_does_not_delete(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Удалить')
        self.assertTrue(Booking.objects.filter(pk=self.booking.pk).exists())

    def test_post_deletes_booking(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('rooms:my_bookings'))
        self.assertFalse(Booking.objects.filter(pk=self.booking.pk).exists())

    def test_foreign_booking_returns_404(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Booking.objects.filter(pk=self.booking.pk).exists())


class TimelineAndExtendTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.room = create_room()

    def test_timeline_includes_booking_crossing_midnight(self):
        start = future_dt(days=1, hour=23)
        end = start + timedelta(hours=2)
        create_booking(self.room, self.owner, start, end, name='Ночная')
        next_day = (start + timedelta(days=1)).date()
        response = self.client.get(reverse('rooms:index'), {'date': next_day.strftime('%Y-%m-%d')})
        titles = [row['title'] for row in response.context['timeline_rows']]
        self.assertIn('Ночная', titles)

    def test_room_detail_bookings_sorted(self):
        day = future_dt().date()
        create_booking(self.room, self.owner, future_dt(hour=14), future_dt(hour=15), name='Поздняя')
        create_booking(self.room, self.owner, future_dt(hour=9), future_dt(hour=10), name='Ранняя')
        response = self.client.get(
            reverse('rooms:detail', kwargs={'pk': self.room.pk}),
            {'date': day.strftime('%Y-%m-%d')},
        )
        names = [booking.name for booking in response.context['bookings']]
        self.assertEqual(names, ['Ранняя', 'Поздняя'])

    def extend(self, booking):
        return self.client.post(reverse('rooms:extend_booking', kwargs={'pk': booking.pk}))

    def test_extend_adds_30_minutes(self):
        booking = create_booking(self.room, self.owner, future_dt(hour=10), future_dt(hour=11))
        old_end = booking.end_time
        self.client.force_login(self.owner)
        self.extend(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.end_time, old_end + timedelta(minutes=30))

    def test_extend_blocked_by_next_booking(self):
        booking = create_booking(self.room, self.owner, future_dt(hour=10), future_dt(hour=11))
        create_booking(self.room, self.other, future_dt(hour=11), future_dt(hour=12), name='Следом')
        old_end = booking.end_time
        self.client.force_login(self.owner)
        self.extend(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.end_time, old_end)

    def test_extend_past_booking_forbidden(self):
        start = timezone.now() - timedelta(hours=3)
        booking = create_booking(self.room, self.owner, start, start + timedelta(hours=1), name='Прошедшая')
        old_end = booking.end_time
        self.client.force_login(self.owner)
        self.extend(booking)
        booking.refresh_from_db()
        self.assertEqual(booking.end_time, old_end)

    def test_extend_foreign_booking_returns_404(self):
        booking = create_booking(self.room, self.owner, future_dt(hour=10), future_dt(hour=11))
        self.client.force_login(self.other)
        response = self.extend(booking)
        self.assertEqual(response.status_code, 404)
