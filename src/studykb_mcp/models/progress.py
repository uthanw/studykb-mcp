"""Progress tracking data models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Progress status type
ProgressStatus = Literal["active", "done", "review", "pending"]


class ProgressEntry(BaseModel):
    """A single progress entry for a knowledge point."""

    name: str
    status: ProgressStatus
    comment: str = ""
    updated_at: datetime
    mastered_at: datetime | None = None
    review_count: int = 0
    next_review_at: datetime | None = None


class ProgressFile(BaseModel):
    """Progress file structure for a category."""

    category: str
    last_updated: datetime
    entries: dict[str, ProgressEntry] = Field(default_factory=dict)

    def get_stats(self) -> dict[str, int]:
        """Get statistics for this progress file."""
        stats: dict[str, int] = {
            "active": 0,
            "done": 0,
            "review": 0,
            "pending": 0,
            "total": 0,
        }
        for entry in self.entries.values():
            stats[entry.status] += 1
            stats["total"] += 1
        return stats
