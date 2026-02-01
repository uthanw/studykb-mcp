"""Progress tracking service."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import aiofiles
import aiofiles.os

from ..config import settings
from ..models.progress import ProgressEntry, ProgressFile, ProgressStatus
from .review_service import ReviewService

# 全局锁字典，按 category 隔离，确保同一 category 的写操作串行化
_category_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class ProgressService:
    """Service for managing learning progress."""

    def __init__(self, progress_path: Path | None = None) -> None:
        self.progress_path = progress_path or settings.progress_path
        self.review_service = ReviewService()

    async def get_progress(
        self,
        category: str,
        status_filter: list[ProgressStatus] | None = None,
        since: Literal["7d", "30d", "90d", "all"] = "all",
        limit: int = 20,
    ) -> ProgressFile:
        """Get progress data for a category.

        This method automatically checks and triggers done -> review transitions.

        Args:
            category: Category name
            status_filter: Optional list of statuses to filter by
            since: Time range filter based on updated_at
            limit: Maximum entries per status group (-1 for all)

        Returns:
            ProgressFile with filtered entries
        """
        progress_file = await self._load_progress_file(category)

        # Auto-check and update done -> review transitions
        updated = self._check_review_triggers(progress_file)
        if updated:
            await self._save_progress_file(category, progress_file)

        # Apply filters
        filtered_entries = self._filter_entries(
            progress_file.entries, status_filter, since, limit
        )

        return ProgressFile(
            category=category,
            last_updated=progress_file.last_updated,
            entries=filtered_entries,
        )

    async def get_full_progress(self, category: str) -> ProgressFile:
        """Get full progress data for a category without filtering.

        Args:
            category: Category name

        Returns:
            ProgressFile with all entries
        """
        return await self._load_progress_file(category)

    async def update_progress(
        self,
        category: str,
        progress_id: str,
        status: ProgressStatus,
        name: str | None = None,
        comment: str = "",
    ) -> tuple[ProgressEntry, bool, ProgressStatus | None]:
        """Create or update a progress entry.

        Uses per-category locking to prevent concurrent write conflicts
        when batch_call executes multiple updates in parallel.

        Args:
            category: Category name
            progress_id: Progress ID (dot-separated, e.g., "ds.graph.mst.kruskal")
            status: New status
            name: Knowledge point name (required for new entries)
            comment: Comment/notes

        Returns:
            Tuple of (entry, is_new, old_status)

        Raises:
            ValueError: If name is not provided for new entries
        """
        # 使用 category 级别的锁，确保同一 category 的写操作串行化
        async with _category_locks[category]:
            progress_file = await self._load_progress_file(category)

            is_new = progress_id not in progress_file.entries
            now = datetime.now()
            old_status: ProgressStatus | None = None

            if is_new:
                if not name:
                    raise ValueError("name is required for new progress entry")
                entry = ProgressEntry(
                    name=name,
                    status=status,
                    comment=comment,
                    updated_at=now,
                    mastered_at=now if status == "done" else None,
                    review_count=0,
                    next_review_at=(
                        self.review_service.calculate_next_review(now, 0)
                        if status == "done"
                        else None
                    ),
                )
            else:
                existing = progress_file.entries[progress_id]
                old_status = existing.status

                entry = ProgressEntry(
                    name=name or existing.name,
                    status=status,
                    comment=comment,
                    updated_at=now,
                    mastered_at=self._update_mastered_at(existing, old_status, status, now),
                    review_count=self._update_review_count(existing, old_status, status),
                    next_review_at=self._update_next_review(existing, old_status, status, now),
                )

            progress_file.entries[progress_id] = entry
            progress_file.last_updated = now

            await self._save_progress_file(category, progress_file)

            return entry, is_new, old_status

    def _update_mastered_at(
        self,
        existing: ProgressEntry,
        old_status: ProgressStatus,
        new_status: ProgressStatus,
        now: datetime,
    ) -> datetime | None:
        """Update mastered_at field based on status change."""
        if new_status == "done" and old_status != "done":
            return now
        return existing.mastered_at

    def _update_review_count(
        self,
        existing: ProgressEntry,
        old_status: ProgressStatus,
        new_status: ProgressStatus,
    ) -> int:
        """Update review count based on status change."""
        # review -> done counts as a successful review
        if old_status == "review" and new_status == "done":
            return existing.review_count + 1
        return existing.review_count

    def _update_next_review(
        self,
        existing: ProgressEntry,
        old_status: ProgressStatus,
        new_status: ProgressStatus,
        now: datetime,
    ) -> datetime | None:
        """Update next_review_at based on status change."""
        if new_status != "done":
            return None

        review_count = existing.review_count
        if old_status == "review":
            review_count += 1

        return self.review_service.calculate_next_review(now, review_count)

    def _check_review_triggers(self, progress_file: ProgressFile) -> bool:
        """Check and trigger done -> review transitions.

        Args:
            progress_file: Progress file to check

        Returns:
            True if any entries were updated
        """
        now = datetime.now()
        updated = False

        for entry in progress_file.entries.values():
            if entry.status == "done" and entry.next_review_at:
                if now >= entry.next_review_at:
                    entry.status = "review"
                    entry.updated_at = now
                    updated = True

        return updated

    def _filter_entries(
        self,
        entries: dict[str, ProgressEntry],
        status_filter: list[ProgressStatus] | None,
        since: str,
        limit: int,
    ) -> dict[str, ProgressEntry]:
        """Apply filters to progress entries.

        Args:
            entries: All entries
            status_filter: Optional status filter
            since: Time range filter
            limit: Maximum entries per status group

        Returns:
            Filtered entries
        """
        result: dict[str, ProgressEntry] = {}

        # Parse time filter
        since_time = self._parse_since(since)

        # Group by status
        by_status: dict[str, list[tuple[str, ProgressEntry]]] = {
            "active": [],
            "review": [],
            "done": [],
            "pending": [],
        }

        for entry_id, entry in entries.items():
            if since_time and entry.updated_at < since_time:
                continue
            if status_filter and entry.status not in status_filter:
                continue
            by_status[entry.status].append((entry_id, entry))

        # Sort by updated_at (descending) and apply limit
        for status in by_status:
            by_status[status].sort(key=lambda x: x[1].updated_at, reverse=True)

            entries_to_include = by_status[status]
            if limit > 0:
                entries_to_include = entries_to_include[:limit]

            for entry_id, entry in entries_to_include:
                result[entry_id] = entry

        return result

    def _parse_since(self, since: str) -> datetime | None:
        """Parse the 'since' parameter into a datetime.

        Args:
            since: Time range string ("7d", "30d", "90d", "all")

        Returns:
            Datetime threshold, or None for "all"
        """
        if since == "all":
            return None

        days = {"7d": 7, "30d": 30, "90d": 90}.get(since, 0)
        if days:
            return datetime.now() - timedelta(days=days)
        return None

    async def _load_progress_file(self, category: str) -> ProgressFile:
        """Load progress file for a category.

        Args:
            category: Category name

        Returns:
            ProgressFile (empty if file doesn't exist)
        """
        file_path = self.progress_path / f"{category}.json"

        if not await aiofiles.os.path.exists(file_path):
            return ProgressFile(
                category=category,
                last_updated=datetime.now(),
                entries={},
            )

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())

        return ProgressFile.model_validate(data)

    async def delete_progress(
        self, category: str, progress_id: str
    ) -> ProgressEntry | None:
        """Delete a progress entry.

        Uses per-category locking to prevent concurrent write conflicts.

        Args:
            category: Category name
            progress_id: Progress ID to delete

        Returns:
            The deleted entry, or None if not found
        """
        async with _category_locks[category]:
            progress_file = await self._load_progress_file(category)

            if progress_id not in progress_file.entries:
                return None

            deleted_entry = progress_file.entries.pop(progress_id)
            progress_file.last_updated = datetime.now()

            await self._save_progress_file(category, progress_file)

            return deleted_entry

    async def _save_progress_file(self, category: str, progress: ProgressFile) -> None:
        """Save progress file for a category.

        Args:
            category: Category name
            progress: Progress data to save
        """
        # Ensure directory exists
        await aiofiles.os.makedirs(self.progress_path, exist_ok=True)

        file_path = self.progress_path / f"{category}.json"

        # Write atomically using a temporary file
        temp_path = file_path.with_suffix(".tmp")
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(progress.model_dump_json(indent=2))

        # Atomic replace
        await aiofiles.os.replace(temp_path, file_path)

    async def category_has_progress(self, category: str) -> bool:
        """Check if a category has a progress file.

        Args:
            category: Category name

        Returns:
            True if progress file exists
        """
        return await aiofiles.os.path.exists(self.progress_path / f"{category}.json")
