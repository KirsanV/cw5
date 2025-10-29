from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status, serializers
from django.urls import reverse
from datetime import time
from .models import Habit


User = get_user_model()


class HabitModelTest(TestCase):
    """Тесты модели привычки"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_habit(self):
        """Тест создания привычки"""
        habit = Habit.objects.create(
            user=self.user,
            place='Дом',
            time=time(9, 0, 0),
            action='Утренняя зарядка',
            duration=120,
            is_public=True
        )

        self.assertEqual(habit.user, self.user)
        self.assertEqual(habit.place, 'Дом')
        self.assertEqual(habit.action, 'Утренняя зарядка')
        self.assertEqual(habit.duration, 120)
        self.assertTrue(habit.is_public)
        self.assertFalse(habit.is_pleasant)

    def test_habit_str_representation(self):
        """Тест строкового представления привычки"""
        habit = Habit.objects.create(
            user=self.user,
            place='Дом',
            time=time(9, 0, 0),
            action='Утренняя зарядка',
            duration=120
        )

        habit_str = str(habit)
        self.assertIn(self.user.username, habit_str)
        self.assertIn('Утренняя зарядка', habit_str)
        self.assertIn('09:00', habit_str)
        self.assertTrue(len(habit_str) > 0)

    def test_habit_validation_duration_too_long(self):
        """Тест валидации времени выполнения"""
        habit = Habit(
            user=self.user,
            place='Дом',
            time=time(9, 0, 0),
            action='Тест',
            duration=150
        )

        with self.assertRaises(Exception):
            habit.full_clean()

    def test_pleasant_habit_cannot_have_reward(self):
        """Тест что приятная привычка не может иметь вознаграждение"""
        habit = Habit(
            user=self.user,
            place='Дом',
            time=time(9, 0, 0),
            action='Приятная привычка',
            duration=60,
            is_pleasant=True,
            reward='Шоколадка'
        )

        with self.assertRaises(Exception):
            habit.full_clean()


class HabitAPITest(APITestCase):
    """Тесты API привычек"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        self.habits_url = reverse('habits:habit-list-create')
        self.public_habits_url = reverse('habits:public-habit-list')
        self.habit = Habit.objects.create(
            user=self.user,
            place='Дом',
            time=time(9, 0, 0),
            action='Личная привычка',
            duration=120,
            is_public=False
        )

        self.public_habit = Habit.objects.create(
            user=self.other_user,
            place='Парк',
            time=time(18, 0, 0),
            action='Публичная привычка',
            duration=90,
            is_public=True
        )

    def test_get_habits_authenticated(self):
        """Тест получения списка привычек аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.habits_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['action'], 'Личная привычка')
        else:
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['action'], 'Личная привычка')

    def test_get_habits_unauthenticated(self):
        """Тест получения списка привычек неаутентифицированным пользователем"""
        response = self.client.get(self.habits_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_habit_authenticated(self):
        """Тест создания привычки аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.user)

        habit_data = {
            'place': 'Офис',
            'time': '10:00:00',
            'action': 'Новая привычка',
            'duration': 60,
            'is_public': True
        }

        response = self.client.post(self.habits_url, habit_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Habit.objects.count(), 3)
        self.assertEqual(response.data['action'], 'Новая привычка')
        self.assertEqual(response.data['user'], self.user.id)

    def test_get_public_habits(self):
        """Тест получения списка публичных привычек"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.public_habits_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['action'], 'Публичная привычка')
        else:
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['action'], 'Публичная привычка')

    def test_update_own_habit(self):
        """Тест обновления своей привычки"""
        self.client.force_authenticate(user=self.user)

        update_data = {
            'action': 'Обновленная привычка',
            'place': 'Новое место',
            'time': '11:00:00',
            'duration': 90
        }

        url = reverse('habits:habit-detail', kwargs={'pk': self.habit.id})
        response = self.client.patch(url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.action, 'Обновленная привычка')

    def test_cannot_update_other_user_habit(self):
        """Тест что нельзя обновить чужую привычку"""
        self.client.force_authenticate(user=self.user)

        update_data = {'action': 'Взломанная привычка'}
        url = reverse('habits:habit-detail', kwargs={'pk': self.public_habit.id})
        response = self.client.patch(url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_habit(self):
        """Тест удаления своей привычки"""
        self.client.force_authenticate(user=self.user)

        url = reverse('habits:habit-detail', kwargs={'pk': self.habit.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Habit.objects.count(), 1)

    def test_habit_validation_api(self):
        """Тест валидации привычки через API"""
        self.client.force_authenticate(user=self.user)

        invalid_habit_data = {
            'place': 'Дом',
            'time': '10:00:00',
            'action': 'Привычка с долгим выполнением',
            'duration': 150,
            'is_public': True
        }

        response = self.client.post(self.habits_url, invalid_habit_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            'duration' in response.data
            or 'non_field_errors' in response.data
            or any('120 секунд' in str(error) for error in response.data.values() if isinstance(error, list))
        )


class HabitValidatorTest(TestCase):
    """Тесты валидаторов привычек"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.pleasant_habit = Habit.objects.create(
            user=self.user,
            place='Дом',
            time=time(9, 0, 0),
            action='Приятная привычка',
            duration=60,
            is_pleasant=True
        )

    def test_related_habit_must_be_pleasant(self):
        """Тест что связанная привычка должна быть приятной"""
        useful_habit = Habit(
            user=self.user,
            place='Дом',
            time=time(10, 0, 0),
            action='Полезная привычка',
            duration=120,
            is_pleasant=False,
            related_habit=self.pleasant_habit
        )

        try:
            useful_habit.full_clean()
        except Exception as e:
            self.fail(f"Валидация не должна падать: {e}")

    def test_pleasant_habit_cannot_have_related_habit(self):
        """Тест что приятная привычка не может иметь связанную привычку"""
        another_pleasant = Habit(
            user=self.user,
            place='Дом',
            time=time(11, 0, 0),
            action='Другая приятная',
            duration=60,
            is_pleasant=True,
            related_habit=self.pleasant_habit
        )

        with self.assertRaises(Exception):
            another_pleasant.full_clean()


