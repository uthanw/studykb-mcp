"""Categories API - CRUD operations for knowledge base categories."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from studykb_mcp.services.kb_service import KBService

router = APIRouter()


class CategoryCreate(BaseModel):
    """Request body for creating a category."""
    name: str


class CategoryResponse(BaseModel):
    """Response for a single category."""
    name: str
    file_count: int
    materials: list[dict]


@router.get("")
async def list_categories():
    """Get all categories with their materials."""
    kb_service = KBService()
    categories = await kb_service.list_categories()

    return {
        "categories": [
            {
                "name": cat.name,
                "file_count": cat.file_count,
                "materials": [
                    {
                        "name": mat.name,
                        "line_count": mat.line_count,
                        "has_index": mat.has_index,
                    }
                    for mat in cat.materials
                ],
            }
            for cat in categories
        ]
    }


@router.post("")
async def create_category(body: CategoryCreate):
    """Create a new category."""
    from studykb_init.operations.category import create_category, category_exists

    if await category_exists(body.name):
        raise HTTPException(status_code=400, detail=f"Category '{body.name}' already exists")

    success, message = await create_category(body.name)
    if not success:
        raise HTTPException(status_code=500, detail=message)

    return {"success": True, "message": message, "name": body.name}


@router.delete("/{name}")
async def delete_category(name: str):
    """Delete a category and all its contents."""
    from studykb_init.config import load_config
    import shutil

    settings = load_config()
    category_path = settings.kb_path / name

    if not category_path.exists():
        raise HTTPException(status_code=404, detail=f"Category '{name}' not found")

    # Delete category directory
    shutil.rmtree(category_path)

    # Delete progress file if exists
    progress_file = settings.progress_path / f"{name}.json"
    if progress_file.exists():
        progress_file.unlink()

    return {"success": True, "message": f"Category '{name}' deleted"}


@router.get("/{name}")
async def get_category(name: str):
    """Get a single category with details."""
    kb_service = KBService()
    categories = await kb_service.list_categories()

    for cat in categories:
        if cat.name == name:
            return {
                "name": cat.name,
                "file_count": cat.file_count,
                "materials": [
                    {
                        "name": mat.name,
                        "line_count": mat.line_count,
                        "has_index": mat.has_index,
                    }
                    for mat in cat.materials
                ],
            }

    raise HTTPException(status_code=404, detail=f"Category '{name}' not found")
