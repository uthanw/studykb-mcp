"""Tests for ReviewService."""

from datetime import datetime, timedelta

import pytest

from studykb_mcp.services.review_service import ReviewService


class TestReviewService:
    """Tests for ReviewService."""

    def test_calculate_next_review_first_time(self):
        """Test calculating first review date."""
        service = ReviewService()
        now = datetime(2025, 1, 20, 14, 30, 0)

        next_review = service.calculate_next_review(now, review_count=0)

        # First review should be 7 days later
        expected = datetime(2025, 1, 27, 0, 0, 0)
        assert next_review == expected

    def test_calculate_next_review_with_multiplier(self):
        """Test calculating review date with multiplier."""
        service = ReviewService()
        now = datetime(2025, 1, 20, 14, 30, 0)

        # After first review: 7 * 1.5 = 10.5 -> 10 days
        next_review = service.calculate_next_review(now, review_count=1)
        expected_days = int(7 * 1.5)
        assert (next_review - now).days == expected_days

        # After second review: 7 * 1.5^2 = 15.75 -> 15 days
        next_review = service.calculate_next_review(now, review_count=2)
        expected_days = int(7 * 1.5**2)
        assert (next_review - now).days == expected_days

    def test_calculate_next_review_max_interval(self):
        """Test that review interval is capped at max."""
        service = ReviewService()
        now = datetime(2025, 1, 20, 14, 30, 0)

        # After many reviews, should cap at 90 days
        next_review = service.calculate_next_review(now, review_count=10)
        # Note: result is set to 00:00:00, so days diff might be 89 not 90
        assert (next_review - now).days >= 89
        assert (next_review - now).days <= 90

    def test_get_overdue_days_not_due(self):
        """Test overdue days when not yet due."""
        service = ReviewService()
        future = datetime.now() + timedelta(days=5)

        overdue = service.get_overdue_days(future)
        assert overdue == 0

    def test_get_overdue_days_overdue(self):
        """Test overdue days when overdue."""
        service = ReviewService()
        past = datetime.now() - timedelta(days=10)

        overdue = service.get_overdue_days(past)
        assert overdue == 10

    def test_is_review_due_none(self):
        """Test is_review_due with None."""
        service = ReviewService()
        assert service.is_review_due(None) is False

    def test_is_review_due_future(self):
        """Test is_review_due with future date."""
        service = ReviewService()
        future = datetime.now() + timedelta(days=5)
        assert service.is_review_due(future) is False

    def test_is_review_due_past(self):
        """Test is_review_due with past date."""
        service = ReviewService()
        past = datetime.now() - timedelta(days=5)
        assert service.is_review_due(past) is True

    def test_format_interval(self):
        """Test formatting review interval."""
        service = ReviewService()

        assert service.format_interval(0) == "7d"
        assert service.format_interval(1) == "10d"  # 7 * 1.5 = 10.5 -> 10
        assert service.format_interval(2) == "15d"  # 7 * 1.5^2 = 15.75 -> 15

    def test_review_schedule_growth(self):
        """Test that review schedule grows exponentially then caps."""
        service = ReviewService()
        intervals = []

        for i in range(10):
            interval = service.format_interval(i)
            days = int(interval.replace("d", ""))
            intervals.append(days)

        # Should be growing
        for i in range(1, len(intervals) - 1):
            assert intervals[i] >= intervals[i - 1]

        # Last few should be capped at 90
        assert intervals[-1] == 90
