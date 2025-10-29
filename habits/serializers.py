from rest_framework import serializers
from .models import Habit


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = [
            'id', 'user', 'place', 'time', 'action', 'is_pleasant',
            'related_habit', 'periodicity', 'reward', 'duration',
            'is_public', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']

    def validate(self, data):
        related_habit = data.get('related_habit')
        reward = data.get('reward', '')
        is_pleasant = data.get('is_pleasant', False)

        if related_habit and reward:
            raise serializers.ValidationError(
                "Нельзя указывать одновременно связанную привычку и вознаграждение"
            )
        if is_pleasant and (related_habit or reward):
            raise serializers.ValidationError(
                "У приятной привычки не может быть связанной привычки или вознаграждения"
            )
        if related_habit and not related_habit.is_pleasant:
            raise serializers.ValidationError(
                "В связанные привычки могут попадать только приятные привычки"
            )
        if data.get('duration', 0) > 120:
            raise serializers.ValidationError(
                "Время выполнения не должно превышать 120 секунд"
            )
        if data.get('periodicity', 1) > 7:
            raise serializers.ValidationError(
                "Нельзя выполнять привычку реже, чем 1 раз в 7 дней"
            )

        return data
