"""TOON-style output formatters for MCP tool responses.

TOON format optimizes token usage by:
- Declaring field names once in header: `items[N]{field1,field2}:`
- Data rows contain only values, comma-separated
- Explicit [N] length for validation
"""

from datetime import datetime

from ..models.kb import Category
from ..models.progress import ProgressEntry, ProgressFile, ProgressStatus, RelatedSection
from ..services.kb_service import GrepResult
from ..services.review_service import ReviewService


def _escape_value(value: str) -> str:
    """Escape special characters in TOON values."""
    if not value:
        return ""
    # Escape commas and newlines in values
    value = value.replace("\\", "\\\\")
    value = value.replace(",", "\\,")
    value = value.replace("\n", "\\n")
    return value


def _format_date(dt: datetime | None, with_time: bool = True) -> str:
    """Format datetime compactly."""
    if not dt:
        return "-"
    if with_time:
        return dt.strftime("%m-%d %H:%M")
    return dt.strftime("%m-%d")


def _format_sections(sections: list[RelatedSection]) -> str:
    """Format related sections compactly.

    Format: material:start-end|material:start-end
    Example: 图论.md:150-220|图论.md:450-480
    """
    if not sections:
        return "-"
    parts = []
    for sec in sections:
        parts.append(f"{sec.material}:{sec.start_line}-{sec.end_line}")
    return "|".join(parts)


def format_overview(categories: list[Category]) -> str:
    """Format knowledge base overview in TOON style.

    Args:
        categories: List of categories

    Returns:
        TOON formatted string
    """
    if not categories:
        return "# overview\nstatus: empty\nmessage: No categories found. Create a directory in kb/ to get started."

    total_files = sum(c.file_count for c in categories)
    lines = [
        "# overview",
        f"total: {len(categories)} categories, {total_files} files",
        "",
    ]

    # Categories with materials
    for cat in categories:
        lines.append(f"## {cat.name}")
        if cat.materials:
            lines.append(f"materials[{len(cat.materials)}]{{filename,lines,has_index}}:")
            for mat in cat.materials:
                index_flag = "Y" if mat.has_index else "N"
                lines.append(f"  {mat.name},{mat.line_count},{index_flag}")
        else:
            lines.append("  (no materials)")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_progress(
    progress: ProgressFile,
    status_filter: list[ProgressStatus] | None = None,
    show_time: bool = False,
) -> str:
    """Format progress data in TOON style.

    Args:
        progress: Progress file data
        status_filter: Applied status filter
        show_time: Whether to include time info (updated_at, due date, etc.)

    Returns:
        TOON formatted string
    """
    review_service = ReviewService()
    stats = progress.get_stats()

    # Group entries by status
    by_status: dict[str, list[tuple[str, ProgressEntry]]] = {
        "active": [],
        "review": [],
        "done": [],
        "pending": [],
    }

    for entry_id, entry in progress.entries.items():
        by_status[entry.status].append((entry_id, entry))

    # Sort each group by updated_at descending
    for status in by_status:
        by_status[status].sort(key=lambda x: x[1].updated_at, reverse=True)

    # Build output
    lines = [
        f"# progress: {progress.category}",
        f"stats: active={stats['active']},review={stats['review']},done={stats['done']},pending={stats['pending']}",
    ]

    if status_filter:
        lines.append(f"filter: {','.join(status_filter)}")

    # Active entries
    if by_status["active"]:
        lines.append("")
        if show_time:
            lines.append(f"active[{len(by_status['active'])}]{{id,name,updated,comment,sections}}:")
            for entry_id, entry in by_status["active"]:
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{_format_date(entry.updated_at)},{comment},{sections}")
        else:
            lines.append(f"active[{len(by_status['active'])}]{{id,name,comment,sections}}:")
            for entry_id, entry in by_status["active"]:
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{comment},{sections}")

    # Review entries (with overdue info)
    if by_status["review"]:
        lines.append("")
        if show_time:
            lines.append(f"review[{len(by_status['review'])}]{{id,name,due,overdue,comment,sections}}:")
            for entry_id, entry in by_status["review"]:
                due = _format_date(entry.next_review_at, with_time=False) if entry.next_review_at else "-"
                overdue = review_service.get_overdue_days(entry.next_review_at) if entry.next_review_at else 0
                overdue_str = f"{overdue}d" if overdue > 0 else "-"
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{due},{overdue_str},{comment},{sections}")
        else:
            lines.append(f"review[{len(by_status['review'])}]{{id,name,comment,sections}}:")
            for entry_id, entry in by_status["review"]:
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{comment},{sections}")

    # Done entries
    if by_status["done"]:
        lines.append("")
        if show_time:
            lines.append(f"done[{len(by_status['done'])}]{{id,name,mastered,next_review,comment,sections}}:")
            for entry_id, entry in by_status["done"]:
                mastered = _format_date(entry.mastered_at, with_time=False) if entry.mastered_at else "-"
                next_rev = _format_date(entry.next_review_at, with_time=False) if entry.next_review_at else "-"
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{mastered},{next_rev},{comment},{sections}")
        else:
            lines.append(f"done[{len(by_status['done'])}]{{id,name,comment,sections}}:")
            for entry_id, entry in by_status["done"]:
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{comment},{sections}")

    # Pending entries
    if by_status["pending"]:
        lines.append("")
        if show_time:
            lines.append(f"pending[{len(by_status['pending'])}]{{id,name,updated,comment,sections}}:")
            for entry_id, entry in by_status["pending"]:
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{_format_date(entry.updated_at)},{comment},{sections}")
        else:
            lines.append(f"pending[{len(by_status['pending'])}]{{id,name,comment,sections}}:")
            for entry_id, entry in by_status["pending"]:
                comment = _escape_value(entry.comment) if entry.comment else ""
                sections = _format_sections(entry.related_sections)
                lines.append(f"  {entry_id},{_escape_value(entry.name)},{comment},{sections}")

    return "\n".join(lines)


