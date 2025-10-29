import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from users.models import User
from config.settings import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    try:
        data = json.loads(request.body)
        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '').strip()
        username = message.get('from', {}).get('username', '')
        first_name = message.get('from', {}).get('first_name', '')

        if not chat_id:
            return JsonResponse({'status': 'error', 'message': 'No chat id'})

        if text == '/start':
            user = None
            if username:
                try:
                    user = User.objects.get(telegram_username=username)
                    user.telegram_chat_id = chat_id
                    user.save()

                    response_text = (
                        f"👋 Привет, {first_name}!\n\n"
                        f"✅ Ваш аккаунт успешно привязан!\n"
                        f"📝 Username: @{username}\n"
                        f"🔔 Теперь вы будете получать напоминания о привычках!\n\n"
                        "Создавайте привычки в системе и я буду напоминать вам о них! ⏰"
                    )

                except User.DoesNotExist:
                    response_text = (
                        f"👋 Привет, {first_name}!\n\n"
                        f"❌ Пользователь @{username} не найден в системе.\n\n"
                        "Чтобы получать напоминания:\n"
                        "1. Зарегистрируйтесь на нашем сайте\n"
                        "2. В личном кабинете укажите ваш Telegram: @{}\n"
                        "3. Вернитесь и отправьте /start снова\n\n"
                        "Или обратитесь к администратору для привязки аккаунта."
                    ).format(username)
            else:
                response_text = (
                    "👋 Привет!\n\n"
                    "❌ У вас не установлен username в Telegram.\n\n"
                    "Пожалуйста, установите username в настройках Telegram "
                    "и укажите его в вашем профиле на нашем сайте."
                )

        elif text == '/help':
            response_text = (
                "ℹ️ **Справка по командам:**\n\n"
                "/start - привязать аккаунт\n"
                "/help - показать эту справку\n\n"
                "💡 **Как это работает:**\n"
                "1. Укажите ваш @username в профиле на сайте\n"
                "2. Отправьте /start боту\n"
                "3. Создавайте привычки с указанием времени\n"
                "4. Получайте напоминания автоматически! ⏰"
            )

        else:
            response_text = (
                "❌ Неизвестная команда.\n"
                "Используйте /help для просмотра доступных команд."
            )

        send_telegram_message(chat_id, response_text)
        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)})


def send_telegram_message(chat_id, text):
    import requests
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, data=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return None
