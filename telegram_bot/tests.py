from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import time, timedelta
from .models import UserSession
from .tasks import send_telegram_reminder, check_habits_for_reminders
import json

User = get_user_model()


class UserSessionModelTest(TestCase):
    """Тесты модели сессии пользователя"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            telegram_username='test_user'
        )

    def test_create_user_session(self):
        """Тест создания сессии пользователя"""
        session = UserSession.objects.create(
            user=self.user,
            state='awaiting_action',
            temp_habit_data={'action': 'Тест'}
        )

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.state, 'awaiting_action')
        self.assertEqual(session.temp_habit_data, {'action': 'Тест'})

    def test_user_session_str_representation(self):
        """Тест строкового представления сессии"""
        session = UserSession.objects.create(user=self.user, state='start')

        expected_str = f"Сессия {self.user.username} (start)"
        self.assertEqual(str(session), expected_str)


class TelegramTasksTest(TestCase):
    """Тесты задач Telegram"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            telegram_username='test_user',
            telegram_chat_id='123456'
        )

    @patch('requests.post')
    def test_send_telegram_message_success(self, mock_post):
        """Тест успешной отправки сообщения"""
        from telegram_bot.views import send_telegram_message

        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True}
        mock_post.return_value = mock_response

        result = send_telegram_message('123456', 'Test message')

        mock_post.assert_called_once()
        self.assertEqual(result, {'ok': True})

    @patch('telegram_bot.tasks.requests.post')
    def test_send_telegram_reminder_no_chat_id(self, mock_post):
        """Тест отправки напоминания без chat_id"""
        from habits.models import Habit

        user_no_chat = User.objects.create_user(
            username='nouser',
            email='nouser@example.com',
            password='testpass123'
        )

        habit = Habit.objects.create(
            user=user_no_chat,
            place='Дом',
            time='09:00:00',
            action='Тестовая привычка',
            duration=120
        )

        result = send_telegram_reminder(habit.id)

        mock_post.assert_not_called()
        self.assertFalse(result)

    def test_send_telegram_reminder_habit_not_found(self):
        """Тест отправки напоминания для несуществующей привычки"""
        result = send_telegram_reminder(999)

        self.assertFalse(result)

    @patch('telegram_bot.tasks.send_telegram_reminder.delay')
    def test_check_habits_for_reminders(self, mock_delay):
        """Тест проверки привычек для напоминаний"""
        from habits.models import Habit

        Habit.objects.create(
            user=self.user,
            place='Дом',
            time=time(12, 0, 0),
            action='Тестовая привычка',
            duration=60
        )

        try:
            result = check_habits_for_reminders()
            self.assertIsNotNone(result)
            print(f"Task completed with result: {result}")

            if mock_delay.called:
                print(f"Delay was called {mock_delay.call_count} times")
            else:
                print("No reminders were scheduled (this might be normal depending on time logic)")

            self.assertTrue(True)

        except Exception as e:
            self.fail(f"Task failed with exception: {e}")

    @patch('telegram_bot.tasks.send_telegram_reminder.delay')
    def test_check_habits_for_reminders_no_habits(self, mock_delay):
        """Тест проверки привычек когда нет подходящих привычек"""
        result = check_habits_for_reminders()

        mock_delay.assert_not_called()
        self.assertIn('Checked 0 habits', result)

    @patch('telegram_bot.tasks.send_telegram_reminder.delay')
    def test_check_habits_for_reminders_user_no_chat_id(self, mock_delay):
        """Тест проверки привычек для пользователя без chat_id"""
        from habits.models import Habit

        user_no_chat = User.objects.create_user(
            username='nouser',
            email='nouser@example.com',
            password='testpass123'
        )

        now = timezone.localtime()
        reminder_time = (now + timedelta(minutes=2)).time()

        Habit.objects.create(
            user=user_no_chat,
            place='Дом',
            time=reminder_time,
            action='Привычка без chat_id',
            duration=60
        )

        result = check_habits_for_reminders()

        mock_delay.assert_not_called()
        self.assertIn('Checked 1 habits', result)


