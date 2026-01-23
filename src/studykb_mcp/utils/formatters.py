"""TUI-style output formatters for MCP tool responses."""

from datetime import datetime

from ..models.kb import Category
from ..models.progress import ProgressEntry, ProgressFile, ProgressStatus
from ..services.kb_service import GrepResult
from ..services.review_service import ReviewService
from .datetime_utils import format_date_short, format_overdue, format_relative_time


def format_overview(categories: list[Category]) -> str:
    """Format knowledge base overview for display.

    Args:
        categories: List of categories

    Returns:
        Formatted TUI-style string
    """
    if not categories:
        return "# Knowledge Base Overview\n\nNo categories found.\nCreate a directory in kb/ to get started."

    lines = ["# Knowledge Base Overview", ""]

    for cat in categories:
        lines.append(f"{cat.name}/ ({cat.file_count} files)")
        for i, mat in enumerate(cat.materials):
            prefix = "└" if i == len(cat.materials) - 1 else "├"
            idx_tag = " [IDX]" if mat.has_index else ""
            lines.append(f"  {prefix} {mat.name:<20} {mat.line_count:>6} ln{idx_tag}")
        lines.append("")

    total_files = sum(c.file_count for c in categories)
    lines.append("---")
    lines.append(f"{len(categories)} categories, {total_files} files")
    lines.append("[IDX] = index available")

    return "\n".join(lines)


def format_progress(
    progress: ProgressFile,
    status_filter: list[ProgressStatus] | None = None,
    limit: int = 20,
) -> str:
    """Format progress data for display.

    Args:
        progress: Progress file data
        status_filter: Applied status filter (for header display)
        limit: Applied limit (for footer display)

    Returns:
        Formatted TUI-style string
    """
    review_service = ReviewService()

    # Header
    filter_info = ""
    if status_filter:
        filter_info = f" [filter: {', '.join(status_filter)}]"
    lines = [f"# Progress: {progress.category}{filter_info}", ""]

    # Stats
    stats = progress.get_stats()
    lines.append(
        f"done: {stats['done']} | active: {stats['active']} | "
        f"review: {stats['review']} | pending: {stats['pending']} | total: {stats['total']}"
    )

    # Progress bar
    if stats["total"] > 0:
        done_pct = (stats["done"] + stats["review"]) / stats["total"]
        bar_len = 30
        filled = int(bar_len * done_pct)
        bar = "=" * filled + "." * (bar_len - filled)
        lines.append(f"[{bar}] {int(done_pct * 100)}%")
    lines.append("")

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

    # Format each section
    status_info = {
        "active": ("🔥", "active"),
        "review": ("🔄", "review"),
        "done": ("✅", "done"),
        "pending": ("📋", "pending"),
    }

    for status, (emoji, label) in status_info.items():
        entries = by_status[status]
        if not entries:
            continue

        count = len(entries)
        shown = entries[:limit] if limit > 0 else entries
        more = count - len(shown)

        if more > 0:
            lines.append(f"## {emoji} {label} (showing {len(shown)}, +{more} more)")
        else:
            lines.append(f"## {emoji} {label} ({count})")
        lines.append("")

        for entry_id, entry in shown:
            # Main line
            if status == "review" and entry.next_review_at:
                overdue = review_service.get_overdue_days(entry.next_review_at)
                overdue_str = format_overdue(overdue)
                lines.append(f"{entry_id} | {entry.name} | {overdue_str}")
            elif status == "done":
                date_str = format_date_short(entry.updated_at)
                lines.append(f"{entry_id:<35} | {entry.name:<15} | {date_str}")
            else:
                lines.append(f"{entry_id} | {entry.name}")

            # Comment line (for active and review)
            if status in ("active", "review") and entry.comment:
                lines.append(f'  "{entry.comment}"')

            # Additional info
            if status == "active":
                lines.append(f"  updated: {format_relative_time(entry.updated_at)}")
            elif status == "review":
                lines.append(f"  reviewed {entry.review_count}x")

            if status in ("active", "review"):
                lines.append("")

    # Footer
    lines.append("---")
    if limit > 0:
        lines.append(f"Showing up to {limit} per group. Use limit=-1 to fetch all.")

    return "\n".join(lines)


