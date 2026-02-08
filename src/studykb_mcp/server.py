"""MCP Server implementation for StudyKB."""

import asyncio
import contextlib

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool

from .tools.grep import grep_handler
from .tools.read_file import read_file_handler
from .tools.read_index import read_index_handler
from .tools.read_overview import read_overview_handler
from .tools.read_progress import read_progress_handler
from .tools.update_progress import (
    create_progress_handler,
    delete_progress_handler,
    update_progress_handler,
)
from .tools.workspace import (
    delete_workspace_file_handler,
    edit_workspace_file_handler,
    list_workspace_handler,
    read_workspace_file_handler,
    write_workspace_file_handler,
)

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
- 需要获取所有存在的文件名

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

💡 两种使用模式：
1. 列表模式（只传 category）：获取该分类的完整进度概览
2. 详情模式（传 category + progress_id）：获取单个节点详情，包含关联资料片段

📌 调用时机：
- 用户说"继续学习""今天学什么"时，了解当前进度
- 需要确定下一个学习内容时
- 用户问"我学到哪了""还有多少没学"时
- 检查是否有需要复习的内容时
- 需要查看某个知识点的关联资料位置时（传 progress_id）

🔗 推荐前置调用：
- read_overview：确认大类名称存在

🔗 推荐后续调用：
- read_index / grep：根据进度定位具体内容
- read_file：根据 related_sections 读取关联资料片段
- update_progress：开始新知识点时标记 active""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称，如 '数据结构'、'计算机组成原理'",
                },
                "progress_id": {
                    "type": "string",
                    "description": "【可选·详情模式】指定进度节点 ID，返回该节点详情（含关联资料片段）",
                },
                "status_filter": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["done", "active", "review", "pending"],
                    },
                    "description": "【可选·列表模式】筛选状态。不传则返回所有状态",
                },
                "since": {
                    "type": "string",
                    "enum": ["7d", "30d", "90d", "all"],
                    "default": "all",
                    "description": "【可选·列表模式】时间范围筛选，基于 updated_at",
                },
                "show_time": {
                    "type": "boolean",
                    "default": False,
                    "description": "【可选·列表模式】是否显示时间信息（updated_at, due date 等），默认不显示以节省 token",
                },
            },
            "required": ["category"],
        },
    ),
    Tool(
        name="update_progress",
        description="""更新已有的学习进度条目状态。

⚠️ 重要：此工具仅用于更新【已存在】的进度节点，不会创建新节点。

📌 调用时机：
- 开始学习某个知识点时（一旦决定开始学，在讲解前就立即更新） → status="active"
- 用户明确掌握了某个知识点时 → status="done"
- 用户说"这个要复习"或完成复习时 → status="review" / "done"
- 用户更新对某个知识点的理解/笔记时 → 更新 comment
- 需要更新知识点的关联资料片段时 → 更新 related_sections

🔗 推荐前置调用：
- read_progress：确认节点存在及当前状态

⚠️ 注意：
- 如果 progress_id 不存在会报错
- status 变为 done 时会自动设置 next_review 时间
- related_sections 不传时保留原有值，传空数组则清空""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称",
                },
                "progress_id": {
                    "type": "string",
                    "description": "已存在的进度标识，如 'ds.graph.mst.kruskal'",
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "done", "review", "pending"],
                    "description": "状态: active(正在学习), done(已掌握), review(需要复习), pending(待学习)",
                },
                "comment": {
                    "type": "string",
                    "description": "一句话描述当前理解/进度/笔记",
                },
                "related_sections": {
                    "type": "array",
                    "description": "关联的资料片段列表（不传则保留原值）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "material": {"type": "string", "description": "资料文件名（含 .md 后缀）"},
                            "start_line": {"type": "integer", "description": "起始行号"},
                            "end_line": {"type": "integer", "description": "结束行号"},
                            "desc": {"type": "string", "description": "片段描述，如'教材正文'、'习题'等"},
                        },
                        "required": ["material", "start_line", "end_line"],
                    },
                },
            },
            "required": ["category", "progress_id", "status"],
        },
    ),
    Tool(
        name="create_progress",
        description="""创建新的学习进度节点。

⚠️ 重要原则：
1. 【避免随意创建】现有节点通常已涵盖大部分知识点，优先使用现有节点
2. 【细粒度拆分】仅当现有节点粒度太粗、无法准确追踪学习进度时才创建
3. 【配合删除使用】创建细粒度节点时，应同时删除被拆分的粗粒度节点

📌 正确的创建场景：
- 现有节点 "ds.sort" 太粗 → 拆分为 "ds.sort.bubble", "ds.sort.quick", "ds.sort.merge" 等
- 学习了索引中没有的补充知识点
- 用户明确要求添加新的追踪项

🔗 推荐配合调用：
- delete_progress：删除被拆分/取代的旧节点
- read_progress：先确认现有节点结构

💡 示例：
拆分 "ds.tree.binary" 为更细粒度：
1. create_progress: ds.tree.binary.traversal (二叉树遍历)
2. create_progress: ds.tree.binary.bst (二叉搜索树)
3. create_progress: ds.tree.binary.avl (AVL树)
4. delete_progress: ds.tree.binary (删除旧的粗粒度节点)""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称",
                },
                "progress_id": {
                    "type": "string",
                    "description": "新进度标识，使用点分层级格式，如 'ds.graph.mst.kruskal'",
                },
                "name": {
                    "type": "string",
                    "description": "知识点名称，如 'Kruskal算法'",
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "done", "review", "pending"],
                    "default": "pending",
                    "description": "初始状态，默认 pending",
                },
                "comment": {
                    "type": "string",
                    "description": "备注（可选）",
                },
                "related_sections": {
                    "type": "array",
                    "description": "关联的资料片段列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "material": {"type": "string", "description": "资料文件名（含 .md 后缀）"},
                            "start_line": {"type": "integer", "description": "起始行号"},
                            "end_line": {"type": "integer", "description": "结束行号"},
                            "desc": {"type": "string", "description": "片段描述，如'教材正文'、'习题'等"},
                        },
                        "required": ["material", "start_line", "end_line"],
                    },
                },
            },
            "required": ["category", "progress_id", "name"],
        },
    ),
    Tool(
        name="delete_progress",
        description="""删除学习进度节点。

📌 调用时机：
- 拆分粗粒度节点后，删除原节点
- 合并多个细粒度节点为一个后，删除旧节点
- 删除错误创建或不再需要的节点

🔗 推荐配合调用：
- create_progress：创建替代的新节点

⚠️ 注意：
- 删除操作不可恢复
- 建议先创建新节点，确认无误后再删除旧节点""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称",
                },
                "progress_id": {
                    "type": "string",
                    "description": "要删除的进度标识",
                },
            },
            "required": ["category", "progress_id"],
        },
    ),
    Tool(
        name="read_index",
        description="""读取资料的索引文件，获取章节结构和行号映射。

📌 调用时机：
- 【重要】始终推荐尽早执行本工具以掌握资料内容
- 需要定位某个知识点在资料中的具体位置时
- 准备用 read_file 读取内容前，先查行号
- 需要搜寻例题/教科书标准定义

📄 返回格式：
- CSV 格式索引数据，字段: type,depth,number,title,start,end,tags
- 行类型: #meta(元信息), overview(概览), chapter(章节), lookup(快速查找)
- depth: 0=章, 1=节, 2=小节; tags 用 ; 分隔

🔗 推荐前置调用：
- read_overview：确认资料存在且有 [IDX] 标记

🔗 推荐后续调用：
- read_file：根据索引中的行号读取具体内容

⚠️ 注意：
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
                    "description": "资料文件名（含 .md 后缀），如 '王道数据结构.md'",
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
- 任何时机，当用户准备正式开始学习特定章节前，必须先读取资料文件并参考资料上的可靠教学顺序进行讲解。
- 当时机需要寻求例题时，优先寻找知识库中的现存例题。若无才考虑现编或使用其他工具获取。

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
                    "description": "资料文件名（含 .md 后缀），如 '王道数据结构.md'",
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
        description="""在资料中搜索关键词，返回匹配行及上下文。大小写不敏感。

📌 调用时机：
- 用户问"xxx在哪里""讲讲xxx"时，定位内容位置
- 资料没有索引文件，需要搜索定位时
- 查找某个概念/术语的所有出现位置

🔗 推荐后续调用：
- read_file：根据搜索结果的行号读取完整段落

⚠️ 注意：
- 不指定 material 时搜索整个大类（所有 .md 文件）
- 返回匹配行 + 上下文（默认前后各 2 行）""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "大类名称，如 '数据结构'",
                },
                "pattern": {
                    "type": "string",
                    "description": "搜索关键词，如 'Dijkstra'、'最短路径'",
                },
                "material": {
                    "type": "string",
                    "description": "【可选】指定搜索的文件（含 .md），不填则搜索该大类全部文件",
                },
                "context_lines": {
                    "type": "integer",
                    "default": 2,
                    "description": "【可选】上下文行数，默认 2（即显示匹配行前后各 2 行）",
                },
                "max_matches": {
                    "type": "integer",
                    "default": 20,
                    "description": "【可选】最大匹配数，默认 20，设为 -1 返回全部",
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
    # Workspace tools
    Tool(
        name="read_workspace_file",
        description="""读取进度节点工作区中的文件内容。

📌 调用时机：
- 需要查看某个知识点的学习笔记时
- 需要查看之前写的代码示例时
- 在编辑文件前先读取当前内容

🔗 推荐前置调用：
- list_workspace：查看工作区有哪些文件
- read_progress：确认 progress_id 存在

⚠️ 注意：
- 默认读取 note.md（主笔记文件）
- 支持读取任意文本文件（.md, .py, .js, .txt 等）
- 二进制文件（图片等）无法读取""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "大类名称，如 '数据结构'"},
                "progress_id": {"type": "string", "description": "进度节点 ID，如 'ds.graph.mst.kruskal'"},
                "file_path": {
                    "type": "string",
                    "default": "note.md",
                    "description": "工作区内的文件路径，默认 'note.md'",
                },
                "start_line": {"type": "integer", "description": "【可选】起始行号，从 1 开始"},
                "end_line": {"type": "integer", "description": "【可选】结束行号"},
            },
            "required": ["category", "progress_id"],
        },
    ),
    Tool(
        name="write_workspace_file",
        description="""创建或覆盖进度节点工作区中的文件。

📌 调用时机：
- 为新知识点创建学习笔记
- 保存代码示例
- 完全重写现有文件

💡 学习场景示例：
- 学习 Kruskal 算法时，创建 note.md 记录要点
- 写一个实现代码保存到 code/kruskal.py
- 整理思维导图内容到 note.md

🔗 推荐配合调用：
- read_workspace_file：写入前先读取确认
- update_progress：更新进度状态

⚠️ 注意：
- 文件不存在时自动创建（包括目录）
- 文件已存在时会覆盖
- 如只需局部修改，请使用 edit_workspace_file""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "大类名称"},
                "progress_id": {"type": "string", "description": "进度节点 ID"},
                "file_path": {
                    "type": "string",
                    "default": "note.md",
                    "description": "工作区内的文件路径，默认 'note.md'",
                },
                "content": {"type": "string", "description": "文件内容"},
            },
            "required": ["category", "progress_id", "content"],
        },
    ),
    Tool(
        name="edit_workspace_file",
        description="""通过精确字符串匹配修改工作区文件内容。

📌 调用时机：
- 在已有笔记中添加新内容
- 修改代码中的某个函数
- 更正笔记中的错误
- 更新知识点的理解

💡 学习场景示例：
- 在笔记末尾追加今天的学习心得
- 修改代码示例中的 bug
- 更新对某个概念的理解描述

🔗 推荐前置调用：
- read_workspace_file：确认当前文件内容，获取要替换的精确文本

⚠️ 重要提示：
- old_string 必须与文件中的内容【精确匹配】
- 包含足够的上下文以确保唯一匹配
- 如果匹配到多处或找不到，会返回错误
- 创建新文件请用 write_workspace_file""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "大类名称"},
                "progress_id": {"type": "string", "description": "进度节点 ID"},
                "file_path": {
                    "type": "string",
                    "default": "note.md",
                    "description": "工作区内的文件路径，默认 'note.md'",
                },
                "old_string": {
                    "type": "string",
                    "description": "要替换的精确文本（必须与文件内容完全匹配）",
                },
                "new_string": {
                    "type": "string",
                    "description": "替换后的新文本",
                },
            },
            "required": ["category", "progress_id", "old_string", "new_string"],
        },
    ),
    Tool(
        name="delete_workspace_file",
        description="""删除工作区中的文件。

📌 调用时机：
- 删除不再需要的代码示例
- 清理过时的笔记草稿
- 整理工作区

⚠️ 注意：
- 删除操作不可恢复
- 不能删除目录，只能删除文件""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "大类名称"},
                "progress_id": {"type": "string", "description": "进度节点 ID"},
                "file_path": {"type": "string", "description": "要删除的文件路径"},
            },
            "required": ["category", "progress_id", "file_path"],
        },
    ),
    Tool(
        name="list_workspace",
        description="""列出进度节点工作区的文件结构。

📌 调用时机：
- 查看某个知识点有哪些笔记/代码
- 了解工作区的文件组织
- 在读取文件前先查看有什么

🔗 推荐后续调用：
- read_workspace_file：读取感兴趣的文件""",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "大类名称"},
                "progress_id": {"type": "string", "description": "进度节点 ID"},
            },
            "required": ["category", "progress_id"],
        },
    ),
]

# Tool handlers mapping
HANDLERS = {
    "read_overview": read_overview_handler,
    "read_progress": read_progress_handler,
    "update_progress": update_progress_handler,
    "create_progress": create_progress_handler,
    "delete_progress": delete_progress_handler,
    "read_index": read_index_handler,
    "read_file": read_file_handler,
    "grep": grep_handler,
    # Workspace tools
    "read_workspace_file": read_workspace_file_handler,
    "write_workspace_file": write_workspace_file_handler,
    "edit_workspace_file": edit_workspace_file_handler,
    "delete_workspace_file": delete_workspace_file_handler,
    "list_workspace": list_workspace_handler,
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


# Streamable HTTP transport
session_manager = StreamableHTTPSessionManager(app=server)


# Create ASGI app
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.cors import CORSMiddleware


@contextlib.asynccontextmanager
async def lifespan(app_instance: Starlette):
    async with session_manager.run():
        yield


app = Starlette(
    routes=[
        Mount("/mcp", app=session_manager.handle_request),
    ],
    lifespan=lifespan,
)

# Add CORS for browser clients
app = CORSMiddleware(
    app,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


async def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run the MCP server with Streamable HTTP transport."""
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()