class HabitValidatorsTest(TestCase):
    """Тесты валидаторов привычек"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_validate_duration_valid(self):
        """Тест валидации корректной продолжительности"""
        from habits.validators import validate_duration

        self.assertEqual(validate_duration(60), 60)
        self.assertEqual(validate_duration(120), 120)
        self.assertEqual(validate_duration(1), 1)

    def test_validate_duration_invalid(self):
        """Тест валидации слишком долгой продолжительности"""
        from habits.validators import validate_duration

        with self.assertRaises(serializers.ValidationError) as context:
            validate_duration(121)
        self.assertIn('120 секунд', str(context.exception))

        with self.assertRaises(serializers.ValidationError):
            validate_duration(150)

        with self.assertRaises(serializers.ValidationError):
            validate_duration(1000)

    def test_validate_duration_edge_cases(self):
        """Тест граничных случаев валидации продолжительности"""
        from habits.validators import validate_duration

        self.assertEqual(validate_duration(120), 120)

        with self.assertRaises(serializers.ValidationError):
            validate_duration(121)

        with self.assertRaises(serializers.ValidationError):
            validate_duration(1000)

    def test_validate_periodicity_valid(self):
        """Тест валидации корректной периодичности"""
        from habits.validators import validate_periodicity

        self.assertEqual(validate_periodicity(1), 1)
        self.assertEqual(validate_periodicity(7), 7)
        self.assertEqual(validate_periodicity(3), 3)

    def test_validate_periodicity_invalid(self):
        """Тест валидации слишком редкой периодичности"""
        from habits.validators import validate_periodicity

        with self.assertRaises(serializers.ValidationError) as context:
            validate_periodicity(8)
        self.assertIn('1 раз в 7 дней', str(context.exception))

        with self.assertRaises(serializers.ValidationError):
            validate_periodicity(10)

        with self.assertRaises(serializers.ValidationError):
            validate_periodicity(100)

    def test_validate_periodicity_edge_cases(self):
        """Тест граничных случаев валидации периодичности"""
        from habits.validators import validate_periodicity

        self.assertEqual(validate_periodicity(7), 7)

        with self.assertRaises(serializers.ValidationError):
            validate_periodicity(8)

        with self.assertRaises(serializers.ValidationError):
            validate_periodicity(100)

    def test_validate_duration_in_serializer(self):
        """Тест что валидатор работает в сериализаторе"""
        from habits.validators import validate_duration

        class TestSerializer(serializers.Serializer):
            duration = serializers.IntegerField(validators=[validate_duration])

        serializer = TestSerializer(data={'duration': 90})
        self.assertTrue(serializer.is_valid())

        serializer = TestSerializer(data={'duration': 150})
        self.assertFalse(serializer.is_valid())
        self.assertIn('duration', serializer.errors)
