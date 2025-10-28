from django.core.management.base import BaseCommand
import requests
import time
from datetime import time as dt_time
from config.settings import TELEGRAM_BOT_TOKEN
from users.models import User
from telegram_bot.models import UserSession
from habits.models import Habit


class Command(BaseCommand):
    help = 'Run Telegram bot with long polling'

    def handle(self, *args, **options):
        self.stdout.write('🤖 Starting Interactive Habits Bot...')
        self.stdout.write('🎯 Bot is ready to create habits!')

        offset = 0

        while True:
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
                params = {
                    'offset': offset,
                    'timeout': 30,
                    'allowed_updates': ['message', 'callback_query']
                }

                response = requests.get(url, params=params, timeout=35)

                if response.status_code == 200:
                    data = response.json()

                    if data.get('ok'):
                        updates = data.get('result', [])

                        if updates:
                            self.stdout.write(f'📩 Found {len(updates)} new messages')

                            for update in updates:
                                offset = update['update_id'] + 1
                                self.process_update(update)

                time.sleep(1)

            except Exception as e:
                self.stdout.write(f'❌ Error: {e}')
                time.sleep(5)

    def process_update(self, update):
        """Обработка входящего сообщения"""
        if 'message' in update:
            self.process_message(update['message'])
        elif 'callback_query' in update:
            self.process_callback(update['callback_query'])

    def process_message(self, message):
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        user_name = message['from'].get('first_name', 'User')
        username = message['from'].get('username', '')

        self.stdout.write(f'💬 Message from {user_name} (@{username}): "{text}"')

        user, session = self.get_or_create_user_session(username, chat_id, user_name)

        if not user or not session:
            self.send_message(chat_id, "❌ Ошибка: пользователь не найден. Сначала зарегистрируйтесь на сайте.")
            return

        if text == '/start':
            self.handle_start(chat_id, user, session)
        elif text == '/cancel':
            self.handle_cancel(chat_id, session)
        else:
            self.handle_state(chat_id, text, user, session)

    def get_or_create_user_session(self, username, chat_id, user_name):
        """Получаем или создаем пользователя и сессию"""
        if not username:
            return None, None

        try:
            user = User.objects.get(telegram_username=username)
            user.telegram_chat_id = chat_id
            user.save()

            session, created = UserSession.objects.get_or_create(
                user=user,
                defaults={'state': 'start'}
            )

            return user, session

        except User.DoesNotExist:
            user = User.objects.create(
                username=f"telegram_{username}",
                telegram_username=username,
                telegram_chat_id=chat_id,
                first_name=user_name,
                is_active=True
            )

            session = UserSession.objects.create(user=user, state='start')
            return user, session

    def handle_start(self, chat_id, user, session):
        """Обработка команды /start"""
        session.state = 'awaiting_action'
        session.temp_habit_data = {}
        session.save()

        welcome_text = f"""👋 Привет, {user.first_name}!

Я помогу тебе создать полезную привычку! 📝

Давай начнем!

❓ **Какую полезную привычку вы хотели бы приобрести?**

_Опишите действие, которое хотите выполнять_"""

        self.send_message(chat_id, welcome_text)

    def handle_cancel(self, chat_id, session):
        """Отмена создания привычки"""
        session.state = 'start'
        session.temp_habit_data = {}
        session.save()

        self.send_message(chat_id, "❌ Создание привычки отменено. Используйте /start чтобы начать заново.")

    def handle_state(self, chat_id, text, user, session):
        """Обработка состояний диалога"""
        if session.state == 'awaiting_action':
            self.handle_awaiting_action(chat_id, text, session)
        elif session.state == 'awaiting_place':
            self.handle_awaiting_place(chat_id, text, session)
        elif session.state == 'awaiting_time':
            self.handle_awaiting_time(chat_id, text, session)
        elif session.state == 'awaiting_duration':
            self.handle_awaiting_duration(chat_id, text, session)
        elif session.state == 'awaiting_is_pleasant':
            self.handle_awaiting_is_pleasant(chat_id, text, session)
        elif session.state == 'awaiting_periodicity':
            self.handle_awaiting_periodicity(chat_id, text, session)
        elif session.state == 'awaiting_reward':
            self.handle_awaiting_reward(chat_id, text, session)
        elif session.state == 'awaiting_is_public':
            self.handle_awaiting_is_public(chat_id, text, session, user)
        else:
            self.send_message(chat_id, "Используйте /start чтобы начать создание привычки.")

    def handle_awaiting_action(self, chat_id, text, session):
        """Обработка действия привычки"""
        session.temp_habit_data['action'] = text
        session.state = 'awaiting_place'
        session.save()

        question = """📍 **Место где нужно проводить действие?**

_Где вы будете выполнять эту привычку?_
Например: Дом, Офис, Парк, Спортзал"""

        self.send_message(chat_id, question)

    def handle_awaiting_place(self, chat_id, text, session):
        """Обработка места привычки"""
        session.temp_habit_data['place'] = text
        session.state = 'awaiting_time'
        session.save()

        question = """⏰ **Во сколько по МСК вы хотите проводить действие?**

_Введите время в формате ЧЧ:ММ_
Например: 09:00, 18:30, 22:00"""

        self.send_message(chat_id, question)

    def handle_awaiting_time(self, chat_id, text, session):
        """Обработка времени привычки"""
        try:
            hours, minutes = map(int, text.split(':'))
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError

            session.temp_habit_data['time'] = f"{hours:02d}:{minutes:02d}:00"
            session.state = 'awaiting_duration'
            session.save()

            question = """⏱️ **Сколько времени займет выполнение привычки?**

_Введите время в секундах (максимум 120)_
Например: 60 (1 минута), 120 (2 минуты)"""

            self.send_message(chat_id, question)

        except (ValueError, IndexError):
            self.send_message(chat_id, "❌ Неверный формат времени. Используйте ЧЧ:ММ, например: 09:30")

    def handle_awaiting_duration(self, chat_id, text, session):
        """Обработка длительности привычки"""
        try:
            duration = int(text)
            if duration > 120:
                self.send_message(
                    chat_id,
                    "❌ Время выполнения не должно превышать 120 секунд. Введите другое значение:"
                )
                return

            session.temp_habit_data['duration'] = duration
            session.state = 'awaiting_is_pleasant'
            session.save()

            question = """😊 **Это приятная привычка?**

Приятная привычка - это способ вознаградить себя за выполнение полезной привычки.

_Ответьте Да или Нет_"""

            self.send_message(chat_id, question)

        except ValueError:
            self.send_message(chat_id, "❌ Введите число (в секундах), например: 60")

    def handle_awaiting_is_pleasant(self, chat_id, text, session):
        """Обработка типа привычки"""
        text_lower = text.lower()
        if text_lower in ['да', 'yes', 'y', 'д']:
            is_pleasant = True
        elif text_lower in ['нет', 'no', 'n', 'н']:
            is_pleasant = False
        else:
            self.send_message(chat_id, "❌ Пожалуйста, ответьте Да или Нет")
            return

        session.temp_habit_data['is_pleasant'] = is_pleasant
        session.state = 'awaiting_periodicity'
        session.save()

        if is_pleasant:
            question = """🔄 **Как часто выполнять привычку?**

_Выберите периодичность:_
1 - Ежедневно
2 - Раз в 2 дня
3 - Раз в 3 дня
4 - Раз в 4 дня
5 - Раз в 5 дней
6 - Раз в 6 дней
7 - Еженедельно

_Введите число от 1 до 7_"""
        else:
            question = """🔄 **Как часто выполнять привычку?**

_Выберите периодичность:_
1 - Ежедневно
2 - Раз в 2 дня
3 - Раз в 3 дня
4 - Раз в 4 дня
5 - Раз в 5 дней
6 - Раз в 6 дней
7 - Еженедельно

_Введите число от 1 до 7_"""

        self.send_message(chat_id, question)

    def handle_awaiting_periodicity(self, chat_id, text, session):
        """Обработка периодичности"""
        try:
            periodicity = int(text)
            if not 1 <= periodicity <= 7:
                raise ValueError

            session.temp_habit_data['periodicity'] = periodicity

            if session.temp_habit_data.get('is_pleasant'):
                session.state = 'awaiting_is_public'
                question = """🌍 **Сделать привычку публичной?**

Публичные привычки видны другим пользователям.

_Ответьте Да или Нет_"""
            else:
                session.state = 'awaiting_reward'
                question = """🎁 **Чем себя вознаградить после выполнения?**

_Опишите вознаграждение или напишите "нет" если не нужно_

Например: "Съесть шоколадку", "Посмотреть сериал", "нет" """

            session.save()
            self.send_message(chat_id, question)

        except ValueError:
            self.send_message(chat_id, "❌ Введите число от 1 до 7")

    def handle_awaiting_reward(self, chat_id, text, session):
        """Обработка вознаграждения"""
        if text.lower() not in ['нет', 'no', 'n', 'н']:
            session.temp_habit_data['reward'] = text

        session.state = 'awaiting_is_public'
        session.save()

        question = """🌍 **Сделать привычку публичной?**

Публичные привычки видны другим пользователям.

_Ответьте Да или Нет_"""

        self.send_message(chat_id, question)

    def handle_awaiting_is_public(self, chat_id, text, session, user):
        """Обработка публичности и создание привычки"""
        text_lower = text.lower()
        if text_lower in ['да', 'yes', 'y', 'д']:
            is_public = True
        elif text_lower in ['нет', 'no', 'n', 'н']:
            is_public = False
        else:
            self.send_message(chat_id, "❌ Пожалуйста, ответьте Да или Нет")
            return

        try:
            habit_data = session.temp_habit_data

            time_parts = list(map(int, habit_data['time'].split(':')))
            habit_time = dt_time(time_parts[0], time_parts[1], time_parts[2])
            Habit.objects.create(
                user=user,
                place=habit_data['place'],
                time=habit_time,
                action=habit_data['action'],
                is_pleasant=habit_data.get('is_pleasant', False),
                periodicity=habit_data.get('periodicity', 1),
                reward=habit_data.get('reward', ''),
                duration=habit_data['duration'],
                is_public=is_public
            )

            result_text = f"""✅ **Привычка создана успешно!** 🎉

📋 **Детали привычки:**
🏃 Действие: {habit_data['action']}
📍 Место: {habit_data['place']}
⏰ Время: {habit_data['time'][:5]} (МСК)
⏱️ Длительность: {habit_data['duration']} сек.
🔄 Периодичность: {self.get_periodicity_text(habit_data.get('periodicity', 1))}
😊 Тип: {'Приятная привычка' if habit_data.get('is_pleasant') else 'Полезная привычка'}
🎁 Вознаграждение: {habit_data.get('reward', 'Не указано')}
🌍 Видимость: {'Публичная' if is_public else 'Приватная'}

🔔 Теперь вы будете получать напоминания в указанное время!

Используйте /start чтобы создать еще одну привычку."""

            session.state = 'start'
            session.temp_habit_data = {}
            session.save()

            self.send_message(chat_id, result_text)
            self.stdout.write(f'✅ Создана привычка для {user.username}: {habit_data["action"]}')

        except Exception as e:
            self.send_message(chat_id, f"❌ Ошибка при создании привычки: {str(e)}")
            self.stdout.write(f'❌ Ошибка создания привычки: {e}')

    def get_periodicity_text(self, periodicity):
        """Текст для периодичности"""
        periods = {
            1: 'Ежедневно',
            2: 'Раз в 2 дня',
            3: 'Раз в 3 дня',
            4: 'Раз в 4 дня',
            5: 'Раз в 5 дней',
            6: 'Раз в 6 дней',
            7: 'Еженедельно'
        }
        return periods.get(periodicity, 'Ежедневно')

    def process_callback(self, callback_query):
        """Обработка callback-запросов (для кнопок)"""
        pass

    def send_message(self, chat_id, text):
        """Отправка сообщения"""
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                self.stdout.write(f'✅ Message sent to {chat_id}')
            else:
                self.stdout.write(f'⚠️ Send error: {response.status_code}')
        except Exception as e:
            self.stdout.write(f'❌ Send failed: {e}')
