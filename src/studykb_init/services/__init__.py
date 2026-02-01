"""Progress tracking service for studykb_init.

This is a simplified version that only handles progress file operations
without depending on the MCP server modules.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from studykb_init.config import load_config


ProgressStatus = Literal["active", "done", "review", "pending"]


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
    ) -> tuple[dict, bool]:
        """Create or update a progress entry.

        Args:
            category: Category name
            progress_id: Progress ID (dot-separated)
            status: New status
            name: Knowledge point name (required for new entries)
            comment: Comment/notes

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
