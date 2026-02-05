"""Workspace service for progress node file operations."""

import os
from pathlib import Path

import aiofiles
import aiofiles.os

from ..config import settings
from .edit_strategy import EditStrategy, ReplaceResult


class WorkspaceService:
    """Service for managing progress node workspaces.

    Each progress node (progress_id) can have its own workspace directory
    containing notes, code files, and other resources.

    Directory structure:
        workspaces/{category}/{progress_id}/
            ├── note.md          # Default note file
            ├── code/            # Code files
            └── assets/          # Images and other resources
    """

    def __init__(self, workspaces_path: Path | None = None) -> None:
        """Initialize workspace service.

        Args:
            workspaces_path: Path to workspaces directory (default from settings)
        """
        self.workspaces_path = workspaces_path or settings.workspaces_path
        self.edit_strategy = EditStrategy()
        self.max_file_size = settings.max_file_size
        self.max_read_lines = settings.max_read_lines

    def _get_workspace_path(self, category: str, progress_id: str) -> Path:
        """Get workspace directory path for a progress node.

        Converts dots in progress_id to underscores to avoid path issues.

        Args:
            category: Category name
            progress_id: Progress node ID (e.g., "ds.graph.mst.kruskal")

        Returns:
            Path to workspace directory
        """
        safe_id = progress_id.replace(".", "_")
        return self.workspaces_path / category / safe_id

    def _validate_path(self, workspace_path: Path, file_path: str) -> Path:
        """Validate that file path is within workspace (prevent path traversal).

        Args:
            workspace_path: Workspace directory path
            file_path: Relative file path within workspace

        Returns:
            Absolute path to file

        Raises:
            ValueError: If path escapes workspace directory
        """
        full_path = (workspace_path / file_path).resolve()
        workspace_resolved = workspace_path.resolve()

        if not str(full_path).startswith(str(workspace_resolved)):
            raise ValueError(f"路径越界: {file_path}")

        return full_path

    async def ensure_workspace(self, category: str, progress_id: str) -> Path:
        """Ensure workspace directory exists.

        Args:
            category: Category name
            progress_id: Progress node ID

        Returns:
            Path to workspace directory
        """
        workspace_path = self._get_workspace_path(category, progress_id)
        await aiofiles.os.makedirs(workspace_path, exist_ok=True)
        return workspace_path

    async def read_file(
        self,
        category: str,
        progress_id: str,
        file_path: str = "note.md",
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> tuple[list[tuple[int, str]], bool]:
        """Read file from workspace.

        Args:
            category: Category name
            progress_id: Progress node ID
            file_path: Relative file path within workspace (default "note.md")
            start_line: Starting line number (1-based, inclusive)
            end_line: Ending line number (1-based, inclusive)

        Returns:
            Tuple of (list of (line_number, line_content), was_truncated)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path escapes workspace
        """
        workspace_path = self._get_workspace_path(category, progress_id)
        full_path = self._validate_path(workspace_path, file_path)

        if not await aiofiles.os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # Check file size
        stat = await aiofiles.os.stat(full_path)
        if stat.st_size > self.max_file_size:
            raise ValueError(f"文件过大: {stat.st_size} bytes (最大 {self.max_file_size})")

        lines: list[tuple[int, str]] = []
        truncated = False

        # Read all lines
        async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
            all_lines = await f.readlines()

        # Apply line range filter
        if start_line is None:
            start_line = 1
        if end_line is None:
            end_line = len(all_lines)

        # Calculate actual range
        actual_start = max(1, start_line) - 1  # Convert to 0-based
        actual_end = min(len(all_lines), end_line)

        # Check if truncation needed
        if actual_end - actual_start > self.max_read_lines:
            actual_end = actual_start + self.max_read_lines
            truncated = True

        # Extract lines with line numbers
        for i in range(actual_start, actual_end):
            lines.append((i + 1, all_lines[i].rstrip("\n")))

        return lines, truncated

    async def write_file(
        self,
        category: str,
        progress_id: str,
        file_path: str = "note.md",
        content: str = "",
    ) -> None:
        """Write file to workspace (create or overwrite).

        Args:
            category: Category name
            progress_id: Progress node ID
            file_path: Relative file path within workspace (default "note.md")
            content: File content

        Raises:
            ValueError: If path escapes workspace or content too large
        """
        # Check content size
        if len(content.encode("utf-8")) > self.max_file_size:
            raise ValueError(f"内容过大 (最大 {self.max_file_size} bytes)")

        workspace_path = await self.ensure_workspace(category, progress_id)
        full_path = self._validate_path(workspace_path, file_path)

        # Ensure parent directory exists
        await aiofiles.os.makedirs(full_path.parent, exist_ok=True)

        # Write file atomically
        temp_path = full_path.with_suffix(".tmp")
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        await aiofiles.os.replace(temp_path, full_path)

    async def edit_file(
        self,
        category: str,
        progress_id: str,
        file_path: str = "note.md",
        old_string: str = "",
        new_string: str = "",
        expected_replacements: int = 1,
    ) -> ReplaceResult:
        """Edit file using three-tier matching strategy.

        Args:
            category: Category name
            progress_id: Progress node ID
            file_path: Relative file path within workspace (default "note.md")
            old_string: String to search for
            new_string: Replacement string
            expected_replacements: Expected number of matches

        Returns:
            ReplaceResult with success status and updated content or error

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path escapes workspace
        """
        workspace_path = self._get_workspace_path(category, progress_id)
        full_path = self._validate_path(workspace_path, file_path)

        if not await aiofiles.os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # Read current content
        async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
            content = await f.read()

        # Perform replacement using three-tier strategy
        result = self.edit_strategy.perform_replacement(
            content, old_string, new_string, expected_replacements
        )

        # Save if successful
        if result.success and result.content is not None:
            temp_path = full_path.with_suffix(".tmp")
            async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
                await f.write(result.content)
            await aiofiles.os.replace(temp_path, full_path)

        return result

    async def delete_file(
        self,
        category: str,
        progress_id: str,
        file_path: str,
    ) -> None:
        """Delete file from workspace.

        Args:
            category: Category name
            progress_id: Progress node ID
            file_path: Relative file path within workspace

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path escapes workspace
            IsADirectoryError: If path is a directory
        """
        workspace_path = self._get_workspace_path(category, progress_id)
        full_path = self._validate_path(workspace_path, file_path)

        if not await aiofiles.os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if await aiofiles.os.path.isdir(full_path):
            raise IsADirectoryError(f"不能删除目录: {file_path}")

        await aiofiles.os.remove(full_path)

    async def list_files(
        self,
        category: str,
        progress_id: str,
    ) -> list[dict[str, str | int]]:
        """List all files in workspace.

        Args:
            category: Category name
            progress_id: Progress node ID

        Returns:
            List of file info dicts with keys: path, type, size
        """
        workspace_path = self._get_workspace_path(category, progress_id)

        if not await aiofiles.os.path.exists(workspace_path):
            return []

        files: list[dict[str, str | int]] = []

        # Walk directory tree
        for root, dirs, filenames in os.walk(workspace_path):
            root_path = Path(root)
            rel_root = root_path.relative_to(workspace_path)

            for filename in filenames:
                file_path = root_path / filename
                rel_path = rel_root / filename if str(rel_root) != "." else Path(filename)

                try:
                    stat = await aiofiles.os.stat(file_path)
                    files.append({
                        "path": str(rel_path),
                        "type": "file",
                        "size": stat.st_size,
                    })
                except OSError:
                    continue

        # Sort by path
        files.sort(key=lambda f: f["path"])
        return files

    async def workspace_exists(self, category: str, progress_id: str) -> bool:
        """Check if workspace exists.

        Args:
            category: Category name
            progress_id: Progress node ID

        Returns:
            True if workspace directory exists
        """
        workspace_path = self._get_workspace_path(category, progress_id)
        return await aiofiles.os.path.exists(workspace_path)
