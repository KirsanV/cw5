from rest_framework import serializers


def validate_duration(value):
    """Валидатор времени выполнения привычки"""
    if value > 120:
        raise serializers.ValidationError(
            "Время выполнения не должно превышать 120 секунд"
        )
    return value


def validate_periodicity(value):
    """Валидатор периодичности выполнения"""
    if value > 7:
        raise serializers.ValidationError(
            "Нельзя выполнять привычку реже, чем 1 раз в 7 дней"
        )
    return value