def format_progress_update(
    category: str,
    progress_id: str,
    entry: ProgressEntry,
    is_new: bool,
    old_status: ProgressStatus | None = None,
) -> str:
    """Format progress update confirmation.

    Args:
        category: Category name
        progress_id: Progress ID
        entry: Updated entry
        is_new: Whether this was a new entry
        old_status: Previous status (if updating)

    Returns:
        Formatted confirmation string
    """
    review_service = ReviewService()

    if is_new:
        lines = [
            "✨ Progress created",
            "",
            f"{category} / {progress_id}",
            f"{entry.name} [NEW]",
            "",
            f"  status: {entry.status}",
        ]
    else:
        lines = [
            "✅ Progress updated",
            "",
            f"{category} / {progress_id}",
            entry.name,
            "",
            f"  {old_status} → {entry.status}",
        ]

    if entry.comment:
        lines.append(f'  "{entry.comment}"')

    if entry.status == "done" and entry.next_review_at:
        days = (entry.next_review_at - datetime.now()).days
        lines.append("")
        lines.append(f"next review: {format_date_short(entry.next_review_at)} ({days}d)")

    return "\n".join(lines)


def format_read_file(
    category: str,
    material: str,
    start_line: int,
    end_line: int,
    lines: list[tuple[int, str]],
    truncated: bool,
) -> str:
    """Format file content for display.

    Args:
        category: Category name
        material: Material name
        start_line: Requested start line
        end_line: Requested end line
        lines: List of (line_number, content) tuples
        truncated: Whether content was truncated

    Returns:
        Formatted file content
    """
    header = f"# {category}/{material} L{start_line}-{end_line}"
    if truncated:
        header += " (truncated)"

    content_lines = [header, ""]

    for line_num, text in lines:
        content_lines.append(f"{line_num:5} | {text}")

    if truncated:
        content_lines.append("")
        content_lines.append("⚠️ Content truncated. Request a smaller range.")

    return "\n".join(content_lines)


def format_grep_results(
    category: str,
    pattern: str,
    material: str | None,
    results: list[GrepResult],
    max_matches: int,
) -> str:
    """Format grep search results.

    Args:
        category: Category name
        pattern: Search pattern
        material: Material name (if single file search)
        results: List of grep results
        max_matches: Maximum matches requested

    Returns:
        Formatted search results
    """
    total_matches = sum(r.total_matches for r in results)

    # Header
    if material:
        header = f'# grep "{pattern}" in {category}/{material}'
    else:
        header = f'# grep "{pattern}" in {category}/*'

    lines = [header]

    if total_matches == 0:
        lines.append("0 matches")
        lines.append("")
        lines.append("Try different keywords or search in other categories.")
        return "\n".join(lines)

    lines.append(f"{total_matches} matches")
    lines.append("")

    # Results
    for result in results:
        if not material:
            # Multi-file search: show file header
            lines.append(f"-- {result.material} ({result.total_matches}) --")
            lines.append("")

        for match in result.matches:
            lines.append(f"[L{match.line_num}]")
            for ctx in match.context:
                line_num = ctx["line_num"]
                text = ctx["text"]
                is_match = ctx["is_match"]
                prefix = ">" if is_match else " "
                lines.append(f"{prefix} {line_num:5} | {text}")
            lines.append("")

    return "\n".join(lines)


def format_index_not_found(category: str, material: str) -> str:
    """Format index not found error.

    Args:
        category: Category name
        material: Material name

    Returns:
        Formatted error message
    """
    return f"""⚠️ Index not found: {category}/{material}

No index file available for this material.
Use `grep` to search or `read_file` with estimated ranges."""