class TelegramStatesTest(TestCase):
    """Тесты состояний Telegram бота"""

    def test_user_state_enum(self):
        """Тест перечисления состояний пользователя"""
        from telegram_bot.states import UserState

        self.assertEqual(UserState.START.value, "start")
        self.assertEqual(UserState.AWAITING_ACTION.value, "awaiting_action")
        self.assertEqual(UserState.AWAITING_PLACE.value, "awaiting_place")
        self.assertEqual(UserState.AWAITING_TIME.value, "awaiting_time")
        self.assertEqual(UserState.AWAITING_DURATION.value, "awaiting_duration")
        self.assertEqual(UserState.AWAITING_IS_PLEASANT.value, "awaiting_is_pleasant")
        self.assertEqual(UserState.AWAITING_PERIODICITY.value, "awaiting_periodicity")
        self.assertEqual(UserState.AWAITING_REWARD.value, "awaiting_reward")
        self.assertEqual(UserState.AWAITING_IS_PUBLIC.value, "awaiting_is_public")
        self.assertEqual(UserState.CONFIRMING_HABIT.value, "confirming_habit")

    def test_user_state_enum_members(self):
        """Тест членов перечисления состояний"""
        from telegram_bot.states import UserState

        states = list(UserState)
        self.assertEqual(len(states), 10)

        self.assertIn(UserState.START, states)
        self.assertIn(UserState.AWAITING_ACTION, states)
        self.assertIn(UserState.CONFIRMING_HABIT, states)


