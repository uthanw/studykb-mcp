"""Tests for KBService."""

import pytest

from studykb_mcp.services.kb_service import KBService


class TestKBService:
    """Tests for KBService."""

    @pytest.mark.asyncio
    async def test_list_categories(self, sample_kb):
        """Test listing categories."""
        service = KBService(kb_path=sample_kb)
        categories = await service.list_categories()

        assert len(categories) == 2
        names = [c.name for c in categories]
        assert "数据结构" in names
        assert "计算机组成原理" in names

    @pytest.mark.asyncio
    async def test_list_categories_empty(self, empty_kb):
        """Test listing categories when KB is empty."""
        service = KBService(kb_path=empty_kb)
        categories = await service.list_categories()

        assert len(categories) == 0

    @pytest.mark.asyncio
    async def test_list_materials(self, sample_kb):
        """Test listing materials in a category."""
        service = KBService(kb_path=sample_kb)
        categories = await service.list_categories()

        ds_category = next(c for c in categories if c.name == "数据结构")
        assert ds_category.file_count == 2

        material_names = [m.name for m in ds_category.materials]
        assert "数据结构教材" in material_names
        assert "算法笔记" in material_names

    @pytest.mark.asyncio
    async def test_material_has_index(self, sample_kb):
        """Test detecting index files."""
        service = KBService(kb_path=sample_kb)
        categories = await service.list_categories()

        ds_category = next(c for c in categories if c.name == "数据结构")
        ds_material = next(m for m in ds_category.materials if m.name == "数据结构教材")
        notes_material = next(m for m in ds_category.materials if m.name == "算法笔记")

        assert ds_material.has_index is True
        assert notes_material.has_index is False

    @pytest.mark.asyncio
    async def test_read_file_range(self, sample_kb):
        """Test reading a range of lines from a file."""
        service = KBService(kb_path=sample_kb)
        lines, truncated = await service.read_file_range(
            category="数据结构",
            material="数据结构教材",
            start_line=1,
            end_line=5,
        )

        assert truncated is False
        assert len(lines) == 5
        assert lines[0][0] == 1  # Line number
        assert "数据结构教材" in lines[0][1]  # Content

    @pytest.mark.asyncio
    async def test_read_file_range_truncation(self, sample_kb):
        """Test truncation when requesting too many lines."""
        service = KBService(kb_path=sample_kb)
        lines, truncated = await service.read_file_range(
            category="数据结构",
            material="数据结构教材",
            start_line=1,
            end_line=1000,
            max_lines=10,
        )

        assert truncated is True
        assert len(lines) == 10

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, sample_kb):
        """Test reading a non-existent file."""
        service = KBService(kb_path=sample_kb)

        with pytest.raises(FileNotFoundError):
            await service.read_file_range(
                category="数据结构",
                material="不存在的文件",
                start_line=1,
                end_line=10,
            )

    @pytest.mark.asyncio
    async def test_read_index(self, sample_kb):
        """Test reading an index file."""
        service = KBService(kb_path=sample_kb)
        content = await service.read_index(category="数据结构", material="数据结构教材")

        assert content is not None
        assert "章节结构" in content
        assert "Kruskal算法" in content

    @pytest.mark.asyncio
    async def test_read_index_not_found(self, sample_kb):
        """Test reading a non-existent index file."""
        service = KBService(kb_path=sample_kb)
        content = await service.read_index(category="数据结构", material="算法笔记")

        assert content is None

    @pytest.mark.asyncio
    async def test_grep_single_file(self, sample_kb):
        """Test grepping in a single file."""
        service = KBService(kb_path=sample_kb)
        results = await service.grep(
            category="数据结构",
            pattern="Kruskal",
            material="数据结构教材",
        )

        assert len(results) == 1
        assert results[0].material == "数据结构教材"
        assert results[0].total_matches >= 1

    @pytest.mark.asyncio
    async def test_grep_all_files(self, sample_kb):
        """Test grepping across all files in a category."""
        service = KBService(kb_path=sample_kb)
        results = await service.grep(
            category="数据结构",
            pattern="算法",
        )

        assert len(results) >= 1
        total_matches = sum(r.total_matches for r in results)
        assert total_matches >= 1

    @pytest.mark.asyncio
    async def test_grep_no_matches(self, sample_kb):
        """Test grepping with no matches."""
        service = KBService(kb_path=sample_kb)
        results = await service.grep(
            category="数据结构",
            pattern="量子计算",
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_grep_case_insensitive(self, sample_kb):
        """Test that grep is case-insensitive."""
        service = KBService(kb_path=sample_kb)
        results = await service.grep(
            category="数据结构",
            pattern="kruskal",  # lowercase
            material="数据结构教材",
        )

        assert len(results) == 1
        assert results[0].total_matches >= 1

    @pytest.mark.asyncio
    async def test_grep_context_lines(self, sample_kb):
        """Test grep context lines."""
        service = KBService(kb_path=sample_kb)
        results = await service.grep(
            category="数据结构",
            pattern="Kruskal",
            material="数据结构教材",
            context_lines=3,
        )

        assert len(results) == 1
        match = results[0].matches[0]
        # Context should include lines before and after
        assert len(match.context) >= 1

    @pytest.mark.asyncio
    async def test_category_exists(self, sample_kb):
        """Test checking if a category exists."""
        service = KBService(kb_path=sample_kb)

        assert await service.category_exists("数据结构") is True
        assert await service.category_exists("不存在的分类") is False

    @pytest.mark.asyncio
    async def test_material_exists(self, sample_kb):
        """Test checking if a material exists."""
        service = KBService(kb_path=sample_kb)

        assert await service.material_exists("数据结构", "数据结构教材") is True
        assert await service.material_exists("数据结构", "不存在的教材") is False
