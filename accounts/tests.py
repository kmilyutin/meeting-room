from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class AccountViewTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            'username': 'new-user',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        data.update(overrides)
        return data

    def test_registration_creates_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse('accounts:register'),
            self.registration_data(),
        )

        self.assertRedirects(response, reverse('accounts:login'))
        self.assertTrue(
            User.objects.filter(username='new-user').exists(),
        )

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(
            username='new-user',
            password='StrongPass123!',
        )

        response = self.client.post(
            reverse('accounts:register'),
            self.registration_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'username',
            response.context['form'].errors,
        )
        self.assertEqual(
            User.objects.filter(username='new-user').count(),
            1,
        )

    def test_login_accepts_valid_credentials(self):
        user = User.objects.create_user(
            username='member',
            password='StrongPass123!',
        )

        response = self.client.post(
            reverse('accounts:login'),
            {
                'username': 'member',
                'password': 'StrongPass123!',
            },
        )

        self.assertRedirects(response, reverse('rooms:index'))
        self.assertEqual(
            int(self.client.session['_auth_user_id']),
            user.pk,
        )

    def test_login_rejects_invalid_password(self):
        User.objects.create_user(
            username='member',
            password='StrongPass123!',
        )

        response = self.client.post(
            reverse('accounts:login'),
            {
                'username': 'member',
                'password': 'wrong-password',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(response.context['form'].errors)

    def test_logout_ends_session(self):
        user = User.objects.create_user(
            username='member',
            password='StrongPass123!',
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('accounts:logout'),
        )

        self.assertRedirects(
            response,
            reverse('rooms:index'),
        )
        self.assertNotIn(
            '_auth_user_id',
            self.client.session,
        )

    def test_profile_requires_login(self):
        response = self.client.get(
            reverse('accounts:profile'),
        )

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:profile')}",
        )

    def test_authenticated_user_can_open_profile(self):
        user = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='StrongPass123!',
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse('accounts:profile'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'member@example.com')

    def test_user_string_is_username(self):
        user = User(username='member')

        self.assertEqual(str(user), 'member')
        
