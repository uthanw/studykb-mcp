"""Workspace tools - MCP tool handlers for workspace file operations."""

from typing import Any

from ..services.workspace_service import WorkspaceService


async def read_workspace_file_handler(arguments: dict[str, Any]) -> str:
    """Handle read_workspace_file tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Progress node ID (required)
            - file_path (str): File path within workspace (default "note.md")
            - start_line (int): Start line number (optional)
            - end_line (int): End line number (optional)

    Returns:
        Formatted file content or error message
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]
    file_path: str = arguments.get("file_path", "note.md")
    start_line: int | None = arguments.get("start_line")
    end_line: int | None = arguments.get("end_line")

    service = WorkspaceService()

    try:
        lines, truncated = await service.read_file(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
        )
    except FileNotFoundError as e:
        return f"❌ {e}"
    except ValueError as e:
        return f"❌ {e}"

    # Format output
    result = f"📄 {category}/{progress_id}/{file_path}\n"

    if lines:
        result += f"行 {lines[0][0]}-{lines[-1][0]}\n"
        result += "─" * 40 + "\n"
        for line_num, line_content in lines:
            result += f"{line_num:4d}│ {line_content}\n"
    else:
        result += "(空文件)\n"

    if truncated:
        result += f"\n⚠️ 内容已截断，最多显示 {len(lines)} 行"

    return result


async def write_workspace_file_handler(arguments: dict[str, Any]) -> str:
    """Handle write_workspace_file tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Progress node ID (required)
            - content (str): File content (required)
            - file_path (str): File path within workspace (default "note.md")

    Returns:
        Success message or error
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]
    content: str = arguments["content"]
    file_path: str = arguments.get("file_path", "note.md")

    service = WorkspaceService()

    try:
        await service.write_file(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
            content=content,
        )
    except ValueError as e:
        return f"❌ {e}"

    line_count = content.count("\n") + 1 if content else 0
    return f"✅ 已写入 {category}/{progress_id}/{file_path} ({line_count} 行)"


async def edit_workspace_file_handler(arguments: dict[str, Any]) -> str:
    """Handle edit_workspace_file tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Progress node ID (required)
            - old_string (str): String to search for (required)
            - new_string (str): Replacement string (required)
            - file_path (str): File path within workspace (default "note.md")
            - expected_replacements (int): Expected match count (default 1)

    Returns:
        Success message with match type or error
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]
    old_string: str = arguments["old_string"]
    new_string: str = arguments["new_string"]
    file_path: str = arguments.get("file_path", "note.md")
    expected_replacements: int = arguments.get("expected_replacements", 1)

    service = WorkspaceService()

    try:
        result = await service.edit_file(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
            old_string=old_string,
            new_string=new_string,
            expected_replacements=expected_replacements,
        )
    except FileNotFoundError as e:
        return f"❌ {e}"
    except ValueError as e:
        return f"❌ {e}"

    if result.success:
        match_type_labels = {
            "exact": "精确匹配",
            "whitespace_flexible": "空白符容错匹配",
            "token": "Token 匹配",
        }
        match_label = match_type_labels.get(result.match_type or "", result.match_type)
        return f"✅ 已编辑 {category}/{progress_id}/{file_path} (匹配方式: {match_label})"
    else:
        return f"❌ 编辑失败\n{result.error}"


async def delete_workspace_file_handler(arguments: dict[str, Any]) -> str:
    """Handle delete_workspace_file tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Progress node ID (required)
            - file_path (str): File path to delete (required)

    Returns:
        Success message or error
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]
    file_path: str = arguments["file_path"]

    service = WorkspaceService()

    try:
        await service.delete_file(
            category=category,
            progress_id=progress_id,
            file_path=file_path,
        )
    except FileNotFoundError as e:
        return f"❌ {e}"
    except ValueError as e:
        return f"❌ {e}"
    except IsADirectoryError as e:
        return f"❌ {e}"

    return f"✅ 已删除 {category}/{progress_id}/{file_path}"


async def list_workspace_handler(arguments: dict[str, Any]) -> str:
    """Handle list_workspace tool call.

    Args:
        arguments: Tool arguments
            - category (str): Category name (required)
            - progress_id (str): Progress node ID (required)

    Returns:
        Formatted file list or empty message
    """
    category: str = arguments["category"]
    progress_id: str = arguments["progress_id"]

    service = WorkspaceService()

    files = await service.list_files(
        category=category,
        progress_id=progress_id,
    )

    if not files:
        return f"📁 {category}/{progress_id}/\n(工作区为空或不存在)"

    result = f"📁 {category}/{progress_id}/\n"
    result += "─" * 40 + "\n"

    total_size = 0
    for file_info in files:
        path = file_info["path"]
        size = file_info["size"]
        total_size += size

        # Format size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / 1024 / 1024:.1f} MB"

        result += f"  {path:<30} {size_str:>10}\n"

    result += "─" * 40 + "\n"
    result += f"共 {len(files)} 个文件"

    return result
