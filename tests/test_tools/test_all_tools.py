"""Tests for MCP Tools."""

import pytest

from studykb_mcp.tools.grep import grep_handler
from studykb_mcp.tools.read_file import read_file_handler
from studykb_mcp.tools.read_index import read_index_handler
from studykb_mcp.tools.read_overview import read_overview_handler
from studykb_mcp.tools.read_progress import read_progress_handler
from studykb_mcp.tools.update_progress import update_progress_handler


class TestReadOverview:
    """Tests for read_overview tool."""

    @pytest.mark.asyncio
    async def test_read_overview(self, sample_kb, monkeypatch):
        """Test read_overview returns formatted overview."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await read_overview_handler({})

        assert "Knowledge Base Overview" in result
        assert "数据结构" in result
        assert "计算机组成原理" in result
        assert "[IDX]" in result  # Should show index indicator

    @pytest.mark.asyncio
    async def test_read_overview_empty(self, empty_kb, monkeypatch):
        """Test read_overview with empty KB."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", empty_kb)

        result = await read_overview_handler({})

        assert "Knowledge Base Overview" in result
        assert "No categories found" in result


class TestReadProgress:
    """Tests for read_progress tool."""

    @pytest.mark.asyncio
    async def test_read_progress(self, sample_progress, monkeypatch):
        """Test read_progress returns formatted progress."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "progress_path", sample_progress)

        result = await read_progress_handler({"category": "数据结构"})

        assert "Progress: 数据结构" in result
        assert "done:" in result
        assert "active:" in result

    @pytest.mark.asyncio
    async def test_read_progress_with_filter(self, sample_progress, monkeypatch):
        """Test read_progress with status filter."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "progress_path", sample_progress)

        result = await read_progress_handler({
            "category": "数据结构",
            "status_filter": ["active"],
        })

        assert "filter: active" in result


class TestUpdateProgress:
    """Tests for update_progress tool."""

    @pytest.mark.asyncio
    async def test_update_progress_new(self, empty_progress, monkeypatch):
        """Test creating new progress entry."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "progress_path", empty_progress)

        result = await update_progress_handler({
            "category": "数据结构",
            "progress_id": "ds.test.new",
            "status": "active",
            "name": "新知识点",
            "comment": "开始学习",
        })

        assert "Progress created" in result
        assert "ds.test.new" in result
        assert "新知识点" in result

    @pytest.mark.asyncio
    async def test_update_progress_existing(self, sample_progress, monkeypatch):
        """Test updating existing progress entry."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "progress_path", sample_progress)

        result = await update_progress_handler({
            "category": "数据结构",
            "progress_id": "ds.linear.linked_list",
            "status": "done",
            "comment": "已掌握",
        })

        assert "Progress updated" in result
        assert "active → done" in result

    @pytest.mark.asyncio
    async def test_update_progress_missing_name(self, empty_progress, monkeypatch):
        """Test error when name is missing for new entry."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "progress_path", empty_progress)

        result = await update_progress_handler({
            "category": "数据结构",
            "progress_id": "ds.test.new",
            "status": "active",
            "comment": "开始学习",
        })

        assert "Error" in result
        assert "name is required" in result


class TestReadIndex:
    """Tests for read_index tool."""

    @pytest.mark.asyncio
    async def test_read_index(self, sample_kb, monkeypatch):
        """Test reading index file."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await read_index_handler({
            "category": "数据结构",
            "material": "数据结构教材",
        })

        assert "章节结构" in result
        assert "Kruskal算法" in result

    @pytest.mark.asyncio
    async def test_read_index_not_found(self, sample_kb, monkeypatch):
        """Test reading non-existent index."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await read_index_handler({
            "category": "数据结构",
            "material": "算法笔记",
        })

        assert "Index not found" in result


class TestReadFile:
    """Tests for read_file tool."""

    @pytest.mark.asyncio
    async def test_read_file(self, sample_kb, monkeypatch):
        """Test reading file range."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await read_file_handler({
            "category": "数据结构",
            "material": "数据结构教材",
            "start_line": 1,
            "end_line": 10,
        })

        assert "数据结构/数据结构教材" in result
        assert "L1-10" in result

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, sample_kb, monkeypatch):
        """Test reading non-existent file."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await read_file_handler({
            "category": "数据结构",
            "material": "不存在",
            "start_line": 1,
            "end_line": 10,
        })

        assert "Error" in result


class TestGrep:
    """Tests for grep tool."""

    @pytest.mark.asyncio
    async def test_grep_single_file(self, sample_kb, monkeypatch):
        """Test grep in single file."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await grep_handler({
            "category": "数据结构",
            "pattern": "Kruskal",
            "material": "数据结构教材",
        })

        assert "grep" in result
        assert "Kruskal" in result
        assert "matches" in result

    @pytest.mark.asyncio
    async def test_grep_all_files(self, sample_kb, monkeypatch):
        """Test grep across all files."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await grep_handler({
            "category": "数据结构",
            "pattern": "算法",
        })

        assert "grep" in result
        assert "数据结构/*" in result

    @pytest.mark.asyncio
    async def test_grep_no_matches(self, sample_kb, monkeypatch):
        """Test grep with no matches."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await grep_handler({
            "category": "数据结构",
            "pattern": "量子计算",
        })

        assert "0 matches" in result
