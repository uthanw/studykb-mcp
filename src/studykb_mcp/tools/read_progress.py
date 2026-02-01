"""read_progress tool - Get learning progress for a category."""

from typing import Any

from ..models.progress import ProgressStatus
from ..services.progress_service import ProgressService
from ..utils.formatters import format_progress, format_progress_detail


async def read_progress_handler(arguments: dict[str, Any]) -> str:
    """Handle read_progress tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str, optional): Specific progress ID for detail view
            - status_filter (list[str], optional): Filter by status
            - since (str, optional): Time range filter ("7d", "30d", "90d", "all")
            - show_time (bool, optional): Include time info in list view (default: False)

    Returns:
        Formatted progress data (list or detail view)
    """
    category: str = arguments["category"]
    progress_id: str | None = arguments.get("progress_id")
    status_filter: list[ProgressStatus] | None = arguments.get("status_filter")
    since: str = arguments.get("since", "all")
    show_time: bool = arguments.get("show_time", False)

    service = ProgressService()

    # If progress_id specified, return detail view
    if progress_id:
        progress_file = await service.get_full_progress(category)
        if progress_id not in progress_file.entries:
            return f"# error: not_found\nprogress_id: {progress_id}\nmessage: 进度节点不存在"
        entry = progress_file.entries[progress_id]
        return format_progress_detail(category, progress_id, entry)

    # Otherwise return list view
    progress = await service.get_progress(
        category=category,
        status_filter=status_filter,
        since=since,  # type: ignore
        limit=-1,  # Always return all entries
    )

    return format_progress(progress, status_filter, show_time=show_time)
