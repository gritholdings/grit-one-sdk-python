from django.utils import timezone
from datetime import timedelta


def get_cooldown_remaining_seconds(last_sent_timestamp, cooldown_seconds=300):
    """
    Calculate remaining cooldown time in seconds.

    Args:
        last_sent_timestamp: DateTimeField timestamp of last action
        cooldown_seconds: Cooldown period in seconds (default: 300 seconds/5 minutes)

    Returns:
        int: Remaining seconds until cooldown expires, 0 if expired or no timestamp
    """
    if not last_sent_timestamp:
        return 0

    cooldown_period = timedelta(seconds=cooldown_seconds)
    time_elapsed = timezone.now() - last_sent_timestamp

    if time_elapsed < cooldown_period:
        remaining_time = (cooldown_period - time_elapsed).total_seconds()
        return max(0, int(remaining_time))

    return 0


def format_remaining_time(seconds):
    """
    Format remaining seconds into human-readable string.

    Args:
        seconds: Number of seconds remaining

    Returns:
        str: Formatted string like "4 minutes and 32 seconds"
    """
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
    """
    Check if cooldown period is still active.

    Args:
        last_sent_timestamp: DateTimeField timestamp of last action
        cooldown_seconds: Cooldown period in seconds (default: 300 seconds/5 minutes)

    Returns:
        bool: True if cooldown is active, False otherwise
    """
    return get_cooldown_remaining_seconds(last_sent_timestamp, cooldown_seconds) > 0