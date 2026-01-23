"""Tests for ProgressService."""

from datetime import datetime, timedelta

import pytest

from studykb_mcp.services.progress_service import ProgressService


class TestProgressService:
    """Tests for ProgressService."""

    @pytest.mark.asyncio
    async def test_get_progress(self, sample_progress):
        """Test getting progress data."""
        service = ProgressService(progress_path=sample_progress)
        progress = await service.get_progress(category="数据结构")

        assert progress.category == "数据结构"
        assert len(progress.entries) >= 1

    @pytest.mark.asyncio
    async def test_get_progress_empty_category(self, empty_progress):
        """Test getting progress for a category with no data."""
        service = ProgressService(progress_path=empty_progress)
        progress = await service.get_progress(category="数据结构")

        assert progress.category == "数据结构"
        assert len(progress.entries) == 0

    @pytest.mark.asyncio
    async def test_get_progress_with_status_filter(self, sample_progress):
        """Test filtering progress by status."""
        service = ProgressService(progress_path=sample_progress)
        progress = await service.get_progress(
            category="数据结构",
            status_filter=["active"],
        )

        for entry in progress.entries.values():
            assert entry.status == "active"

    @pytest.mark.asyncio
    async def test_get_progress_with_time_filter(self, sample_progress):
        """Test filtering progress by time."""
        service = ProgressService(progress_path=sample_progress)
        progress = await service.get_progress(
            category="数据结构",
            since="7d",
        )

        now = datetime.now()
        cutoff = now - timedelta(days=7)
        for entry in progress.entries.values():
            assert entry.updated_at >= cutoff

    @pytest.mark.asyncio
    async def test_auto_review_trigger(self, sample_progress):
        """Test automatic done -> review transition."""
        service = ProgressService(progress_path=sample_progress)

        # Get progress (this should trigger review check)
        progress = await service.get_progress(category="数据结构")

        # The entry with overdue next_review_at should now be "review"
        ds_array = progress.entries.get("ds.linear.array")
        if ds_array:
            # This was done with overdue review, should now be review
            assert ds_array.status == "review"

    @pytest.mark.asyncio
    async def test_update_progress_create_new(self, empty_progress):
        """Test creating a new progress entry."""
        service = ProgressService(progress_path=empty_progress)

        entry, is_new, old_status = await service.update_progress(
            category="数据结构",
            progress_id="ds.test.new",
            status="active",
            name="新知识点",
            comment="开始学习",
        )

        assert is_new is True
        assert old_status is None
        assert entry.name == "新知识点"
        assert entry.status == "active"

    @pytest.mark.asyncio
    async def test_update_progress_require_name_for_new(self, empty_progress):
        """Test that name is required for new entries."""
        service = ProgressService(progress_path=empty_progress)

        with pytest.raises(ValueError, match="name is required"):
            await service.update_progress(
                category="数据结构",
                progress_id="ds.test.new",
                status="active",
                comment="开始学习",
            )

    @pytest.mark.asyncio
    async def test_update_progress_update_existing(self, sample_progress):
        """Test updating an existing progress entry."""
        service = ProgressService(progress_path=sample_progress)

        entry, is_new, old_status = await service.update_progress(
            category="数据结构",
            progress_id="ds.linear.linked_list",
            status="done",
            comment="链表已掌握",
        )

        assert is_new is False
        assert old_status == "active"
        assert entry.status == "done"
        assert entry.next_review_at is not None

    @pytest.mark.asyncio
    async def test_update_progress_review_to_done_increments_count(self, sample_progress):
        """Test that review -> done increments review_count."""
        service = ProgressService(progress_path=sample_progress)

        # First get the current state
        progress = await service.get_progress(category="数据结构")
        # ds.linear.array should be "review" after auto-trigger
        old_entry = progress.entries.get("ds.linear.array")
        if old_entry:
            old_count = old_entry.review_count

            # Update to done
            entry, _, _ = await service.update_progress(
                category="数据结构",
                progress_id="ds.linear.array",
                status="done",
                comment="复习完成",
            )

            assert entry.review_count == old_count + 1

    @pytest.mark.asyncio
    async def test_update_progress_done_sets_review_time(self, empty_progress):
        """Test that setting status to done sets next_review_at."""
        service = ProgressService(progress_path=empty_progress)

        entry, _, _ = await service.update_progress(
            category="数据结构",
            progress_id="ds.test.new",
            status="done",
            name="测试知识点",
            comment="已掌握",
        )

        assert entry.next_review_at is not None
        assert entry.mastered_at is not None
        # Default interval is 7 days
        assert (entry.next_review_at - datetime.now()).days >= 6

    @pytest.mark.asyncio
    async def test_progress_stats(self, sample_progress):
        """Test progress statistics."""
        service = ProgressService(progress_path=sample_progress)
        progress = await service.get_full_progress(category="数据结构")

        stats = progress.get_stats()
        assert "active" in stats
        assert "done" in stats
        assert "review" in stats
        assert "pending" in stats
        assert "total" in stats
        assert stats["total"] == sum(
            stats[s] for s in ["active", "done", "review", "pending"]
        )
