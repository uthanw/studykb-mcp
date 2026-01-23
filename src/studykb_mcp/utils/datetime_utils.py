"""Datetime utilities."""

from datetime import datetime


def format_relative_time(dt: datetime) -> str:
    """Format a datetime as a relative time string.

    Args:
        dt: The datetime to format

    Returns:
        Relative time string (e.g., "2h ago", "3d ago", "Jan 19")
    """
    now = datetime.now()
    diff = now - dt

    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            minutes = diff.seconds // 60
            if minutes == 0:
                return "just now"
            return f"{minutes}m ago"
        return f"{hours}h ago"
    elif diff.days == 1:
        return "yesterday"
    elif diff.days < 7:
        return f"{diff.days}d ago"
    else:
        return dt.strftime("%b %d")


def format_date_short(dt: datetime) -> str:
    """Format a datetime as a short date.

    Args:
        dt: The datetime to format

    Returns:
        Short date string (e.g., "Jan 19")
    """
    return dt.strftime("%b %d")


def format_overdue(days: int) -> str:
    """Format overdue days for display.

    Args:
        days: Number of days overdue

    Returns:
        Formatted string (e.g., "+14d overdue")
    """
    if days <= 0:
        return ""
    return f"+{days}d overdue"
