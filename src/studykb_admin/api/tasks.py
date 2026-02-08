"""CLI API - Web-based CLI with real-time updates via WebSocket."""

import asyncio
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from studykb_init.config import load_config, ensure_api_configured, ensure_mineru_configured
from studykb_init.operations.category import (
    category_exists,
    create_category,
    get_category_materials,
    list_categories,
)
from studykb_init.operations.import_file import (
    get_file_info,
    import_file,
    read_index,
    save_index,
)

router = APIRouter()

# Store active CLI sessions
cli_sessions: dict[str, dict] = {}

# Store active background tasks for cancellation
active_tasks: dict[str, asyncio.Task] = {}


class CLIMessage(BaseModel):
    """Message structure for CLI WebSocket communication."""
    type: str  # log, status, progress, tool_call, result, error, complete
    content: Any
    timestamp: Optional[str] = None


class IndexRequest(BaseModel):
    """Request for index generation."""
    category: str
    material: str


class ProgressInitRequest(BaseModel):
    """Request for progress initialization."""
    category: str


class FullInitRequest(BaseModel):
    """Request for full initialization flow."""
    category: str
    material_path: Optional[str] = None
    new_category: bool = False


# Custom Console adapter for WebSocket output
class WebSocketConsole:
    """Console adapter that sends output to WebSocket.

    This class mimics the Rich Console interface but sends output via WebSocket.
    It provides compatibility with rich.live.Live by implementing required methods.
    """

    def __init__(self, send_func: Callable[[dict], Any]):
        self.send = send_func
        self._live = None
        # Properties needed by Rich Live
        self.is_terminal = False
        self.is_jupyter = False
        self.force_terminal = False
        self.force_interactive = False
        self.soft_wrap = False
        self.width = 120
        self.height = 40
        self.color_system = None
        self.encoding = "utf-8"
        self.record = False
        self._buffer = []
        self._lock = asyncio.Lock()
        # Token tracking (updated by agent)
        self._current_context_tokens = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def print(self, *args, **kwargs):
        """Send print output via WebSocket."""
        text = " ".join(str(a) for a in args)
        # Strip rich markup for simple text
        import re
        clean_text = re.sub(r'\[.*?\]', '', text)

        # Detect message type based on content patterns
        msg_type = "log"
        extra = {}

        # Tool call pattern: "  $ command" or "  → tool_name(...)"
        if clean_text.strip().startswith("$ "):
            msg_type = "tool_call"
            extra["command"] = clean_text.strip()[2:]
            extra["tokens"] = {
                "ctx": self._current_context_tokens,
                "input": self._total_input_tokens,
                "output": self._total_output_tokens,
            }
        elif clean_text.strip().startswith("→ "):
            msg_type = "tool_call"
            extra["tool"] = clean_text.strip()[2:]
            extra["tokens"] = {
                "ctx": self._current_context_tokens,
                "input": self._total_input_tokens,
                "output": self._total_output_tokens,
            }
        # Tool result pattern: starts with spaces (indented)
        elif clean_text.startswith("    "):
            msg_type = "tool_result"
        # Completion pattern
        elif "任务完成" in clean_text or "✓" in clean_text:
            msg_type = "complete"
            extra["success"] = True
        elif "警告" in clean_text or "失败" in clean_text:
            msg_type = "error"

        asyncio.create_task(self.send({
            "type": msg_type,
            "content": clean_text,
            **extra,
        }))

    def status(self, text: str):
        """Return a context manager for status display."""
        return WebSocketStatus(text, self.send)

    # Methods required by rich.live.Live
    def set_live(self, live):
        """Set the Live instance (required by Rich Live)."""
        self._live = live

    def clear_live(self):
        """Clear the Live instance (required by Rich Live)."""
        self._live = None

    def push_render_hook(self, hook):
        """Push a render hook (no-op for WebSocket)."""
        pass

    def pop_render_hook(self):
        """Pop a render hook (no-op for WebSocket)."""
        pass

    def begin_capture(self):
        """Begin capture (no-op for WebSocket)."""
        pass

    def end_capture(self):
        """End capture (no-op for WebSocket)."""
        return ""

    def bell(self):
        """Ring the bell (no-op for WebSocket)."""
        pass

    def control(self, *args, **kwargs):
        """Control sequence (no-op for WebSocket)."""
        pass

    def get_datetime(self):
        """Get current datetime."""
        from datetime import datetime
        return datetime.now()

    def line(self, count=1):
        """Print empty lines (no-op for WebSocket)."""
        pass

    def rule(self, *args, **kwargs):
        """Print a rule (no-op for WebSocket)."""
        pass

    def clear(self, home=True):
        """Clear the console (no-op for WebSocket)."""
        pass

    def show_cursor(self, show=True):
        """Show/hide cursor (no-op for WebSocket)."""
        pass

    @property
    def options(self):
        """Return console options (minimal implementation)."""
        from rich.console import ConsoleOptions
        return ConsoleOptions(
            size=(self.width, self.height),
            legacy_windows=False,
            min_width=1,
            max_width=self.width,
            is_terminal=False,
            encoding=self.encoding,
        )

    def render(self, renderable, options=None):
        """Render a renderable (minimal implementation)."""
        return []

    def render_lines(self, renderable, options=None, style=None, pad=True, new_lines=False):
        """Render lines (minimal implementation)."""
        return []

    def render_str(self, text, style=None, justify=None, overflow=None, emoji=None, markup=None, highlight=None, highlighter=None):
        """Render string (minimal implementation)."""
        return text

    def measure(self, renderable, options=None):
        """Measure a renderable (minimal implementation)."""
        from rich.measure import Measurement
        return Measurement(0, self.width)

    def size(self):
        """Return console size."""
        from rich.console import ConsoleDimensions
        return ConsoleDimensions(self.width, self.height)


