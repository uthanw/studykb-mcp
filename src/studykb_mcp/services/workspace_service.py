"""Workspace service for progress node file operations."""

import os
from pathlib import Path

import aiofiles
import aiofiles.os

from ..config import settings
from .edit_strategy import EditStrategy, ReplaceResult
from .history_service import HistoryService


class WorkspaceService:
    """Service for managing progress node workspaces.

    Each progress node (progress_id) can have its own workspace directory
    containing notes, code files, and other resources.

    Directory structure:
        workspaces/{category}/{progress_id}/
            ├── note.md          # Default note file
            ├── code/            # Code files
            ├── assets/          # Images and other resources
            └── .history/        # Version snapshots (auto-managed)
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
        """
        safe_id = progress_id.replace(".", "_")
        return self.workspaces_path / category / safe_id

    def _validate_path(self, workspace_path: Path, file_path: str) -> Path:
        """Validate that file path is within workspace (prevent path traversal)."""
        full_path = (workspace_path / file_path).resolve()
        workspace_resolved = workspace_path.resolve()

        if not str(full_path).startswith(str(workspace_resolved)):
            raise ValueError(f"路径越界: {file_path}")

        return full_path

    def _get_history(self, category: str, progress_id: str) -> HistoryService:
        """Get HistoryService for a workspace."""
        return HistoryService(self._get_workspace_path(category, progress_id))

    async def ensure_workspace(self, category: str, progress_id: str) -> Path:
        """Ensure workspace directory exists."""
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

        async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
            all_lines = await f.readlines()

        if start_line is None:
            start_line = 1
        if end_line is None:
            end_line = len(all_lines)

        actual_start = max(1, start_line) - 1
        actual_end = min(len(all_lines), end_line)

        if actual_end - actual_start > self.max_read_lines:
            actual_end = actual_start + self.max_read_lines
            truncated = True

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

        Automatically saves a history snapshot:
        - If the file already exists, snapshots the OLD content (operation=write)
        - If the file is new, snapshots the NEW content (operation=create)
        """
        if len(content.encode("utf-8")) > self.max_file_size:
            raise ValueError(f"内容过大 (最大 {self.max_file_size} bytes)")

        workspace_path = await self.ensure_workspace(category, progress_id)
        full_path = self._validate_path(workspace_path, file_path)
        await aiofiles.os.makedirs(full_path.parent, exist_ok=True)

        history = self._get_history(category, progress_id)
        file_exists = await aiofiles.os.path.exists(full_path)

        if file_exists:
            # Snapshot the OLD content before overwriting
            async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                old_content = await f.read()
            await history.save_snapshot(file_path, old_content, "write", "文件覆写")

        # Write atomically
        temp_path = full_path.with_suffix(".tmp")
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        await aiofiles.os.replace(temp_path, full_path)

        if not file_exists:
            # Snapshot the NEW content for create
            await history.save_snapshot(file_path, content, "create", "文件创建")

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

        Automatically saves a snapshot of OLD content on success.
        """
        workspace_path = self._get_workspace_path(category, progress_id)
        full_path = self._validate_path(workspace_path, file_path)

        if not await aiofiles.os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
            content = await f.read()

        result = self.edit_strategy.perform_replacement(
            content, old_string, new_string, expected_replacements
        )

        if result.success and result.content is not None:
            # Snapshot OLD content before saving edit
            history = self._get_history(category, progress_id)
            await history.save_snapshot(file_path, content, "edit", "文件编辑")

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

        Automatically saves a snapshot of the content before deletion.
        """
        workspace_path = self._get_workspace_path(category, progress_id)
        full_path = self._validate_path(workspace_path, file_path)

        if not await aiofiles.os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if await aiofiles.os.path.isdir(full_path):
            raise IsADirectoryError(f"不能删除目录: {file_path}")

        # Snapshot content before deletion
        history = self._get_history(category, progress_id)
        try:
            async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                old_content = await f.read()
            await history.save_snapshot(file_path, old_content, "delete", "文件删除")
        except (UnicodeDecodeError, OSError):
            pass  # binary files or read errors — skip snapshot

        await aiofiles.os.remove(full_path)

    async def list_files(
        self,
        category: str,
        progress_id: str,
    ) -> list[dict[str, str | int]]:
        """List all files in workspace (excluding .history directory)."""
        workspace_path = self._get_workspace_path(category, progress_id)

        if not await aiofiles.os.path.exists(workspace_path):
            return []

        files: list[dict[str, str | int]] = []

        for root, dirs, filenames in os.walk(workspace_path):
            # Skip the .history directory
            dirs[:] = [d for d in dirs if d != HistoryService.HISTORY_DIR]

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

        files.sort(key=lambda f: f["path"])
        return files

    async def workspace_exists(self, category: str, progress_id: str) -> bool:
        """Check if workspace exists."""
        workspace_path = self._get_workspace_path(category, progress_id)
        return await aiofiles.os.path.exists(workspace_path)

    # ── History API ──────────────────────────────────────────

    async def list_file_history(
        self, category: str, progress_id: str, file_path: str
    ) -> list[dict]:
        """Return version list for a file (newest first)."""
        history = self._get_history(category, progress_id)
        return await history.list_versions(file_path)

    async def get_file_version(
        self, category: str, progress_id: str, file_path: str, version_id: str
    ) -> str:
        """Get the content of a specific historical version."""
        history = self._get_history(category, progress_id)
        return await history.get_version_content(file_path, version_id)

    async def rollback_file(
        self, category: str, progress_id: str, file_path: str, version_id: str
    ) -> None:
        """Rollback a file to a previous version.

        Reads the old snapshot and writes it via write_file(),
        which automatically saves the current content as a new snapshot.
        """
        old_content = await self.get_file_version(
            category, progress_id, file_path, version_id
        )
        await self.write_file(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
            content=old_content,
        )
