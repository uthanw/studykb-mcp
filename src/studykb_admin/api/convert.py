"""Convert API - MinerU document conversion endpoints."""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from studykb_init.config import load_config, ensure_mineru_configured
from studykb_init.services.mineru_service import MineruService, ConversionResult

router = APIRouter()

# Store conversion task status (in production, use Redis or database)
conversion_tasks: dict[str, dict] = {}


class ConversionStatus(BaseModel):
    """Conversion task status."""
    task_id: str
    status: str  # pending, uploading, processing, downloading, completed, failed
    progress: int  # 0-100
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None


async def run_conversion(
    task_id: str,
    file_path: Path,
    category: str,
    output_filename: str,
    import_after: bool,
    session_id: Optional[str] = None,
):
    """Background task to run conversion with WebSocket progress."""
    from .tasks import send_to_session

    settings = load_config()
    service = MineruService(settings.mineru)

    output_dir = settings.kb_path / category

    async def send_ws(msg_type: str, content: str, **kwargs):
        """Send message via WebSocket if session_id provided."""
        if session_id:
            msg = {"type": msg_type, "content": content, **kwargs}
            await send_to_session(session_id, msg)

    def on_progress(status: str, message: str, progress: int):
        """Progress callback - update task status and send WebSocket."""
        conversion_tasks[task_id].update({
            "status": status,
            "message": message,
            "progress": progress,
        })
        # Send via WebSocket (fire and forget)
        if session_id:
            asyncio.create_task(send_ws("log", message))

    try:
        # Step 1: Request upload URL
        await send_ws("log", f"[转换] 开始转换: {file_path.name}")
        await send_ws("status", "申请上传链接...", active=True)
        on_progress("uploading", "申请上传链接...", 10)

        batch_id, upload_url = await service._request_upload_url(file_path.name)
        await send_ws("log", f"[转换] 获取上传链接成功, batch_id: {batch_id[:8]}...")

        # Step 2: Upload file
        await send_ws("status", "上传文件到 MinerU...", active=True)
        on_progress("uploading", "上传文件...", 20)

        file_size = file_path.stat().st_size / 1024 / 1024  # MB
        await send_ws("log", f"[转换] 上传文件 ({file_size:.1f} MB)...")
        await service._upload_file(file_path, upload_url)
        await send_ws("log", "[转换] 文件上传完成")

        # Step 3: Poll for completion with detailed progress
        await send_ws("status", "等待 MinerU 解析...", active=True)
        on_progress("processing", "等待解析...", 30)

        async def ws_progress_callback(msg: str):
            """Callback for detailed progress updates."""
            await send_ws("log", f"[转换] {msg}")
            # Update progress based on message
            if "解析中" in msg:
                on_progress("processing", msg, 50)
            elif "格式转换" in msg:
                on_progress("processing", msg, 70)
            elif "排队" in msg:
                on_progress("processing", msg, 35)

        download_url = await service._poll_status_with_ws(
            batch_id, file_path.name, ws_progress_callback
        )

        if not download_url:
            raise Exception("解析超时或失败")

        # Step 4: Download and extract result
        await send_ws("status", "下载转换结果...", active=True)
        on_progress("downloading", "下载结果...", 80)
        await send_ws("log", "[转换] 下载转换结果...")

        output_path = await service._download_result(
            download_url, file_path.stem, output_dir
        )
        await send_ws("log", f"[转换] 结果已保存: {output_path.name}")

        # Rename output file if needed
        if output_filename:
            final_name = output_filename if output_filename.endswith(".md") else f"{output_filename}.md"
            final_path = output_dir / final_name

            if final_path != output_path:
                output_path.rename(final_path)
                output_path = final_path
                await send_ws("log", f"[转换] 重命名为: {final_name}")

        # Count lines
        line_count = len(output_path.read_text(encoding="utf-8").splitlines())
        has_images = (output_dir / "images").exists()

        conversion_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "转换完成",
            "result": {
                "output_path": str(output_path),
                "line_count": line_count,
                "has_images": has_images,
            },
        })

        await send_ws("log", f"[转换] 完成! 共 {line_count} 行")
        await send_ws("complete", f"转换完成: {output_path.name}", success=True)

    except Exception as e:
        error_msg = str(e)
        conversion_tasks[task_id].update({
            "status": "failed",
            "message": f"转换失败: {error_msg}",
            "error": error_msg,
        })
        await send_ws("error", f"转换失败: {error_msg}")

    finally:
        # Clean up temp file
        if file_path.exists():
            file_path.unlink(missing_ok=True)


@router.get("/status/{task_id}")
async def get_conversion_status(task_id: str):
    """Get conversion task status."""
    if task_id not in conversion_tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    return conversion_tasks[task_id]


@router.post("/upload")
async def start_conversion(
    background_tasks: BackgroundTasks,
    category: str = Form(...),
    file: UploadFile = File(...),
    output_filename: Optional[str] = Form(None),
    import_after: bool = Form(True),
):
    """Upload a file and start conversion."""
    settings = load_config()

    # Check MinerU configuration
    if not ensure_mineru_configured(settings):
        raise HTTPException(status_code=400, detail="MinerU API 未配置，请先配置 API Token")

    # Check category exists
    category_path = settings.kb_path / category
    if not category_path.exists():
        raise HTTPException(status_code=404, detail=f"分类 '{category}' 不存在")

    # Validate file type
    allowed_extensions = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，支持: {', '.join(allowed_extensions)}"
        )

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

    # Start background conversion
    background_tasks.add_task(
        run_conversion,
        task_id=task_id,
        file_path=temp_path,
        category=category,
        output_filename=output_filename or Path(file.filename).stem,
        import_after=import_after,
    )

    return {"task_id": task_id, "message": "转换任务已启动"}


@router.get("/config")
async def get_mineru_config():
    """Get MinerU configuration status (not the token itself)."""
    settings = load_config()
    configured = ensure_mineru_configured(settings)

    return {
        "configured": configured,
        "api_base": settings.mineru.api_base,
        "model_version": settings.mineru.model_version,
    }


@router.post("/config")
async def update_mineru_config(
    api_token: str = Form(...),
    model_version: str = Form("vlm"),
):
    """Update MinerU API configuration."""
    from studykb_init.config import save_config, load_config

    settings = load_config()
    settings.mineru.api_token = api_token
    settings.mineru.model_version = model_version

    save_config(settings)

    return {"success": True, "message": "MinerU 配置已更新"}


@router.get("/tasks")
async def list_conversion_tasks():
    """List all conversion tasks."""
    return {
        "tasks": list(conversion_tasks.values()),
        "total": len(conversion_tasks),
    }


@router.delete("/tasks/{task_id}")
async def delete_conversion_task(task_id: str):
    """Delete a conversion task record."""
    if task_id not in conversion_tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    del conversion_tasks[task_id]
    return {"success": True, "message": f"任务 '{task_id}' 已删除"}
