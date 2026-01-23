"""grep tool - Search for patterns in materials."""

from typing import Any

from ..services.kb_service import KBService
from ..utils.formatters import format_grep_results


async def grep_handler(arguments: dict[str, Any]) -> str:
    """Handle grep tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - pattern (str): Search pattern (required)
            - material (str, optional): Material name to search in
            - context_lines (int, optional): Context lines before/after match
            - max_matches (int, optional): Maximum matches to return

    Returns:
        Formatted search results
    """
    category: str = arguments["category"]
    pattern: str = arguments["pattern"]
    material: str | None = arguments.get("material")
    context_lines: int = arguments.get("context_lines", 2)
    max_matches: int = arguments.get("max_matches", 20)

    kb_service = KBService()

    results = await kb_service.grep(
        category=category,
        pattern=pattern,
        material=material,
        context_lines=context_lines,
        max_matches=max_matches if max_matches > 0 else 1000,
    )

    return format_grep_results(category, pattern, material, results, max_matches)
