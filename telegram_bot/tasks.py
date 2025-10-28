from celery import shared_task
import requests
from habits.models import Habit
from config.settings import TELEGRAM_BOT_TOKEN
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_telegram_reminder(habit_id):
    """Отправка напоминания о привычке через Telegram."""
    try:
        habit = Habit.objects.select_related('user').get(id=habit_id)
        user = habit.user

        if not user.telegram_chat_id:
            logger.warning("No telegram_chat_id for user %s", user.username)
            return False

        message = "🔔 **Напоминание о привычке!**\n\n"
        message += f"🏃 **Действие:** {habit.action}\n"
        message += f"📍 **Место:** {habit.place}\n"
        message += f"⏰ **Время:** {habit.time.strftime('%H:%M')}\n"
        message += f"⏱️ **Длительность:** {habit.duration} секунд\n"

        if habit.reward:
            message += f"🎁 **Вознаграждение:** {habit.reward}\n"
        elif habit.related_habit:
            message += f"😊 **Приятная привычка:** {habit.related_habit.action}\n"

        message += "\nУдачи! 💪"

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': user.telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }

        requests.post(url, data=data, timeout=10)
        logger.info("Reminder sent for habit %s", habit.id)
        return True

    except Habit.DoesNotExist:
        logger.error("Habit matching query does not exist.")
        return False
    except Exception as e:
        logger.error("Error sending reminder: %s", e)
        return False


@shared_task
def check_habits_for_reminders():
    """Проверка привычек для отправки напоминаний."""
    try:
        from django.utils import timezone
        import pytz

        moscow_tz = pytz.timezone('Europe/Moscow')
        now_moscow = timezone.now().astimezone(moscow_tz)
        current_time_moscow = now_moscow.time()

        logger.info("🔍 Checking habits at %s (Moscow time)", current_time_moscow)

        habits = Habit.objects.select_related('user').all()
        logger.info("📋 Total habits in database: %s", habits.count())

        habits_to_remind = []
        for habit in habits:
            habit_time = habit.time

            logger.info(
                "📝 Habit: '%s' at %s -> current: %s",
                habit.action, habit_time, current_time_moscow
            )

            if (habit_time.hour == current_time_moscow.hour
                    and habit_time.minute == current_time_moscow.minute):
                habits_to_remind.append(habit)
                logger.info("🎯 MATCH FOUND: '%s' at %s", habit.action, habit_time)

        logger.info("✅ Habits to remind: %s", len(habits_to_remind))

        for habit in habits_to_remind:
            if habit.user.telegram_chat_id:
                logger.info(
                    "📤 Sending reminder for: '%s' to %s",
                    habit.action, habit.user.username
                )
                send_telegram_reminder.delay(habit.id)

        return f"Checked {habits.count()} habits, found {len(habits_to_remind)} to remind"

    except Exception as e:
        logger.error("❌ Error in check_habits_for_reminders: %s", e)
        return f"Error: {e}"