def format_progress_update(
    category: str,
    progress_id: str,
    entry: ProgressEntry,
    is_new: bool,
    old_status: ProgressStatus | None = None,
) -> str:
    """Format progress update confirmation in TOON style.

    Args:
        category: Category name
        progress_id: Progress ID
        entry: Updated entry
        is_new: Whether this was a new entry
        old_status: Previous status (if updating)

    Returns:
        TOON formatted string
    """
    action = "created" if is_new else "updated"
    lines = [
        f"# {action}: {category}/{progress_id}",
        f"name: {entry.name}",
        f"status: {entry.status}",
    ]

    if not is_new and old_status and old_status != entry.status:
        lines.append(f"old_status: {old_status}")

    if entry.comment:
        lines.append(f"comment: {_escape_value(entry.comment)}")

    lines.append(f"review_count: {entry.review_count}")

    if entry.next_review_at:
        days = (entry.next_review_at - datetime.now()).days
        lines.append(f"next_review: {_format_date(entry.next_review_at, with_time=False)} ({days}d)")

    # Show related sections count in update confirmation
    if entry.related_sections:
        lines.append(f"related_sections: {len(entry.related_sections)}")

    return "\n".join(lines)


def format_progress_detail(
    category: str,
    progress_id: str,
    entry: ProgressEntry,
) -> str:
    """Format single progress entry detail in TOON style.

    Args:
        category: Category name
        progress_id: Progress ID
        entry: Progress entry

    Returns:
        TOON formatted string with full detail including related_sections
    """
    lines = [
        f"# detail: {category}/{progress_id}",
        f"name: {entry.name}",
        f"status: {entry.status}",
        f"updated: {_format_date(entry.updated_at)}",
    ]

    if entry.comment:
        lines.append(f"comment: {_escape_value(entry.comment)}")

    if entry.mastered_at:
        lines.append(f"mastered: {_format_date(entry.mastered_at, with_time=False)}")

    lines.append(f"review_count: {entry.review_count}")

    if entry.next_review_at:
        days = (entry.next_review_at - datetime.now()).days
        lines.append(f"next_review: {_format_date(entry.next_review_at, with_time=False)} ({days}d)")

    # Related sections
    if entry.related_sections:
        lines.append("")
        lines.append(f"related_sections[{len(entry.related_sections)}]{{material,range,desc}}:")
        for sec in entry.related_sections:
            desc = _escape_value(sec.desc) if sec.desc else ""
            lines.append(f"  {sec.material},{sec.start_line}-{sec.end_line},{desc}")
    else:
        lines.append("")
        lines.append("related_sections: (none)")

    return "\n".join(lines)


