"""MCP Server implementation for StudyKB."""

import asyncio

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool

from .tools.grep import grep_handler
from .tools.read_file import read_file_handler
from .tools.read_index import read_index_handler
from .tools.read_overview import read_overview_handler
from .tools.read_progress import read_progress_handler
from .tools.update_progress import update_progress_handler

# Create MCP Server instance
server = Server("studykb-mcp")


# Tool definitions
TOOLS = [
    Tool(
        name="read_overview",
        description="""获取知识库全景图，列出所有大类及其包含的资料文件。

📌 调用时机：
- 对话开始时，了解当前知识库有哪些内容
- 用户提到一个你不确定是否存在的学科/资料时
- 需要向用户展示可学习的范围时

⚠️ 注意：
- 这是轻量级调用，返回概览信息，不包含具体内容
- 确认资料存在后，再用 read_index 或 grep 深入""",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="read_progress",
        description="""获取某个大类的学习进度追踪数据。

📌 调用时机：
- 用户说"继续学习""今天学什么"时，了解当前进度
- 需要确定下一个学习内容时
- 用户问"我学到哪了""还有多少没学"时
- 检查是否有需要复习的内容时

🔗 推荐前置调用：
- read_overview：确认大类名称存在

🔗 推荐后续调用：
- read_index / grep：根据进度定位具体内容
- update_progress：开始新知识点时标记 active""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称，如 '数据结构'、'计算机组成原理'",
                },
                "status_filter": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["done", "active", "review", "pending"],
                    },
                    "description": "筛选状态，可选值: done, active, review, pending",
                },
                "since": {
                    "type": "string",
                    "enum": ["7d", "30d", "90d", "all"],
                    "default": "all",
                    "description": "时间范围筛选，基于 updated_at",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "每个状态分组的最大返回条数，设为 -1 返回全部",
                },
            },
            "required": ["category"],
        },
    ),
    Tool(
        name="update_progress",
        description="""创建或更新学习进度条目。

📌 调用时机：
- 开始学习新知识点时 → status="active"
- 用户表示掌握了某个知识点时 → status="done"
- 用户说"这个要复习"或完成复习时 → status="review" / "done"
- 用户更新对某个知识点的理解/笔记时 → 更新 comment

🔗 推荐前置调用：
- read_progress：确认当前状态，避免重复创建

⚠️ 注意：
- progress_id 使用点分格式，如 "ds.graph.mst.kruskal"
- 首次创建时 name 必填，后续更新可省略
- status 变为 done 时会自动设置 next_review 时间""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称",
                },
                "progress_id": {
                    "type": "string",
                    "description": "进度标识，使用点分层级格式，如 'ds.graph.mst.kruskal'",
                },
                "name": {
                    "type": "string",
                    "description": "知识点名称，如 'Kruskal算法'（首次创建时必填）",
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "done", "review"],
                    "description": "状态: active(正在学习), done(已掌握), review(需要复习)",
                },
                "comment": {
                    "type": "string",
                    "description": "一句话描述当前理解/进度/笔记",
                },
            },
            "required": ["category", "progress_id", "status", "comment"],
        },
    ),
    Tool(
        name="read_index",
        description="""读取资料的索引文件，获取章节结构和行号映射。

📌 调用时机：
- 需要定位某个知识点在资料中的具体位置时
- 准备用 read_file 读取内容前，先查行号
- 需要搜寻例题/教科书标准定义的

🔗 推荐前置调用：
- read_overview：确认资料存在且有 [IDX] 标记

🔗 推荐后续调用：
- read_file：根据索引中的行号读取具体内容

⚠️ 注意：
- 只有标记 [IDX] 的资料才有索引文件
- 没有索引文件的探索请改用 grep""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称",
                },
                "material": {
                    "type": "string",
                    "description": "资料名称（不含扩展名），如 '王道数据结构'",
                },
            },
            "required": ["category", "material"],
        },
    ),
    Tool(
        name="read_file",
        description="""读取资料文件的指定行范围内容。

📌 调用时机：
- 通过 read_index 或 grep 定位到行号后，读取原文
- 需要给用户展示/讲解教材具体内容时
- 用户说"给我看看原文""书上怎么说的"时

🔗 推荐前置调用：
- read_index：获取准确的行号范围
- grep：搜索关键词定位行号

⚠️ 注意：
- 单次最多读取 500 行，超出会截断并提示
- 行号从 1 开始计数
- 建议精确定位后读取，避免读太多无关内容""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称",
                },
                "material": {
                    "type": "string",
                    "description": "资料名称（不含扩展名）",
                },
                "start_line": {
                    "type": "integer",
                    "description": "起始行号（包含），从 1 开始",
                },
                "end_line": {
                    "type": "integer",
                    "description": "结束行号（包含）",
                },
            },
            "required": ["category", "material", "start_line", "end_line"],
        },
    ),
    Tool(
        name="grep",
        description="""在资料中搜索关键词，返回匹配行及上下文。

📌 调用时机：
- 资料没有索引文件时，用搜索定位内容
- 索引不够详细，需要精确查找某个术语时
- 用户问"xxx在哪里提到过"时
- 需要查找某个概念的所有出现位置时

🔗 推荐后续调用：
- read_file：根据搜索结果的行号读取完整段落

⚠️ 注意：
- 不指定 material 时搜索整个大类，可能较慢
- 匹配结果有上限，超出会截断
- 支持简单文本匹配，不支持正则""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称",
                },
                "material": {
                    "type": "string",
                    "description": "资料名称，不填则搜索该大类下所有文件",
                },
                "pattern": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "context_lines": {
                    "type": "integer",
                    "default": 2,
                    "description": "匹配行的上下文行数（上下各 N 行）",
                },
                "max_matches": {
                    "type": "integer",
                    "default": 20,
                    "description": "最大返回匹配数，设为 -1 返回全部",
                },
            },
            "required": ["category", "pattern"],
        },
    ),
    Tool(
        name="batch_call",
        description="""并行执行多个工具调用，一次返回所有结果。

📌 调用时机：
- 需要同时获取多个独立信息时（如：概览+进度+搜索）
- 对话开始时一次性获取上下文
- 任何可以并行的多个查询

⚠️ 注意：
- 理论上应将有依赖关系的调用分先后进行，但可试探性的批量调用以提升效率。
  例如用户说"今天继续学数据结构"，即便应先获取总览确认大类名，但也可先尝试获取「数据结构」的进度，即便不存在也没有损失。诸如此类。
- 强依赖路径的调用（如先 read_index/grep 再 read_file）避免放在同一批。
- 单次最多 10 个并行调用

💡 示例组合启发：

1️⃣ 会话开始 - 用户说"开始学习/继续学习 X"：
   read_overview + read_progress(category=X)
   → 一次获取知识库全貌 + 该分类进度

2️⃣ 探索知识点 - 用户问"X是什么/讲讲X"：
   grep(pattern=X) + read_index(若有)
   → 同时搜索关键词 + 获取索引定位

3️⃣ 多关键词搜索 - 用户说"Prim和Kruskal有什么区别"：
   grep(pattern=Prim) + grep(pattern=Kruskal)
   → 同时搜索两个概念

4️⃣ 批量状态更新 - 用户说"这几个我都会了"：
   update_progress(id1, done) + update_progress(id2, done) + ...
   → 多个进度并行更新""",
        inputSchema={
            "type": "object",
            "properties": {
                "calls": {
                    "type": "array",
                    "description": "要并行执行的工具调用列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "工具名称",
                            },
                            "arguments": {
                                "type": "object",
                                "description": "工具参数",
                            },
                        },
                        "required": ["tool", "arguments"],
                    },
                    "maxItems": 10,
                },
            },
            "required": ["calls"],
        },
    ),
]

# Tool handlers mapping
HANDLERS = {
    "read_overview": read_overview_handler,
    "read_progress": read_progress_handler,
    "update_progress": update_progress_handler,
    "read_index": read_index_handler,
    "read_file": read_file_handler,
    "grep": grep_handler,
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    # 特殊处理 batch_call
    if name == "batch_call":
        return await _handle_batch_call(arguments)

    handler = HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {e}")]


async def _handle_batch_call(arguments: dict) -> list[TextContent]:
    """Handle batch_call tool - execute multiple tools in parallel."""
    calls = arguments.get("calls", [])

    if not calls:
        return [TextContent(type="text", text="❌ batch_call: 'calls' 参数为空")]

    if len(calls) > 10:
        return [TextContent(type="text", text="❌ batch_call: 最多支持 10 个并行调用")]

    async def execute_single(call: dict, index: int) -> str:
        """Execute a single tool call and format result."""
        tool_name = call.get("tool", "")
        tool_args = call.get("arguments", {})

        handler = HANDLERS.get(tool_name)
        if not handler:
            return f"## [{index + 1}] {tool_name}\n❌ Unknown tool: {tool_name}"

        try:
            result = await handler(tool_args)
            return f"## [{index + 1}] {tool_name}\n{result}"
        except Exception as e:
            return f"## [{index + 1}] {tool_name}\n❌ Error: {e}"

    # 并行执行所有调用
    tasks = [execute_single(call, i) for i, call in enumerate(calls)]
    results = await asyncio.gather(*tasks)

    # 组合结果
    combined = f"# batch_call 结果 ({len(calls)} 个调用)\n\n"
    combined += "\n\n---\n\n".join(results)

    return [TextContent(type="text", text=combined)]


# SSE transport
sse_transport = SseServerTransport("/messages/")


# Create ASGI app
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware


async def handle_sse(request):
    """SSE endpoint handler.

    Note: Must return a Response to avoid 'NoneType' error when client disconnects.
    """
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )
    # Return empty response to fix NoneType error
    return Response()


app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)


async def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run the MCP server with SSE transport."""
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()
