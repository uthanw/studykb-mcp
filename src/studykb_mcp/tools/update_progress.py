"""update_progress tool - Update existing progress entry."""

from typing import Any

from ..models.progress import ProgressStatus, RelatedSection
from ..services.progress_service import ProgressService
from ..utils.formatters import format_progress_update


def _parse_sections(sections_data: list[dict] | None) -> list[RelatedSection] | None:
    """Parse sections data from arguments."""
    if sections_data is None:
        return None
    return [
        RelatedSection(
            material=s["material"],
            start_line=s["start_line"],
            end_line=s["end_line"],
            desc=s.get("desc", ""),
        )
        for s in sections_data
    ]


async def update_progress_handler(arguments: dict[str, Any]) -> str:
    """Handle update_progress tool call - update existing entry only.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Existing progress ID (required)
            - status (str): Status (required)
            - comment (str, optional): Comment/notes
            - related_sections (list, optional): Related material sections

    Returns:
        Formatted update confirmation or error
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]
    status: ProgressStatus = arguments["status"]
    comment: str = arguments.get("comment", "")
    related_sections = _parse_sections(arguments.get("related_sections"))

    service = ProgressService()

    # Check if entry exists - use get_full_progress to avoid filtering
    progress_file = await service.get_full_progress(category)
    if progress_id not in progress_file.entries:
        return f"❌ 进度节点不存在: {progress_id}\n\n请先使用 read_progress 确认现有节点，或使用 create_progress 创建新节点。"

    try:
        entry, is_new, old_status = await service.update_progress(
            category=category,
            progress_id=progress_id,
            status=status,
            name=None,  # Don't update name
            comment=comment,
            related_sections=related_sections,
        )
    except ValueError as e:
        return f"❌ Error: {e}"

    return format_progress_update(category, progress_id, entry, is_new, old_status)


async def create_progress_handler(arguments: dict[str, Any]) -> str:
    """Handle create_progress tool call - create new entry only.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): New progress ID (required)
            - name (str): Knowledge point name (required)
            - status (str, optional): Initial status (default: pending)
            - comment (str, optional): Comment/notes
            - related_sections (list, optional): Related material sections

    Returns:
        Formatted creation confirmation or error
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]
    name: str = arguments["name"]
    status: ProgressStatus = arguments.get("status", "pending")
    comment: str = arguments.get("comment", "")
    related_sections = _parse_sections(arguments.get("related_sections"))

    service = ProgressService()

    # Check if entry already exists - use get_full_progress to avoid filtering
    progress_file = await service.get_full_progress(category)
    if progress_id in progress_file.entries:
        existing = progress_file.entries[progress_id]
        return f"❌ 进度节点已存在: {progress_id} ({existing.name})\n\n如需更新状态，请使用 update_progress 工具。"

    try:
        entry, is_new, old_status = await service.update_progress(
            category=category,
            progress_id=progress_id,
            status=status,
            name=name,
            comment=comment,
            related_sections=related_sections,
        )
    except ValueError as e:
        return f"❌ Error: {e}"

    return format_progress_update(category, progress_id, entry, is_new, old_status)


async def delete_progress_handler(arguments: dict[str, Any]) -> str:
    """Handle delete_progress tool call - delete existing entry.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Progress ID to delete (required)

    Returns:
        Deletion confirmation or error
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]

    service = ProgressService()

    try:
        deleted_entry = await service.delete_progress(category, progress_id)
        if deleted_entry:
            return f"✅ 已删除进度节点\n\n{category} / {progress_id}\n{deleted_entry.name} [{deleted_entry.status}]"
        else:
            return f"❌ 进度节点不存在: {progress_id}"
    except Exception as e:
        return f"❌ 删除失败: {e}"
