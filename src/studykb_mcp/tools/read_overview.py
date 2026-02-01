"""read_overview tool - Get overview of categories and materials."""

from typing import Any

from ..services.kb_service import KBService
from ..services.progress_service import ProgressService


def _escape_value(value: str) -> str:
    """Escape special characters in TOON values."""
    if not value:
        return ""
    value = value.replace("\\", "\\\\")
    value = value.replace(",", "\\,")
    return value


async def read_overview_handler(arguments: dict) -> str:
    """Handle read_overview tool call.

    Returns overview based on progress files (categories) and optionally
    linked knowledge base materials.

    Args:
        arguments: Tool arguments (none expected)

    Returns:
        TOON formatted overview
    """
    progress_service = ProgressService()
    kb_service = KBService()

    # Get categories from progress files
    progress_categories = await progress_service.list_categories()

    # Also check kb directories that might not have progress files yet
    kb_categories_data = await kb_service.list_categories()
    kb_category_names = {cat.name for cat in kb_categories_data}

    # Build combined category list
    all_category_names = set(progress_categories) | kb_category_names

    # Build TOON output
    lines = [
        "# overview",
        f"total: {len(all_category_names)} categories",
        f"with_progress: {len(progress_categories)}",
        f"with_kb: {len(kb_category_names)}",
    ]

    for cat_name in sorted(all_category_names):
        lines.append("")
        has_progress = cat_name in progress_categories
        has_kb = cat_name in kb_category_names
        flags = []
        if has_progress:
            flags.append("progress")
        if has_kb:
            flags.append("kb")
        lines.append(f"## {cat_name} [{','.join(flags)}]")

        # Get progress stats if available
        if has_progress:
            progress = await progress_service.get_progress(cat_name)
            stats = progress.get_stats()
            lines.append(f"stats: active={stats['active']},review={stats['review']},done={stats['done']},pending={stats['pending']}")

        # Get materials from kb if available
        if has_kb:
            kb_cat = next((c for c in kb_categories_data if c.name == cat_name), None)
            if kb_cat and kb_cat.materials:
                lines.append(f"materials[{len(kb_cat.materials)}]{{filename,lines,has_index}}:")
                for mat in kb_cat.materials:
                    index_flag = "Y" if mat.has_index else "N"
                    lines.append(f"  {mat.name},{mat.line_count},{index_flag}")

    return "\n".join(lines)