class WebSocketStatus:
    """Context manager for status display via WebSocket."""

    def __init__(self, text: str, send_func: Callable):
        self.text = text
        self.send = send_func

    async def __aenter__(self):
        await self.send({"type": "status", "content": self.text, "active": True})
        return self

    async def __aexit__(self, *args):
        await self.send({"type": "status", "content": self.text, "active": False})

    def __enter__(self):
        asyncio.create_task(self.send({"type": "status", "content": self.text, "active": True}))
        return self

    def __exit__(self, *args):
        asyncio.create_task(self.send({"type": "status", "content": self.text, "active": False}))


@router.websocket("/ws/{session_id}")
async def cli_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for CLI session communication."""
    await websocket.accept()

    cli_sessions[session_id] = {
        "websocket": websocket,
        "active": True,
    }

    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming commands
            if data.get("type") == "cancel":
                cli_sessions[session_id]["active"] = False
                # Cancel the running background task
                task = active_tasks.get(session_id)
                if task and not task.done():
                    task.cancel()
                    await send_to_session(session_id, {
                        "type": "error",
                        "content": "任务已被用户中断",
                    })

    except WebSocketDisconnect:
        if session_id in cli_sessions:
            del cli_sessions[session_id]


async def send_to_session(session_id: str, message: dict):
    """Send message to a CLI session."""
    if session_id in cli_sessions:
        ws = cli_sessions[session_id]["websocket"]
        try:
            await ws.send_json(message)
        except Exception:
            pass


@router.get("/config/status")
async def get_config_status():
    """Get configuration status for all APIs."""
    settings = load_config()

    return {
        "llm": {
            "configured": ensure_api_configured(settings),
            "model": settings.llm.model,
            "base_url": settings.llm.base_url,
        },
        "mineru": {
            "configured": ensure_mineru_configured(settings),
            "model_version": settings.mineru.model_version,
        },
    }


@router.post("/cancel")
async def cancel_task(session_id: str):
    """Cancel a running background task for the given session."""
    task = active_tasks.get(session_id)
    if task and not task.done():
        task.cancel()
        await send_to_session(session_id, {
            "type": "error",
            "content": "任务已被用户中断",
        })
        return {"success": True, "message": "任务已中断"}
    return {"success": False, "message": "没有正在运行的任务"}


@router.get("/categories")
async def get_categories_for_cli():
    """Get categories with materials for CLI selection."""
    categories = await list_categories()

    result = []
    for cat in categories:
        materials = await get_category_materials(cat)
        result.append({
            "name": cat,
            "materials": materials,
        })

    return {"categories": result}


@router.post("/create-category")
async def cli_create_category(name: str):
    """Create a new category."""
    if await category_exists(name):
        raise HTTPException(status_code=400, detail=f"分类 '{name}' 已存在")

    success, message = await create_category(name)
    if not success:
        raise HTTPException(status_code=500, detail=message)

    return {"success": True, "message": message, "name": name}


@router.post("/generate-index")
async def generate_index(request: IndexRequest, session_id: str):
    """Generate index for a material file using IndexAgent."""
    settings = load_config()

    if not ensure_api_configured(settings):
        raise HTTPException(status_code=400, detail="LLM API 未配置")

    # Get file info
    file_info = await get_file_info(request.category, request.material)
    if not file_info:
        raise HTTPException(status_code=404, detail=f"资料 '{request.material}' 不存在")

    # Start background task
    task_id = str(uuid.uuid4())[:8]

    async def run_index_agent():
        from studykb_init.agents.index_agent import IndexAgent

        async def send_msg(msg: dict):
            await send_to_session(session_id, msg)

        console = WebSocketConsole(send_msg)
        file_path = Path(file_info["path"])

        await send_msg({
            "type": "log",
            "content": f"开始为 {request.material}.md 生成索引 ({file_info['line_count']} 行)",
        })

        agent = IndexAgent(
            config=settings.llm,
            console=console,
            file_path=file_path,
            material_name=request.material,
        )

        try:
            index_content = await agent.run(f"请为文件 {request.material}.md 生成章节索引")

            if index_content:
                # Save index
                success, message = await save_index(
                    request.category, request.material, index_content, overwrite=True
                )

                await send_msg({
                    "type": "complete",
                    "success": success,
                    "content": index_content[:2000] if success else None,
                    "message": message,
                })
            else:
                await send_msg({
                    "type": "error",
                    "content": "Agent 未返回索引内容",
                })

        except Exception as e:
            await send_msg({
                "type": "error",
                "content": f"Agent 执行失败: {str(e)}",
            })

    bg_task = asyncio.create_task(run_index_agent())
    active_tasks[session_id] = bg_task

    def _cleanup(t: asyncio.Task):
        active_tasks.pop(session_id, None)
    bg_task.add_done_callback(_cleanup)

    return {"task_id": task_id, "message": "索引生成任务已启动"}


@router.post("/init-progress")
async def init_progress(request: ProgressInitRequest, session_id: str):
    """Initialize progress for a category using ProgressAgent."""
    settings = load_config()

    if not ensure_api_configured(settings):
        raise HTTPException(status_code=400, detail="LLM API 未配置")

    # Check category
    category_path = settings.kb_path / request.category
    if not category_path.exists():
        raise HTTPException(status_code=404, detail=f"分类 '{request.category}' 不存在")

    # Check materials
    materials = await get_category_materials(request.category)
    if not materials:
        raise HTTPException(status_code=400, detail=f"分类 '{request.category}' 中没有资料文件")

    task_id = str(uuid.uuid4())[:8]

    async def run_progress_agent():
        from studykb_init.agents.progress_agent import ProgressAgent
        from studykb_init.services.progress_service import ProgressService, RelatedSection

        async def send_msg(msg: dict):
            await send_to_session(session_id, msg)

        console = WebSocketConsole(send_msg)

        await send_msg({
            "type": "log",
            "content": f"开始为分类 '{request.category}' 生成进度条目",
        })

        # Show materials
        for m in materials:
            idx_mark = "[IDX]" if m["has_index"] else ""
            await send_msg({
                "type": "log",
                "content": f"  - {m['name']} ({m['line_count']} 行) {idx_mark}",
            })

        agent = ProgressAgent(
            config=settings.llm,
            console=console,
            category=request.category,
            category_path=category_path,
        )

        try:
            entries = await agent.run(f"请为分类 '{request.category}' 生成学习进度条目")

            if entries and isinstance(entries, list):
                # Save progress entries
                service = ProgressService()
                created_count = 0

                for entry in entries:
                    try:
                        sections = entry.get("related_sections")
                        sections_data = None
                        if sections:
                            sections_data = [
                                RelatedSection(
                                    material=s["material"],
                                    start_line=s["start_line"],
                                    end_line=s["end_line"],
                                    desc=s.get("desc", ""),
                                )
                                for s in sections
                            ]

                        await service.update_progress(
                            category=request.category,
                            progress_id=entry["progress_id"],
                            status="pending",
                            name=entry["name"],
                            comment="",
                            related_sections=sections_data,
                        )
                        created_count += 1
                    except Exception as e:
                        await send_msg({
                            "type": "log",
                            "content": f"创建失败: {entry.get('progress_id')}: {e}",
                        })

                await send_msg({
                    "type": "complete",
                    "success": True,
                    "content": {"created_count": created_count, "total": len(entries)},
                    "message": f"已创建 {created_count} 个进度条目",
                })
            else:
                await send_msg({
                    "type": "error",
                    "content": "Agent 未返回有效的进度条目",
                })

        except Exception as e:
            await send_msg({
                "type": "error",
                "content": f"Agent 执行失败: {str(e)}",
            })

    bg_task = asyncio.create_task(run_progress_agent())
    active_tasks[session_id] = bg_task

    def _cleanup(t: asyncio.Task):
        active_tasks.pop(session_id, None)
    bg_task.add_done_callback(_cleanup)

    return {"task_id": task_id, "message": "进度初始化任务已启动"}


@router.post("/full-init")
async def full_init(request: FullInitRequest, session_id: str):
    """Run full initialization flow."""
    settings = load_config()

    if not ensure_api_configured(settings):
        raise HTTPException(status_code=400, detail="LLM API 未配置")

    task_id = str(uuid.uuid4())[:8]

    async def run_full_init():
        from studykb_init.agents.index_agent import IndexAgent
        from studykb_init.agents.progress_agent import ProgressAgent
        from studykb_init.services.progress_service import ProgressService, RelatedSection

        async def send_msg(msg: dict):
            await send_to_session(session_id, msg)

        console = WebSocketConsole(send_msg)
        category = request.category

        try:
            # Step 1: Create category if needed
            await send_msg({
                "type": "progress",
                "step": 1,
                "total": 4,
                "content": "检查/创建分类",
            })

            if request.new_category:
                success, message = await create_category(category)
                if not success:
                    await send_msg({"type": "error", "content": message})
                    return
                await send_msg({"type": "log", "content": f"✓ {message}"})
            else:
                if not await category_exists(category):
                    await send_msg({"type": "error", "content": f"分类 '{category}' 不存在"})
                    return

            # Step 2: Import file if provided
            await send_msg({
                "type": "progress",
                "step": 2,
                "total": 4,
                "content": "导入资料文件",
            })

            material = None
            if request.material_path:
                source_path = Path(request.material_path).expanduser().resolve()
                success, message, file_info = await import_file(source_path, category)
                if success:
                    await send_msg({"type": "log", "content": f"✓ {message}"})
                    material = file_info["name"]
                else:
                    await send_msg({"type": "error", "content": message})
                    return
            else:
                materials = await get_category_materials(category)
                if materials:
                    material = materials[0]["name"]
                    await send_msg({"type": "log", "content": f"使用现有资料: {material}"})
                else:
                    await send_msg({"type": "error", "content": "没有可用的资料文件"})
                    return

            # Step 3: Generate index
            await send_msg({
                "type": "progress",
                "step": 3,
                "total": 4,
                "content": "生成索引",
            })

            file_info = await get_file_info(category, material)
            if file_info:
                file_path = Path(file_info["path"])

                agent = IndexAgent(
                    config=settings.llm,
                    console=console,
                    file_path=file_path,
                    material_name=material,
                )

                index_content = await agent.run(f"请为文件 {material}.md 生成章节索引")
                if index_content:
                    success, message = await save_index(
                        category, material, index_content, overwrite=True
                    )
                    await send_msg({"type": "log", "content": f"✓ {message}"})

            # Step 4: Initialize progress
            await send_msg({
                "type": "progress",
                "step": 4,
                "total": 4,
                "content": "初始化进度",
            })

            category_path = settings.kb_path / category
            agent = ProgressAgent(
                config=settings.llm,
                console=console,
                category=category,
                category_path=category_path,
            )

            entries = await agent.run(f"请为分类 '{category}' 生成学习进度条目")
            if entries and isinstance(entries, list):
                service = ProgressService()
                created_count = 0

                for entry in entries:
                    try:
                        sections = entry.get("related_sections")
                        sections_data = None
                        if sections:
                            sections_data = [
                                RelatedSection(
                                    material=s["material"],
                                    start_line=s["start_line"],
                                    end_line=s["end_line"],
                                    desc=s.get("desc", ""),
                                )
                                for s in sections
                            ]

                        await service.update_progress(
                            category=category,
                            progress_id=entry["progress_id"],
                            status="pending",
                            name=entry["name"],
                            comment="",
                            related_sections=sections_data,
                        )
                        created_count += 1
                    except Exception:
                        pass

                await send_msg({"type": "log", "content": f"✓ 已创建 {created_count} 个进度条目"})

            await send_msg({
                "type": "complete",
                "success": True,
                "message": "初始化流程完成",
            })

        except Exception as e:
            await send_msg({
                "type": "error",
                "content": f"初始化失败: {str(e)}",
            })

    bg_task = asyncio.create_task(run_full_init())
    active_tasks[session_id] = bg_task

    def _cleanup(t: asyncio.Task):
        active_tasks.pop(session_id, None)
    bg_task.add_done_callback(_cleanup)

    return {"task_id": task_id, "message": "完整初始化任务已启动"}
