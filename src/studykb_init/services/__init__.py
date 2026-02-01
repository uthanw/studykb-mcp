"""Progress tracking service for studykb_init.

This is a simplified version that only handles progress file operations
without depending on the MCP server modules.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from studykb_init.config import load_config


ProgressStatus = Literal["active", "done", "review", "pending"]


@dataclass
class RelatedSection:
    """A related section in a material file."""

    material: str  # 文件名 (含 .md 后缀)
    start_line: int  # 起始行
    end_line: int  # 结束行
    desc: str = ""  # 片段描述

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "material": self.material,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "desc": self.desc,
        }


class ProgressService:
    """Service for managing learning progress."""

    def __init__(self, progress_path: Path | None = None) -> None:
        settings = load_config()
        self.progress_path = progress_path or settings.progress_path

    async def update_progress(
        self,
        category: str,
        progress_id: str,
        status: ProgressStatus,
        name: str | None = None,
        comment: str = "",
        related_sections: list[RelatedSection] | None = None,
    ) -> tuple[dict, bool]:
        """Create or update a progress entry.

        Args:
            category: Category name
            progress_id: Progress ID (dot-separated)
            status: New status
            name: Knowledge point name (required for new entries)
            comment: Comment/notes
            related_sections: List of related material sections

        Returns:
            Tuple of (entry, is_new)
        """
        progress_file = await self._load_progress_file(category)

        is_new = progress_id not in progress_file.get("entries", {})
        now = datetime.now().isoformat()

        if is_new:
            if not name:
                raise ValueError("name is required for new progress entry")
            entry = {
                "name": name,
                "status": status,
                "comment": comment,
                "updated_at": now,
                "mastered_at": None,
                "review_count": 0,
                "next_review_at": None,
                "related_sections": [s.to_dict() for s in related_sections] if related_sections else [],
            }
        else:
            existing = progress_file["entries"][progress_id]
            entry = {
                "name": name or existing.get("name"),
                "status": status,
                "comment": comment,
                "updated_at": now,
                "mastered_at": existing.get("mastered_at"),
                "review_count": existing.get("review_count", 0),
                "next_review_at": existing.get("next_review_at"),
                "related_sections": (
                    [s.to_dict() for s in related_sections]
                    if related_sections is not None
                    else existing.get("related_sections", [])
                ),
            }

        if "entries" not in progress_file:
            progress_file["entries"] = {}

        progress_file["entries"][progress_id] = entry
        progress_file["last_updated"] = now

        await self._save_progress_file(category, progress_file)

        return entry, is_new

    async def _load_progress_file(self, category: str) -> dict:
        """Load progress file for a category."""
        file_path = self.progress_path / f"{category}.json"

        if not file_path.exists():
            return {
                "category": category,
                "last_updated": datetime.now().isoformat(),
                "entries": {},
            }

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def _save_progress_file(self, category: str, progress: dict) -> None:
        """Save progress file for a category."""
        # Ensure directory exists
        self.progress_path.mkdir(parents=True, exist_ok=True)

        file_path = self.progress_path / f"{category}.json"

        # Write atomically using a temporary file
        temp_path = file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)

        # Atomic replace
        temp_path.replace(file_path)