def format_read_file(
    category: str,
    material: str,
    start_line: int,
    end_line: int,
    lines: list[tuple[int, str]],
    truncated: bool,
) -> str:
    """Format file content in TOON style.

    Args:
        category: Category name
        material: Material name
        start_line: Requested start line
        end_line: Requested end line
        lines: List of (line_number, content) tuples
        truncated: Whether content was truncated

    Returns:
        TOON formatted string
    """
    output_lines = [
        f"# file: {category}/{material}",
        f"range: {start_line}-{end_line} ({len(lines)} lines)",
    ]

    if truncated:
        output_lines.append("warning: Content truncated. Request a smaller range.")

    output_lines.append("")
    output_lines.append("```")
    for line_num, text in lines:
        output_lines.append(f"{line_num:>5}| {text}")
    output_lines.append("```")

    return "\n".join(output_lines)


def format_grep_results(
    category: str,
    pattern: str,
    material: str | None,
    results: list[GrepResult],
    max_matches: int,
) -> str:
    """Format grep search results in TOON style.

    Args:
        category: Category name
        pattern: Search pattern
        material: Material name (if single file search)
        results: List of grep results
        max_matches: Maximum matches requested

    Returns:
        TOON formatted string
    """
    total_matches = sum(r.total_matches for r in results)

    lines = [
        f"# grep: {category}" + (f"/{material}" if material else ""),
        f"pattern: {pattern}",
        f"matches: {total_matches} (max: {max_matches})",
    ]

    for r in results:
        if not r.matches:
            continue

        lines.append("")
        lines.append(f"## {r.material} ({r.total_matches} matches)")

        for match in r.matches:
            lines.append("")
            for ctx in match.context:
                marker = ">" if ctx["is_match"] else " "
                lines.append(f"{ctx['line_num']:>5}{marker}| {ctx['text']}")

    if not results or total_matches == 0:
        lines.append("")
        lines.append("(no matches found)")

    return "\n".join(lines)


def format_index_not_found(category: str, material: str, available_files: list[str]) -> str:
    """Format index not found error in TOON style.

    Args:
        category: Category name
        material: Material name
        available_files: List of available material files in the category

    Returns:
        TOON formatted string
    """
    lines = [
        "# error: index_not_found",
        f"file: {category}/{material}",
        f"message: 该资料没有索引文件",
        f"suggestion: 使用 grep 搜索或 read_file 读取指定行范围",
    ]

    if available_files:
        # Show files with index
        with_index = [f for f in available_files if f.endswith(" [IDX]")]
        without_index = [f for f in available_files if not f.endswith(" [IDX]")]

        lines.append("")
        lines.append(f"available_files[{len(available_files)}]:")
        for f in with_index:
            lines.append(f"  {f}")
        for f in without_index:
            lines.append(f"  {f}")

    return "\n".join(lines)


def format_file_not_found(category: str, material: str, available_files: list[str]) -> str:
    """Format file not found error in TOON style.

    Args:
        category: Category name
        material: Material name
        available_files: List of available material files in the category

    Returns:
        TOON formatted string
    """
    lines = [
        "# error: file_not_found",
        f"file: {category}/{material}",
        f"message: 文件不存在",
    ]

    if available_files:
        # Show files with index first
        with_index = [f for f in available_files if f.endswith(" [IDX]")]
        without_index = [f for f in available_files if not f.endswith(" [IDX]")]

        lines.append("")
        lines.append(f"available_files[{len(available_files)}]:")
        for f in with_index:
            lines.append(f"  {f}")
        for f in without_index:
            lines.append(f"  {f}")

    return "\n".join(lines)
