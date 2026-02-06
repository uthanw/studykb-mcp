"""Workspace API - REST endpoints for workspace file operations."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from studykb_mcp.services.workspace_service import WorkspaceService

router = APIRouter()


class FileWriteRequest(BaseModel):
    """Request body for writing a file."""
    file_path: str
    content: str


class RollbackRequest(BaseModel):
    """Request body for rolling back a file to a previous version."""
    file_path: str
    version_id: str


class FileInfo(BaseModel):
    """File information."""
    path: str
    type: str
    size: int


@router.get("/{category}/{progress_id}/files")
async def list_workspace_files(category: str, progress_id: str):
    """List all files in a workspace."""
    service = WorkspaceService()

    files = await service.list_files(category=category, progress_id=progress_id)

    return {
        "category": category,
        "progress_id": progress_id,
        "files": files,
    }


@router.get("/{category}/{progress_id}/file")
async def read_workspace_file(
    category: str,
    progress_id: str,
    file_path: str = Query(default="note.md", description="File path within workspace"),
    start_line: Optional[int] = Query(default=None, description="Start line (1-based)"),
    end_line: Optional[int] = Query(default=None, description="End line (1-based)"),
):
    """Read a file from workspace."""
    service = WorkspaceService()

    try:
        lines, truncated = await service.read_file(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    content = "\n".join(line_content for _, line_content in lines)

    return {
        "category": category,
        "progress_id": progress_id,
        "file_path": file_path,
        "content": content,
        "line_count": len(lines),
        "truncated": truncated,
        "start_line": lines[0][0] if lines else None,
        "end_line": lines[-1][0] if lines else None,
    }


@router.post("/{category}/{progress_id}/file")
async def write_workspace_file(
    category: str,
    progress_id: str,
    body: FileWriteRequest,
):
    """Create or overwrite a file in workspace."""
    service = WorkspaceService()

    try:
        await service.write_file(
            category=category,
            progress_id=progress_id,
            file_path=body.file_path,
            content=body.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    line_count = body.content.count("\n") + 1 if body.content else 0

    return {
        "success": True,
        "category": category,
        "progress_id": progress_id,
        "file_path": body.file_path,
        "line_count": line_count,
    }


@router.delete("/{category}/{progress_id}/file")
async def delete_workspace_file(
    category: str,
    progress_id: str,
    file_path: str = Query(..., description="File path to delete"),
):
    """Delete a file from workspace."""
    service = WorkspaceService()

    try:
        await service.delete_file(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IsADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "category": category,
        "progress_id": progress_id,
        "file_path": file_path,
    }


# ── History endpoints ────────────────────────────────────────


@router.get("/{category}/{progress_id}/history")
async def list_file_history(
    category: str,
    progress_id: str,
    file_path: str = Query(..., description="File path to get history for"),
):
    """List version history for a workspace file (newest first)."""
    service = WorkspaceService()

    versions = await service.list_file_history(
        category=category,
        progress_id=progress_id,
        file_path=file_path,
    )

    return {
        "category": category,
        "progress_id": progress_id,
        "file_path": file_path,
        "versions": versions,
    }


@router.get("/{category}/{progress_id}/history/version")
async def get_file_version(
    category: str,
    progress_id: str,
    file_path: str = Query(..., description="File path"),
    version_id: str = Query(..., description="Version ID (timestamp)"),
):
    """Get the content of a specific historical version."""
    service = WorkspaceService()

    try:
        content = await service.get_file_version(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
            version_id=version_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "category": category,
        "progress_id": progress_id,
        "file_path": file_path,
        "version_id": version_id,
        "content": content,
    }


@router.post("/{category}/{progress_id}/history/rollback")
async def rollback_file(
    category: str,
    progress_id: str,
    body: RollbackRequest,
):
    """Rollback a file to a previous version.

    The current file content is automatically saved as a new snapshot
    before the rollback is applied.
    """
    service = WorkspaceService()

    try:
        await service.rollback_file(
            category=category,
            progress_id=progress_id,
            file_path=body.file_path,
            version_id=body.version_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "category": category,
        "progress_id": progress_id,
        "file_path": body.file_path,
        "rolled_back_to": body.version_id,
    }
