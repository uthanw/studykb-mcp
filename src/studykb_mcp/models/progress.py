"""Progress tracking data models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Progress status type
ProgressStatus = Literal["active", "done", "review", "pending"]


class RelatedSection(BaseModel):
    """A related section in a material file."""

    material: str  # 文件名 (含 .md 后缀)
    start_line: int  # 起始行
    end_line: int  # 结束行
    desc: str = ""  # 片段描述，如"教材正文"、"习题"等


class ProgressEntry(BaseModel):
    """A single progress entry for a knowledge point."""

    name: str
    status: ProgressStatus
    comment: str = ""
    updated_at: datetime
    mastered_at: datetime | None = None
    review_count: int = 0
    next_review_at: datetime | None = None
    related_sections: list[RelatedSection] = Field(default_factory=list)


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
