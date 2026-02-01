"""read_index tool - Read material index file."""

from typing import Any

from ..services.kb_service import KBService
from ..utils.formatters import format_index_not_found


async def read_index_handler(arguments: dict[str, Any]) -> str:
    """Handle read_index tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - material (str): Material name without extension (required)

    Returns:
        Index file content or error message
    """
    category: str = arguments["category"]
    material: str = arguments["material"]

    kb_service = KBService()
    content = await kb_service.read_index(category, material)

    if content is None:
        # Get available files for error message
        categories = await kb_service.get_overview()
        available_files: list[str] = []
        for cat in categories:
            if cat.name == category:
                for mat in cat.materials:
                    suffix = " [IDX]" if mat.has_index else ""
                    available_files.append(f"{mat.name}{suffix}")
                break
        return format_index_not_found(category, material, available_files)

    return content
