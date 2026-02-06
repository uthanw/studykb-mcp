"""History service for workspace file version management.

Stores full-file snapshots on every MCP write/edit/delete operation,
enabling diff comparison and one-click rollback.

Storage layout under each workspace:
    .history/
        {file_path}.history.json   # version metadata
        {file_path}/
            {timestamp_ms}.snapshot  # full content snapshot
"""

import json
import os
import time
from pathlib import Path

import aiofiles
import aiofiles.os

from ..config import settings


class HistoryService:
    """Manages version history snapshots for a single workspace directory."""

    HISTORY_DIR = ".history"

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self.max_versions = settings.max_history_versions

    # ── internal helpers ─────────────────────────────────────

    def _history_root(self) -> Path:
        return self.workspace_path / self.HISTORY_DIR

    def _meta_path(self, file_path: str) -> Path:
        """Metadata JSON path for a tracked file."""
        return self._history_root() / f"{file_path}.history.json"

    def _snapshot_dir(self, file_path: str) -> Path:
        """Directory holding snapshots for a tracked file."""
        return self._history_root() / file_path

    async def _read_meta(self, file_path: str) -> dict:
        meta_path = self._meta_path(file_path)
        if not await aiofiles.os.path.exists(meta_path):
            return {"file_path": file_path, "versions": []}
        async with aiofiles.open(meta_path, "r", encoding="utf-8") as f:
            return json.loads(await f.read())

    async def _write_meta(self, file_path: str, meta: dict) -> None:
        meta_path = self._meta_path(file_path)
        await aiofiles.os.makedirs(meta_path.parent, exist_ok=True)
        tmp = meta_path.with_suffix(".tmp")
        async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, ensure_ascii=False, indent=2))
        await aiofiles.os.replace(tmp, meta_path)

    async def _prune_old_versions(self, file_path: str, meta: dict) -> dict:
        """Remove oldest versions exceeding max_versions limit."""
        versions = meta.get("versions", [])
        if len(versions) <= self.max_versions:
            return meta

        to_remove = versions[self.max_versions:]
        meta["versions"] = versions[:self.max_versions]

        snap_dir = self._snapshot_dir(file_path)
        for v in to_remove:
            snap_file = snap_dir / f"{v['version_id']}.snapshot"
            try:
                if await aiofiles.os.path.exists(snap_file):
                    await aiofiles.os.remove(snap_file)
            except OSError:
                pass

        return meta

    # ── public API ───────────────────────────────────────────

    async def save_snapshot(
        self,
        file_path: str,
        content: str,
        operation: str,
        description: str = "",
    ) -> str:
        """Save a full-file snapshot.

        Args:
            file_path: Relative file path within workspace (e.g. "note.md")
            content: Full file content to snapshot
            operation: One of "create", "write", "edit", "delete"
            description: Human-readable description of the change

        Returns:
            version_id (millisecond timestamp string)
        """
        version_id = str(int(time.time() * 1000))

        # Write snapshot file
        snap_dir = self._snapshot_dir(file_path)
        await aiofiles.os.makedirs(snap_dir, exist_ok=True)
        snap_file = snap_dir / f"{version_id}.snapshot"
        async with aiofiles.open(snap_file, "w", encoding="utf-8") as f:
            await f.write(content)

        # Update metadata (newest first)
        meta = await self._read_meta(file_path)
        entry = {
            "version_id": version_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "operation": operation,
            "description": description or f"文件{_OP_LABELS.get(operation, '操作')}",
            "size": len(content.encode("utf-8")),
            "lines": content.count("\n") + 1 if content else 0,
        }
        meta["versions"].insert(0, entry)

        # Prune & persist
        meta = await self._prune_old_versions(file_path, meta)
        await self._write_meta(file_path, meta)

        return version_id

    async def list_versions(self, file_path: str) -> list[dict]:
        """Return version list for a file (newest first)."""
        meta = await self._read_meta(file_path)
        return meta.get("versions", [])

    async def get_version_content(self, file_path: str, version_id: str) -> str:
        """Read the content of a specific snapshot.

        Raises:
            FileNotFoundError: If snapshot file is missing.
        """
        snap_file = self._snapshot_dir(file_path) / f"{version_id}.snapshot"
        if not await aiofiles.os.path.exists(snap_file):
            raise FileNotFoundError(f"快照不存在: {file_path} @ {version_id}")
        async with aiofiles.open(snap_file, "r", encoding="utf-8") as f:
            return await f.read()


# ── helpers ──────────────────────────────────────────────────

_OP_LABELS: dict[str, str] = {
    "create": "创建",
    "write": "覆写",
    "edit": "编辑",
    "delete": "删除",
}
