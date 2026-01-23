"""update_progress tool - Create or update progress entry."""

from typing import Any

from ..models.progress import ProgressStatus
from ..services.progress_service import ProgressService
from ..utils.formatters import format_progress_update


async def update_progress_handler(arguments: dict[str, Any]) -> str:
    """Handle update_progress tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Progress ID (required)
            - status (str): Status (required, one of: active, done, review)
            - name (str, optional): Knowledge point name (required for new)
            - comment (str): Comment/notes (required)

    Returns:
        Formatted update confirmation
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]
    status: ProgressStatus = arguments["status"]
    name: str | None = arguments.get("name")
    comment: str = arguments.get("comment", "")

    service = ProgressService()

    try:
        entry, is_new, old_status = await service.update_progress(
            category=category,
            progress_id=progress_id,
            status=status,
            name=name,
            comment=comment,
        )
    except ValueError as e:
        return f"❌ Error: {e}"

    return format_progress_update(category, progress_id, entry, is_new, old_status)
