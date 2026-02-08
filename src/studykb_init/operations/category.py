"""Category management operations."""

from pathlib import Path

from ..config import load_config


def _get_kb_path() -> Path:
    """Get knowledge base path from config."""
    settings = load_config()
    return settings.kb_path


async def list_categories() -> list[str]:
    """List all existing categories in the knowledge base.

    Returns:
        List of category names.
    """
    kb_path = _get_kb_path()

    if not kb_path.exists():
        return []

    categories = []
    for item in kb_path.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            categories.append(item.name)

    return sorted(categories)


async def create_category(name: str) -> tuple[bool, str]:
    """Create a new category in the knowledge base.

    Args:
        name: Category name to create.

    Returns:
        Tuple of (success, message).
    """
    if not name or not name.strip():
        return False, "分类名称不能为空"

    name = name.strip()

    # Validate name
    invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    for char in invalid_chars:
        if char in name:
            return False, f"分类名称不能包含特殊字符: {char}"

    kb_path = _get_kb_path()
    category_path = kb_path / name

    if category_path.exists():
        return False, f"分类 '{name}' 已存在"

    try:
        # Ensure kb directory exists
        kb_path.mkdir(parents=True, exist_ok=True)

        # Create category directory
        category_path.mkdir()

        return True, f"分类 '{name}' 创建成功"
    except Exception as e:
        return False, f"创建分类失败: {e}"


async def category_exists(name: str) -> bool:
    """Check if a category exists.

    Args:
        name: Category name to check.

    Returns:
        True if category exists, False otherwise.
    """
    kb_path = _get_kb_path()
    category_path = kb_path / name
    return category_path.exists() and category_path.is_dir()


async def get_category_materials(category: str) -> list[dict]:
    """Get all materials in a category.

    Args:
        category: Category name.

    Returns:
        List of material info dicts with name, line_count, has_index.
    """
    kb_path = _get_kb_path()
    category_path = kb_path / category

    if not category_path.exists():
        return []

    materials = []
    for item in category_path.iterdir():
        if item.is_file() and item.suffix == ".md" and not item.name.endswith("_index.md"):
            material_name = item.stem

            # Count lines
            with open(item, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)

            # Check for index file (CSV or MD)
            index_csv = category_path / f"{material_name}_index.csv"
            index_md = category_path / f"{material_name}_index.md"
            has_index = index_csv.exists() or index_md.exists()

            materials.append(
                {
                    "name": material_name,
                    "line_count": line_count,
                    "has_index": has_index,
                }
            )

    return sorted(materials, key=lambda x: x["name"])
