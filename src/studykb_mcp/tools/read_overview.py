"""read_overview tool - Get knowledge base overview."""

from ..services.kb_service import KBService
from ..utils.formatters import format_overview


async def read_overview_handler(arguments: dict) -> str:
    """Handle read_overview tool call.

    Args:
        arguments: Tool arguments (none expected)

    Returns:
        Formatted knowledge base overview
    """
    kb_service = KBService()
    categories = await kb_service.list_categories()
    return format_overview(categories)
