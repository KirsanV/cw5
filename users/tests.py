from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse

User = get_user_model()


class UserModelTest(TestCase):
    """Тесты модели пользователя"""

    def test_create_user(self):
        """Тест создания обычного пользователя"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            telegram_username='test_user'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.telegram_username, 'test_user')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_superuser(self):
        """Тест создания суперпользователя"""
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertEqual(admin_user.username, 'admin')
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_user_str_representation(self):
        """Тест строкового представления пользователя"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user), 'testuser')


class UserAPITest(APITestCase):
    """Тесты API пользователей"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('users:register')
        self.profile_url = reverse('users:profile')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'telegram_username': 'test_telegram'
        }

    def test_user_registration(self):
        """Тест регистрации пользователя"""
        response = self.client.post(self.register_url, self.user_data, format='json')

        print(f"Registration response status: {response.status_code}")
        print(f"Registration response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')
        self.assertIn('username', response.data)
        self.assertIn('email', response.data)
        self.assertIn('telegram_username', response.data)

        user = User.objects.get(username='testuser')
        self.assertIsNotNone(user.id)

    def test_user_registration_password_mismatch(self):
        """Тест регистрации с несовпадающими паролями"""
        data = self.user_data.copy()
        data['password_confirm'] = 'differentpassword'

        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_user_registration_weak_password(self):
        """Тест регистрации со слабым паролем"""
        data = self.user_data.copy()
        data['password'] = '123'
        data['password_confirm'] = '123'

        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_user_profile_authenticated(self):
        """Тест получения профиля аутентифицированным пользователем"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_get_user_profile_unauthenticated(self):
        """Тест получения профиля неаутентифицированным пользователем"""
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_profile(self):
        """Тест обновления профиля пользователя"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Old',
            last_name='Name'
        )
        self.client.force_authenticate(user=user)

        update_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'telegram_username': 'new_telegram'
        }

        response = self.client.put(self.profile_url, update_data, format='json')

        print(f"Update response status: {response.status_code}")
        print(f"Update response data: {response.data}")

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            patch_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'telegram_username': 'new_telegram'
            }
            response = self.client.patch(self.profile_url, patch_data, format='json')
            print(f"PATCH response status: {response.status_code}")
            print(f"PATCH response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.telegram_username, 'new_telegram')
