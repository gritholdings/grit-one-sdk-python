from django.utils import timezone
from datetime import timedelta


def get_cooldown_remaining_seconds(last_sent_timestamp, cooldown_seconds=300):
    if not last_sent_timestamp:
        return 0
    cooldown_period = timedelta(seconds=cooldown_seconds)
    time_elapsed = timezone.now() - last_sent_timestamp
    if time_elapsed < cooldown_period:
        remaining_time = (cooldown_period - time_elapsed).total_seconds()
        return max(0, int(remaining_time))
    return 0


def format_remaining_time(seconds):
    if seconds <= 0:
        return "0 seconds"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    parts = []
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if remaining_seconds > 0:
        parts.append(f"{remaining_seconds} second{'s' if remaining_seconds != 1 else ''}")
    return " and ".join(parts)


def is_cooldown_active(last_sent_timestamp, cooldown_seconds=300):
    return get_cooldown_remaining_seconds(last_sent_timestamp, cooldown_seconds) > 0