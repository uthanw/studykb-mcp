"""read_progress tool - Get learning progress for a category."""

from typing import Any

from ..models.progress import ProgressStatus
from ..services.progress_service import ProgressService
from ..utils.formatters import format_progress


async def read_progress_handler(arguments: dict[str, Any]) -> str:
    """Handle read_progress tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - status_filter (list[str], optional): Filter by status
            - since (str, optional): Time range filter ("7d", "30d", "90d", "all")
            - limit (int, optional): Max entries per status group

    Returns:
        Formatted progress data
    """
    category: str = arguments["category"]
    status_filter: list[ProgressStatus] | None = arguments.get("status_filter")
    since: str = arguments.get("since", "all")
    limit: int = arguments.get("limit", 20)

    service = ProgressService()
    progress = await service.get_progress(
        category=category,
        status_filter=status_filter,
        since=since,  # type: ignore
        limit=limit,
    )

    return format_progress(progress, status_filter, limit)
