from django.contrib import admin
from .models import UserSession


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'state', 'created_at', 'updated_at')
    list_filter = ('state', 'created_at')
    search_fields = ('user__username', 'user__telegram_username')
    readonly_fields = ('created_at', 'updated_at')