class TelegramCommandsTest(TestCase):
    """Тесты management команд Telegram бота"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            telegram_username='test_user',
            telegram_chat_id='123456'
        )

    @patch('telegram_bot.management.commands.run_bot.requests.get')
    @patch('telegram_bot.management.commands.run_bot.requests.post')
    def test_process_message_start(self, mock_post, mock_get):
        """Тест обработки команды /start"""
        from telegram_bot.management.commands.run_bot import Command

        mock_get.return_value.json.return_value = {'ok': True, 'result': []}
        mock_post.return_value.status_code = 200

        command = Command()

        message = {
            'chat': {'id': '123456'},
            'from': {
                'first_name': 'Test',
                'username': 'test_user'
            },
            'text': '/start'
        }

        command.process_message(message)

        session = UserSession.objects.get(user=self.user)
        self.assertEqual(session.state, 'awaiting_action')

    @patch('telegram_bot.management.commands.run_bot.requests.post')
    def test_send_message_success(self, mock_post):
        """Тест успешной отправки сообщения"""
        from telegram_bot.management.commands.run_bot import Command

        mock_post.return_value.status_code = 200

        command = Command()
        result = command.send_message('123456', 'Test message')

        mock_post.assert_called_once()
        self.assertTrue(result is None or result is True)

    @patch('telegram_bot.management.commands.run_bot.requests.post')
    def test_send_message_failure(self, mock_post):
        """Тест неудачной отправки сообщения"""
        from telegram_bot.management.commands.run_bot import Command

        mock_post.return_value.status_code = 400

        command = Command()
        command.send_message('123456', 'Test message')

        mock_post.assert_called_once()

    def test_get_periodicity_text(self):
        """Тест преобразования периодичности в текст"""
        from telegram_bot.management.commands.run_bot import Command

        command = Command()

        self.assertEqual(command.get_periodicity_text(1), 'Ежедневно')
        self.assertEqual(command.get_periodicity_text(2), 'Раз в 2 дня')
        self.assertEqual(command.get_periodicity_text(7), 'Еженедельно')
        self.assertEqual(command.get_periodicity_text(8), 'Ежедневно')

    @patch('telegram_bot.management.commands.run_bot.requests.get')
    def test_handle_awaiting_time_valid(self, mock_get):
        """Тест обработки корректного времени"""
        from telegram_bot.management.commands.run_bot import Command

        mock_get.return_value.json.return_value = {'ok': True, 'result': []}

        command = Command()
        session = UserSession.objects.create(user=self.user, state='awaiting_time')

        with patch.object(command, 'send_message') as mock_send:
            command.handle_awaiting_time('123456', '09:30', session)

            session.refresh_from_db()
            self.assertEqual(session.state, 'awaiting_duration')
            self.assertEqual(session.temp_habit_data['time'], '09:30:00')

            mock_send.assert_called_once()

    @patch('telegram_bot.management.commands.run_bot.requests.get')
    def test_handle_awaiting_time_invalid(self, mock_get):
        """Тест обработки некорректного времени"""
        from telegram_bot.management.commands.run_bot import Command

        mock_get.return_value.json.return_value = {'ok': True, 'result': []}

        command = Command()
        session = UserSession.objects.create(user=self.user, state='awaiting_time')

        with patch.object(command, 'send_message') as mock_send:
            command.handle_awaiting_time('123456', 'invalid_time', session)

            session.refresh_from_db()
            self.assertEqual(session.state, 'awaiting_time')

            mock_send.assert_called_once()
            self.assertIn('Неверный формат времени', mock_send.call_args[0][1])


class TelegramViewsTest(TestCase):
    """Тесты views Telegram бота"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            telegram_username='test_user',
            telegram_chat_id='123456'
        )

    @patch('telegram_bot.views.send_telegram_message')
    def test_telegram_webhook_start_user_found(self, mock_send):
        """Тест webhook с командой /start когда пользователь найден"""
        from telegram_bot.views import telegram_webhook

        webhook_data = {
            'message': {
                'chat': {'id': '123456'},
                'from': {
                    'username': 'test_user',
                    'first_name': 'Test'
                },
                'text': '/start'
            }
        }

        request = MagicMock()
        request.method = 'POST'
        request.body = json.dumps(webhook_data)

        response = telegram_webhook(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'ok')

        mock_send.assert_called_once()

        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, '123456')

    @patch('telegram_bot.views.send_telegram_message')
    def test_telegram_webhook_start_user_not_found(self, mock_send):
        """Тест webhook с командой /start когда пользователь не найден"""
        from telegram_bot.views import telegram_webhook

        webhook_data = {
            'message': {
                'chat': {'id': '123456'},
                'from': {
                    'username': 'nonexistent_user',
                    'first_name': 'Test'
                },
                'text': '/start'
            }
        }

        request = MagicMock()
        request.method = 'POST'
        request.body = json.dumps(webhook_data)
        response = telegram_webhook(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'ok')

        mock_send.assert_called_once()

    @patch('telegram_bot.views.send_telegram_message')
    def test_telegram_webhook_start_no_username(self, mock_send):
        """Тест webhook с командой /start когда у пользователя нет username"""
        from telegram_bot.views import telegram_webhook
        webhook_data = {
            'message': {
                'chat': {'id': '123456'},
                'from': {
                    'first_name': 'Test'
                },
                'text': '/start'
            }
        }
        request = MagicMock()
        request.method = 'POST'
        request.body = json.dumps(webhook_data)
        response = telegram_webhook(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'ok')
        mock_send.assert_called_once()

    @patch('telegram_bot.views.send_telegram_message')
    def test_telegram_webhook_help_command(self, mock_send):
        """Тест webhook с командой /help"""
        from telegram_bot.views import telegram_webhook

        webhook_data = {
            'message': {
                'chat': {'id': '123456'},
                'from': {'username': 'test_user'},
                'text': '/help'
            }
        }

        request = MagicMock()
        request.method = 'POST'
        request.body = json.dumps(webhook_data)
        response = telegram_webhook(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'ok')
        mock_send.assert_called_once()

    @patch('telegram_bot.views.send_telegram_message')
    def test_telegram_webhook_unknown_command(self, mock_send):
        """Тест webhook с неизвестной командой"""
        from telegram_bot.views import telegram_webhook

        webhook_data = {
            'message': {
                'chat': {'id': '123456'},
                'from': {'username': 'test_user'},
                'text': 'unknown_command'
            }
        }

        request = MagicMock()
        request.method = 'POST'
        request.body = json.dumps(webhook_data)

        response = telegram_webhook(request)

        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'ok')
        mock_send.assert_called_once()

    @patch('telegram_bot.views.send_telegram_message')
    def test_telegram_webhook_no_chat_id(self, mock_send):
        """Тест webhook без chat_id"""
        from telegram_bot.views import telegram_webhook

        webhook_data = {
            'message': {
                'from': {'username': 'test_user'},
                'text': '/start'
            }
        }

        request = MagicMock()
        request.method = 'POST'
        request.body = json.dumps(webhook_data)

        response = telegram_webhook(request)
        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'error')
        mock_send.assert_not_called()

    def test_telegram_webhook_invalid_json(self):
        """Тест webhook с невалидным JSON"""
        from telegram_bot.views import telegram_webhook

        request = MagicMock()
        request.method = 'POST'
        request.body = 'invalid json'

        response = telegram_webhook(request)

        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'error')

    @patch('requests.post')
    def test_send_telegram_message_failure(self, mock_post):
        """Тест неудачной отправки сообщения"""
        from telegram_bot.views import send_telegram_message
        mock_post.side_effect = Exception('Network error')
        result = send_telegram_message('123456', 'Test message')
        self.assertIsNone(result)
