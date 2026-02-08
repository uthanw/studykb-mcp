"""Knowledge base service for file operations."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import aiofiles
import aiofiles.os

from ..config import settings
from ..models.kb import Category, Material


@dataclass
class GrepMatch:
    """A single grep match with context."""

    line_num: int
    context: list[dict[str, int | str | bool]]


@dataclass
class GrepResult:
    """Grep results for a single file."""

    material: str
    matches: list[GrepMatch]
    total_matches: int


class KBService:
    """Service for knowledge base file operations."""

    def __init__(self, kb_path: Path | None = None) -> None:
        self.kb_path = kb_path or settings.kb_path

    async def list_categories(self) -> list[Category]:
        """List all categories in the knowledge base.

        Returns:
            List of categories sorted by name
        """
        categories: list[Category] = []

        if not await aiofiles.os.path.exists(self.kb_path):
            return categories

        for entry in await aiofiles.os.listdir(self.kb_path):
            entry_path = self.kb_path / entry
            if await aiofiles.os.path.isdir(entry_path) and not entry.startswith("."):
                materials = await self._list_materials(entry_path)
                categories.append(Category(name=entry, materials=materials))

        return sorted(categories, key=lambda c: c.name)

    async def _list_materials(self, category_path: Path) -> list[Material]:
        """List all materials in a category.

        Args:
            category_path: Path to the category directory

        Returns:
            List of materials
        """
        materials: list[Material] = []

        for entry in await aiofiles.os.listdir(category_path):
            if entry.endswith(".md") and not entry.endswith("_index.md"):
                file_path = category_path / entry
                line_count = await self._count_lines(file_path)
                has_index = await self._check_index_exists(category_path, entry)

                materials.append(
                    Material(
                        name=entry,  # Keep full filename with .md extension
                        line_count=line_count,
                        has_index=has_index,
                    )
                )

        return sorted(materials, key=lambda m: m.name)

    async def _count_lines(self, file_path: Path) -> int:
        """Count the number of lines in a file using wc -l for speed.

        Args:
            file_path: Path to the file

        Returns:
            Number of lines
        """
        try:
            # Use wc -l for fast line counting (much faster than reading file in Python)
            result = subprocess.run(
                ["wc", "-l", str(file_path)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # wc -l output format: "  12345 /path/to/file"
                return int(result.stdout.strip().split()[0])
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            pass

        # Fallback to Python counting if wc fails
        count = 0
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            async for _ in f:
                count += 1
        return count

    async def _check_index_exists(self, category_path: Path, material_name: str) -> bool:
        """Check if an index file exists for a material.

        Args:
            category_path: Path to the category directory
            material_name: Name of the material file (with .md extension)

        Returns:
            True if index file exists
        """
        stem = material_name.replace(".md", "")
        # CSV 优先，MD 回退
        csv_path = category_path / f"{stem}_index.csv"
        if await aiofiles.os.path.exists(csv_path):
            return True
        md_path = category_path / f"{stem}_index.md"
        return await aiofiles.os.path.exists(md_path)

    async def read_file_range(
        self,
        category: str,
        material: str,
        start_line: int,
        end_line: int,
        max_lines: int | None = None,
    ) -> tuple[list[tuple[int, str]], bool]:
        """Read a range of lines from a material file.

        Args:
            category: Category name
            material: Material name (with .md extension)
            start_line: Starting line number (1-based, inclusive)
            end_line: Ending line number (1-based, inclusive)
            max_lines: Maximum number of lines to return (default from settings)

        Returns:
            Tuple of (list of (line_number, line_content), was_truncated)

        Raises:
            FileNotFoundError: If the material file doesn't exist
        """
        if max_lines is None:
            max_lines = settings.max_read_lines

        file_path = self.kb_path / category / material

        if not await aiofiles.os.path.exists(file_path):
            raise FileNotFoundError(f"Material not found: {category}/{material}")

        lines: list[tuple[int, str]] = []
        truncated = False
        actual_end = min(end_line, start_line + max_lines - 1)

        if end_line - start_line + 1 > max_lines:
            truncated = True

        line_num = 0
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            async for line in f:
                line_num += 1
                if line_num < start_line:
                    continue
                if line_num > actual_end:
                    break
                lines.append((line_num, line.rstrip("\n")))

        return lines, truncated

    async def read_index(self, category: str, material: str) -> str | None:
        """Read the index file for a material.

        Args:
            category: Category name
            material: Material name (with .md extension)

        Returns:
            Index file content, or None if not found
        """
        stem = material.replace(".md", "")
        category_path = self.kb_path / category

        # CSV 优先
        csv_path = category_path / f"{stem}_index.csv"
        if await aiofiles.os.path.exists(csv_path):
            async with aiofiles.open(csv_path, "r", encoding="utf-8") as f:
                return await f.read()

        # MD 回退
        md_path = category_path / f"{stem}_index.md"
        if await aiofiles.os.path.exists(md_path):
            async with aiofiles.open(md_path, "r", encoding="utf-8") as f:
                return await f.read()

        return None

    async def grep(
        self,
        category: str,
        pattern: str,
        material: str | None = None,
        context_lines: int = 2,
        max_matches: int | None = None,
    ) -> list[GrepResult]:
        """Search for a pattern in materials.

        Args:
            category: Category name
            pattern: Search pattern (case-insensitive)
            material: Optional material name to search in (with .md extension, searches all if None)
            context_lines: Number of context lines before and after match
            max_matches: Maximum total matches to return (default from settings)

        Returns:
            List of GrepResult objects
        """
        if max_matches is None:
            max_matches = settings.max_grep_matches

        results: list[GrepResult] = []
        total_found = 0

        category_path = self.kb_path / category

        if not await aiofiles.os.path.exists(category_path):
            return results

        if material:
            # Search single file
            file_path = category_path / material
            if await aiofiles.os.path.exists(file_path):
                matches = await self._grep_file(file_path, pattern, context_lines, max_matches)
                if matches:
                    results.append(
                        GrepResult(
                            material=material,
                            matches=matches,
                            total_matches=len(matches),
                        )
                    )
        else:
            # Search all files in category
            for entry in sorted(await aiofiles.os.listdir(category_path)):
                if entry.endswith(".md") and not entry.endswith("_index.md"):
                    file_path = category_path / entry
                    remaining = max_matches - total_found
                    if remaining <= 0:
                        break

                    matches = await self._grep_file(
                        file_path, pattern, context_lines, remaining
                    )
                    if matches:
                        results.append(
                            GrepResult(
                                material=entry,  # Keep full filename with .md
                                matches=matches,
                                total_matches=len(matches),
                            )
                        )
                        total_found += len(matches)

        return results

    async def _grep_file(
        self,
        file_path: Path,
        pattern: str,
        context_lines: int,
        max_matches: int,
    ) -> list[GrepMatch]:
        """Search for a pattern in a single file.

        Args:
            file_path: Path to the file
            pattern: Search pattern (case-insensitive)
            context_lines: Number of context lines
            max_matches: Maximum matches to return

        Returns:
            List of GrepMatch objects
        """
        matches: list[GrepMatch] = []
        all_lines: list[str] = []

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            async for line in f:
                all_lines.append(line.rstrip("\n"))

        pattern_lower = pattern.lower()

        for i, line in enumerate(all_lines):
            if pattern_lower in line.lower():
                if len(matches) >= max_matches:
                    break

                # Collect context
                start = max(0, i - context_lines)
                end = min(len(all_lines), i + context_lines + 1)
                context: list[dict[str, int | str | bool]] = [
                    {
                        "line_num": j + 1,
                        "text": all_lines[j],
                        "is_match": j == i,
                    }
                    for j in range(start, end)
                ]
                matches.append(GrepMatch(line_num=i + 1, context=context))

        return matches

    async def category_exists(self, category: str) -> bool:
        """Check if a category exists.

        Args:
            category: Category name

        Returns:
            True if category exists
        """
        return await aiofiles.os.path.exists(self.kb_path / category)

    async def material_exists(self, category: str, material: str) -> bool:
        """Check if a material exists.

        Args:
            category: Category name
            material: Material name (with .md extension)

        Returns:
            True if material exists
        """
        return await aiofiles.os.path.exists(self.kb_path / category / material)
