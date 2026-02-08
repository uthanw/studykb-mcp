"""File import operations."""

import shutil
from pathlib import Path
from typing import Optional

from ..config import load_config


def _get_kb_path() -> Path:
    """Get knowledge base path from config."""
    settings = load_config()
    return settings.kb_path


async def import_file(
    source_path: Path,
    category: str,
    new_name: Optional[str] = None,
    overwrite: bool = False,
) -> tuple[bool, str, Optional[dict]]:
    """Import a Markdown file into the knowledge base.

    Args:
        source_path: Path to the source file.
        category: Target category name.
        new_name: Optional new name for the file (without extension).
        overwrite: Whether to overwrite existing file.

    Returns:
        Tuple of (success, message, file_info).
        file_info contains name, line_count, path if successful.
    """
    # Validate source file
    if not source_path.exists():
        return False, f"源文件不存在: {source_path}", None

    if not source_path.is_file():
        return False, f"路径不是文件: {source_path}", None

    if source_path.suffix.lower() != ".md":
        return False, "只支持导入 .md 文件", None

    # Validate category
    kb_path = _get_kb_path()
    category_path = kb_path / category
    if not category_path.exists():
        return False, f"分类 '{category}' 不存在", None

    # Determine target file name
    if new_name:
        target_name = new_name.strip()
        if not target_name:
            return False, "文件名不能为空", None
    else:
        target_name = source_path.stem

    # Ensure .md extension
    target_path = category_path / f"{target_name}.md"

    # Check for existing file
    if target_path.exists() and not overwrite:
        return False, f"文件 '{target_name}.md' 已存在于分类 '{category}'", None

    try:
        # Copy file
        shutil.copy2(source_path, target_path)

        # Count lines
        with open(target_path, "r", encoding="utf-8") as f:
            line_count = sum(1 for _ in f)

        file_info = {
            "name": target_name,
            "line_count": line_count,
            "path": str(target_path),
        }

        return True, f"文件 '{target_name}.md' 已导入到 '{category}/'", file_info

    except Exception as e:
        return False, f"导入文件失败: {e}", None


async def save_index(
    category: str,
    material: str,
    index_content: str,
    overwrite: bool = False,
) -> tuple[bool, str]:
    """Save an index file for a material.

    Args:
        category: Category name.
        material: Material name (with or without .md extension).
        index_content: Index content to save.
        overwrite: Whether to overwrite existing index.

    Returns:
        Tuple of (success, message).
    """
    kb_path = _get_kb_path()
    category_path = kb_path / category
    if not category_path.exists():
        return False, f"分类 '{category}' 不存在"

    # Handle both with and without .md extension
    if material.endswith(".md"):
        material = material[:-3]

    material_path = category_path / f"{material}.md"
    if not material_path.exists():
        return False, f"资料 '{material}' 不存在"

    index_path = category_path / f"{material}_index.csv"

    # 检查 CSV 和旧 MD 索引是否已存在
    old_md_index = category_path / f"{material}_index.md"
    existing = index_path.exists() or old_md_index.exists()
    if existing and not overwrite:
        return False, f"索引文件已存在: {index_path}"

    try:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)

        return True, f"索引已保存: {index_path}"
    except Exception as e:
        return False, f"保存索引失败: {e}"


async def read_index(category: str, material: str) -> Optional[str]:
    """Read an index file for a material.

    Args:
        category: Category name.
        material: Material name (without extension).

    Returns:
        Index content if exists, None otherwise.
    """
    kb_path = _get_kb_path()

    # CSV 优先
    csv_path = kb_path / category / f"{material}_index.csv"
    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    # MD 回退
    md_path = kb_path / category / f"{material}_index.md"
    if not md_path.exists():
        return None

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


async def get_file_info(category: str, material: str) -> Optional[dict]:
    """Get information about a material file.

    Args:
        category: Category name.
        material: Material name (with or without .md extension).

    Returns:
        Dict with name, line_count, has_index, path if exists, None otherwise.
    """
    kb_path = _get_kb_path()

    # Handle both with and without .md extension
    if material.endswith(".md"):
        material = material[:-3]

    file_path = kb_path / category / f"{material}.md"

    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            line_count = sum(1 for _ in f)

        index_csv = kb_path / category / f"{material}_index.csv"
        index_md = kb_path / category / f"{material}_index.md"

        return {
            "name": material,
            "line_count": line_count,
            "has_index": index_csv.exists() or index_md.exists(),
            "path": str(file_path),
        }
    except Exception:
        return None
