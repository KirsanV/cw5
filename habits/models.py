from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Habit(models.Model):
    PERIODICITY_CHOICES = [
        (1, 'Ежедневно'),
        (2, 'Раз в 2 дня'),
        (3, 'Раз в 3 дня'),
        (4, 'Раз в 4 дня'),
        (5, 'Раз в 5 дней'),
        (6, 'Раз в 6 дней'),
        (7, 'Еженедельно'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    place = models.CharField(max_length=255, verbose_name='Место')
    time = models.TimeField(verbose_name='Время')
    action = models.CharField(max_length=255, verbose_name='Действие')
    is_pleasant = models.BooleanField(default=False, verbose_name='Признак приятной привычки')
    related_habit = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Связанная привычка'
    )
    periodicity = models.PositiveSmallIntegerField(
        choices=PERIODICITY_CHOICES,
        default=1,
        verbose_name='Периодичность'
    )
    reward = models.CharField(max_length=255, blank=True, verbose_name='Вознаграждение')
    duration = models.PositiveSmallIntegerField(
        verbose_name='Время на выполнение (в секундах)',
        help_text='Время в секундах'
    )
    is_public = models.BooleanField(default=False, verbose_name='Признак публичности')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Привычка'
        verbose_name_plural = 'Привычки'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user}: {self.action} в {self.time}"

    def clean(self):
        if self.related_habit and self.reward:
            raise ValidationError('Нельзя указывать одновременно связанную привычку и вознаграждение')
        if self.duration > 120:
            raise ValidationError('Время выполнения не должно превышать 120 секунд')
        if self.related_habit and not self.related_habit.is_pleasant:
            raise ValidationError('В связанные привычки могут попадать только приятные привычки')
        if self.is_pleasant and (self.reward or self.related_habit):
            raise ValidationError('У приятной привычки не может быть вознаграждения или связанной привычки')
        if self.periodicity > 7:
            raise ValidationError('Нельзя выполнять привычку реже, чем 1 раз в 7 дней')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
