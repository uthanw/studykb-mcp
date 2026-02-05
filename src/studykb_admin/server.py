"""StudyKB Admin Server - FastAPI backend for management interface."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from .api import categories, materials, progress, convert, tasks, workspace


# WebSocket connection manager for real-time updates
class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("StudyKB Admin starting...")
    yield
    # Shutdown
    print("StudyKB Admin shutting down...")


# Create FastAPI app
app = FastAPI(
    title="StudyKB Admin",
    description="Web management interface for StudyKB knowledge base",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(materials.router, prefix="/api/materials", tags=["materials"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(convert.router, prefix="/api/convert", tags=["convert"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(workspace.router, prefix="/api/workspace", tags=["workspace"])


# MCP configuration endpoint
@app.get("/api/config/mcp")
async def get_mcp_config():
    """Get MCP server configuration for copying."""
    return {
        "mcpServers": {
            "studykb": {
                "command": "studykb-mcp",
                "args": ["--transport", "sse", "--port", "8080"],
                "env": {}
            }
        }
    }


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time task updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_json()
            # Can handle client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "studykb-admin"}


# Serve static files (frontend) - mount last to not override API routes
WEB_DIR = Path(__file__).parent / "web" / "dist"


@app.get("/{path:path}")
async def serve_spa(path: str):
    """Serve SPA frontend, fallback to index.html for client-side routing."""
    # First try to serve the exact file
    file_path = WEB_DIR / path
    if file_path.is_file():
        return FileResponse(file_path)

    # Fallback to index.html for SPA routing
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    # Development mode - no frontend built yet
    return {"message": "Frontend not built. Run: cd web && npm run build"}


def get_manager() -> ConnectionManager:
    """Get the connection manager for dependency injection."""
    return manager


async def run_server(host: str = "0.0.0.0", port: int = 3000) -> None:
    """Run the admin server."""
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main():
    """Entry point for CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="StudyKB Admin Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind")
    args = parser.parse_args()

    asyncio.run(run_server(host=args.host, port=args.port))


if __name__ == "__main__":
    main()
