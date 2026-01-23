"""Ebbinghaus spaced repetition review algorithm service."""

from datetime import datetime, timedelta

from ..config import settings


class ReviewService:
    """Service for calculating review schedules based on Ebbinghaus forgetting curve."""

    def __init__(self) -> None:
        self.initial_interval = settings.review_initial_interval
        self.multiplier = settings.review_multiplier
        self.max_interval = settings.review_max_interval

    def calculate_next_review(self, from_date: datetime, review_count: int) -> datetime:
        """Calculate the next review date.

        Formula: interval = initial_interval * (multiplier ^ review_count)
        Capped at max_interval.

        Args:
            from_date: The date to calculate from (usually now or mastered_at)
            review_count: Number of successful reviews completed

        Returns:
            The next review date (at 00:00:00)
        """
        interval_days = self.initial_interval * (self.multiplier**review_count)
        interval_days = min(interval_days, self.max_interval)

        next_date = from_date + timedelta(days=interval_days)
        return next_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_overdue_days(self, next_review_at: datetime) -> int:
        """Calculate how many days overdue a review is.

        Args:
            next_review_at: The scheduled review date

        Returns:
            Number of days overdue (0 if not yet due)
        """
        now = datetime.now()
        if now < next_review_at:
            return 0
        return (now - next_review_at).days

    def is_review_due(self, next_review_at: datetime | None) -> bool:
        """Check if a review is due.

        Args:
            next_review_at: The scheduled review date, or None if not scheduled

        Returns:
            True if review is due, False otherwise
        """
        if next_review_at is None:
            return False
        return datetime.now() >= next_review_at

    def format_interval(self, review_count: int) -> str:
        """Format the review interval for display.

        Args:
            review_count: Number of successful reviews completed

        Returns:
            Formatted interval string (e.g., "7d", "10d", "90d")
        """
        interval_days = self.initial_interval * (self.multiplier**review_count)
        interval_days = min(interval_days, self.max_interval)
        return f"{int(interval_days)}d"
