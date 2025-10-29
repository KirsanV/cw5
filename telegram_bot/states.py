from enum import Enum


class UserState(Enum):
    START = "start"
    AWAITING_ACTION = "awaiting_action"
    AWAITING_PLACE = "awaiting_place"
    AWAITING_TIME = "awaiting_time"
    AWAITING_DURATION = "awaiting_duration"
    AWAITING_IS_PLEASANT = "awaiting_is_pleasant"
    AWAITING_PERIODICITY = "awaiting_periodicity"
    AWAITING_REWARD = "awaiting_reward"
    AWAITING_IS_PUBLIC = "awaiting_is_public"
    CONFIRMING_HABIT = "confirming_habit"
