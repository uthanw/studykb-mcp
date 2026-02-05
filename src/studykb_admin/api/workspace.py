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


class FileInfo(BaseModel):
    """File information."""
    path: str
    type: str
    size: int


@router.get("/{category}/{progress_id}/files")
async def list_workspace_files(category: str, progress_id: str):
    """List all files in a workspace.

    Args:
        category: Category name
        progress_id: Progress node ID (dots will be converted to underscores)

    Returns:
        List of files with path, type, and size
    """
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
    """Read a file from workspace.

    Args:
        category: Category name
        progress_id: Progress node ID
        file_path: Relative file path within workspace (default: note.md)
        start_line: Optional start line number (1-based)
        end_line: Optional end line number (1-based)

    Returns:
        File content as string
    """
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

    # Join lines to content string
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
    """Create or overwrite a file in workspace.

    Args:
        category: Category name
        progress_id: Progress node ID
        body: Request body with file_path and content

    Returns:
        Success message
    """
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
    """Delete a file from workspace.

    Args:
        category: Category name
        progress_id: Progress node ID
        file_path: File path to delete

    Returns:
        Success message
    """
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
