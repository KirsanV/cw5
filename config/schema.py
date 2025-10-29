from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Habits Tracker API",
        default_version='v1',
        description="""
        # 🎯 Habits Tracker API

        ## Описание
        API для отслеживания привычек с интеграцией Telegram бота.

        ## Основные возможности:
        - 📝 Управление привычками (создание, редактирование, удаление)
        - 👥 Публичные привычки для мотивации
        - 🔔 Напоминания через Telegram
        - 🔐 JWT аутентификация

        ## Авторизация
        Используйте JWT токен в заголовке:
        `Authorization: Bearer <your_token>`

        ## Эндпоинты
        - `/api/users/` - управление пользователями
        - `/api/habits/` - управление привычками
        - `/api/habits/public/` - публичные привычки
        - `/api/token/` - получение JWT токена

        [GitHub Repository](https://github.com/KirsanV/cw5)
        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="lalala@google.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
