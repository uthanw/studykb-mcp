"""Materials API - CRUD operations for material files."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from studykb_init.config import load_config, ensure_mineru_configured
from studykb_init.operations.import_file import get_file_info, import_file

router = APIRouter()

# Supported file extensions for MinerU conversion
MINERU_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}

# Store conversion task status (shared with convert.py)
from .convert import conversion_tasks, run_conversion


class MaterialResponse(BaseModel):
    """Response for a material file."""
    name: str
    line_count: int
    has_index: bool
    path: str


@router.get("/{category}")
async def list_materials(category: str):
    """Get all materials in a category."""
    from studykb_init.operations.category import get_category_materials

    materials = await get_category_materials(category)
    return {"category": category, "materials": materials}


@router.get("/{category}/{material}")
async def get_material(category: str, material: str):
    """Get material file info."""
    info = await get_file_info(category, material)
    if not info:
        raise HTTPException(status_code=404, detail=f"Material '{material}' not found")
    return info


@router.post("/{category}/upload")
async def upload_material(
    background_tasks: BackgroundTasks,
    category: str,
    file: UploadFile = File(...),
    overwrite: bool = Form(False),
    session_id: Optional[str] = Form(None),
):
    """Upload a material file. Auto-detects file type:
    - .md files: Direct import
    - .pdf/.doc/.docx/.ppt/.pptx: MinerU conversion then import
    """
    settings = load_config()
    category_path = settings.kb_path / category

    if not category_path.exists():
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    file_ext = Path(file.filename).suffix.lower()

    # Direct MD import
    if file_ext == ".md":
        temp_path = Path("/tmp") / file.filename
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            success, message, file_info = await import_file(temp_path, category, overwrite=overwrite)
            if not success:
                raise HTTPException(status_code=400, detail=message)
            return {
                "success": True,
                "type": "direct",
                "message": message,
                "file": file_info,
            }
        finally:
            temp_path.unlink(missing_ok=True)

    # MinerU conversion for other supported formats
    elif file_ext in MINERU_EXTENSIONS:
        if not ensure_mineru_configured(settings):
            raise HTTPException(status_code=400, detail="MinerU API 未配置，请先在设置中配置 API Token")

        # Save uploaded file to temp location
        task_id = str(uuid.uuid4())[:8]
        temp_dir = Path("/tmp/studykb_convert")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / f"{task_id}_{file.filename}"

        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Initialize task status
        conversion_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "任务已创建，等待处理",
            "filename": file.filename,
            "category": category,
            "result": None,
            "error": None,
        }

        # Start background conversion with session_id for WebSocket progress
        background_tasks.add_task(
            run_conversion,
            task_id=task_id,
            file_path=temp_path,
            category=category,
            output_filename=Path(file.filename).stem,
            import_after=True,
            session_id=session_id,
        )

        return {
            "success": True,
            "type": "conversion",
            "task_id": task_id,
            "message": f"已启动转换任务: {file.filename}",
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}。支持: .md, .pdf, .doc, .docx, .ppt, .pptx"
        )


# Keep old endpoint for backward compatibility
@router.post("/{category}")
async def upload_material_legacy(
    background_tasks: BackgroundTasks,
    category: str,
    file: UploadFile = File(...),
    overwrite: bool = Form(False),
):
    """Legacy upload endpoint - redirects to new unified upload."""
    return await upload_material(background_tasks, category, file, overwrite)


@router.delete("/{category}/{material}")
async def delete_material(category: str, material: str):
    """Delete a material file and its index."""
    settings = load_config()
    category_path = settings.kb_path / category

    if not category_path.exists():
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")

    # Material file
    material_name = material if material.endswith(".md") else f"{material}.md"
    material_path = category_path / material_name

    if not material_path.exists():
        raise HTTPException(status_code=404, detail=f"Material '{material}' not found")

    # Delete material file
    material_path.unlink()

    # Delete index file if exists
    stem = material_path.stem
    index_path = category_path / f"{stem}_index.md"
    if index_path.exists():
        index_path.unlink()

    return {"success": True, "message": f"Material '{material}' deleted"}


@router.get("/{category}/{material}/content")
async def get_material_content(
    category: str,
    material: str,
    start_line: int = 1,
    end_line: int = 500,
):
    """Get material file content."""
    from studykb_mcp.services.kb_service import KBService

    kb_service = KBService()

    try:
        lines, truncated = await kb_service.read_file_range(
            category=category,
            material=material,
            start_line=start_line,
            end_line=end_line,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Material '{material}' not found")

    return {
        "category": category,
        "material": material,
        "start_line": start_line,
        "end_line": end_line,
        "lines": [{"num": num, "text": text} for num, text in lines],
        "truncated": truncated,
    }


@router.get("/{category}/{material}/index")
async def get_material_index(category: str, material: str):
    """Get material index content."""
    from studykb_mcp.services.kb_service import KBService

    kb_service = KBService()
    content = await kb_service.read_index(category, material)

    if content is None:
        raise HTTPException(status_code=404, detail=f"Index for '{material}' not found")

    return {"category": category, "material": material, "content": content}
