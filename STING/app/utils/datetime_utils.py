"""
Timezone-aware datetime utilities for STING platform.

All timestamps should be stored in UTC and converted to user's local time on the frontend.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC time with timezone awareness.

    Use this instead of datetime.now() to ensure all timestamps are UTC.

    Returns:
        datetime: Current time in UTC with timezone info

    Example:
        >>> from app.utils.datetime_utils import utc_now
        >>> timestamp = utc_now()
        >>> print(timestamp.isoformat())
        '2025-11-25T04:30:00+00:00'
    """
    return datetime.now(timezone.utc)


def utc_from_timestamp(timestamp: float) -> datetime:
    """
    Convert Unix timestamp to UTC datetime.

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        datetime: UTC datetime with timezone info
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """
    Convert any datetime to UTC.

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        datetime: UTC datetime with timezone info
    """
    if dt.tzinfo is None:
        # Assume naive datetime is already UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_iso_utc(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO 8601 UTC string.

    Args:
        dt: Datetime to format (defaults to current UTC time)

    Returns:
        str: ISO 8601 formatted string with 'Z' suffix

    Example:
        >>> format_iso_utc()
        '2025-11-25T04:30:00Z'
    """
    if dt is None:
        dt = utc_now()
    else:
        dt = to_utc(dt)

    # Use 'Z' suffix for UTC (RFC 3339 format)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_iso_utc(iso_string: str) -> datetime:
    """
    Parse ISO 8601 UTC string to datetime.

    Args:
        iso_string: ISO 8601 formatted string

    Returns:
        datetime: UTC datetime with timezone info
    """
    # Handle both 'Z' suffix and '+00:00' offset
    if iso_string.endswith('Z'):
        iso_string = iso_string[:-1] + '+00:00'

    return datetime.fromisoformat(iso_string).astimezone(timezone.utc)


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time difference from now.

    Args:
        dt: Datetime to compare

    Returns:
        str: Human-readable time difference

    Example:
        >>> time_ago(utc_now() - timedelta(minutes=5))
        '5 minutes ago'
    """
    now = utc_now()
    dt = to_utc(dt)
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)} minutes ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 2592000:  # 30 days
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 31536000:  # 365 days
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"
