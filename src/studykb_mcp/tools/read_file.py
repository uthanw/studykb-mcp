"""read_file tool - Read material file content."""

from typing import Any

from ..services.kb_service import KBService
from ..utils.formatters import format_read_file


async def read_file_handler(arguments: dict[str, Any]) -> str:
    """Handle read_file tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - material (str): Material name without extension (required)
            - start_line (int): Start line number, 1-based (required)
            - end_line (int): End line number, 1-based (required)

    Returns:
        Formatted file content or error message
    """
    category: str = arguments["category"]
    material: str = arguments["material"]
    start_line: int = arguments["start_line"]
    end_line: int = arguments["end_line"]

    kb_service = KBService()

    try:
        lines, truncated = await kb_service.read_file_range(
            category=category,
            material=material,
            start_line=start_line,
            end_line=end_line,
        )
    except FileNotFoundError as e:
        return f"❌ Error: {e}"

    return format_read_file(category, material, start_line, end_line, lines, truncated)
