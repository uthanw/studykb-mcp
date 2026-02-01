"""Progress initialization agent for analyzing files and generating progress entries."""

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

from studykb_init.config import LLMConfig
from studykb_init.agents.base import AgentContext, BaseAgent, ToolDefinition


class ProgressAgent(BaseAgent):
    """Agent for analyzing category files and generating progress tracking entries.

    This agent explores all material files in a category directory and generates
    appropriate progress tracking entries with progress IDs and knowledge point names.
    Uses shell tools for efficient file analysis without loading entire files.
    """

    def __init__(
        self,
        config: LLMConfig,
        console: Console,
        category: str,
        category_path: Path,
    ):
        """Initialize the progress agent.

        Args:
            config: LLM API configuration.
            console: Rich console for output.
            category: Category name for the progress file.
            category_path: Path to the category directory containing material files.
        """
        self.category = category
        self.category_path = category_path
        context = AgentContext(
            console=console,
            category=category,
            work_dir=str(category_path),
        )
        super().__init__(config, console, context)

    def _setup_tools(self) -> None:
        """Register shell and progress submission tools."""
        # shell - 通用只读shell命令
        self.register_tool(
            ToolDefinition(
                name="shell",
                description="""执行只读shell命令进行文件分析。
⚠️ 安全限制: 只允许读取操作，禁止任何写入/删除/修改命令。

工作目录已设置为分类文件夹，可直接引用文件名。

允许的命令: ls, wc, grep, sed, awk, head, tail, cat, sort, uniq, cut, tr, find
禁止的操作: >, >>, rm, mv, cp, chmod, chown, dd, tee 等任何写入操作

常用命令示例:
  ls -la                            # 列出目录中的所有文件
  ls *.md                           # 列出所有 Markdown 文件
  wc -l *.md                        # 统计所有 md 文件行数
  grep -n "^# " 文件名.md           # 提取一级标题及行号
  grep -n "^## " 文件名.md          # 提取二级标题及行号
  head -100 文件名.md               # 查看文件开头
  tail -100 文件名.md               # 查看文件结尾
  sed -n '100,200p' 文件名.md       # 读取指定行范围
  cat 文件名_index.md               # 读取索引文件（如果存在）

管道组合示例:
  grep -n "^# " 文件名.md | head -50  # 查看前50个标题""",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "要执行的shell命令(只读操作)",
                        },
                    },
                    "required": ["command"],
                },
                handler=self._shell,
            )
        )

        # submit_progress - 提交进度条目
        self.register_tool(
            ToolDefinition(
                name="submit_progress",
                description="提交生成的进度条目。这是最终输出工具，调用后Agent任务完成。",
                parameters={
                    "type": "object",
                    "properties": {
                        "entries": {
                            "type": "array",
                            "description": "进度条目列表",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "progress_id": {
                                        "type": "string",
                                        "description": "点分格式的进度ID，如 ds.graph.mst.kruskal",
                                    },
                                    "name": {
                                        "type": "string",
                                        "description": "知识点名称，如 Kruskal算法",
                                    },
                                },
                                "required": ["progress_id", "name"],
                            },
                        },
                    },
                    "required": ["entries"],
                },
                handler=self._submit_progress,
                is_terminal=True,
            )
        )

    def _get_file_list(self) -> str:
        """Get a formatted list of files in the category directory."""
        files = []
        for f in sorted(self.category_path.iterdir()):
            if f.suffix == ".md" and not f.name.endswith("_index.md"):
                # Count lines
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        line_count = sum(1 for _ in fp)
                except Exception:
                    line_count = 0

                # Check if index exists
                index_file = f.with_name(f.stem + "_index.md")
                has_index = index_file.exists()
                idx_mark = " [IDX]" if has_index else ""

                files.append(f"  - {f.name} ({line_count} 行){idx_mark}")

        return "\n".join(files) if files else "  (无文件)"

    def get_system_prompt(self) -> str:
        """Get the system prompt for progress initialization."""
        file_list = self._get_file_list()

        return f"""你是一个学习进度规划专家，擅长分析教材内容并规划学习路径。作为linux专家，你会灵活使用shell命令高效分析文件。

## 当前任务

为分类 **"{self.category}"** 生成学习进度跟踪条目。

## 工作目录

`{self.category_path}`

目录中的资料文件:
{file_list}

[IDX] 表示该资料有索引文件（文件名_index.md），优先使用索引文件了解内容结构。

## 可用工具

1. **shell** - 执行只读 shell 命令分析文件（工作目录已设置为分类文件夹）
2. **submit_progress** - 提交最终进度条目（调用后任务完成）

## 工作流程

### 阶段1: 文件探索
首先了解目录中有哪些文件:
```bash
ls -la *.md
```

### 阶段2: 分析每个资料
对于每个资料文件:

1. **如果有索引文件** (文件名_index.md)，优先读取索引:
```bash
cat 资料名_index.md
```

2. **如果没有索引**，提取标题结构:
```bash
grep -n "^# " 资料名.md     # 一级标题
grep -n "^## " 资料名.md    # 二级标题
```

3. **需要详细了解时**，读取特定区域:
```bash
sed -n '100,200p' 资料名.md
```

### 阶段3: 规划进度条目
基于分析结果，为每个可独立学习的知识点创建条目。

### 阶段4: 提交结果
调用 `submit_progress` 提交所有进度条目。

## progress_id 命名规则

使用点分层级格式: `学科缩写.大章节.小节.具体知识点`

### 学科缩写
- `ds` - 数据结构
- `os` - 操作系统
- `co` - 计算机组成原理
- `cn` - 计算机网络
- `db` - 数据库
- `se` - 软件工程
- `chem` - 化学
- `math` - 数学
- `phys` - 物理

### 主题缩写
- `linear` - 线性结构
- `tree` - 树结构
- `graph` - 图
- `sort` - 排序
- `search` - 查找
- `dp` - 动态规划
- `process` - 进程
- `memory` - 内存
- `io` - 输入输出
- `cpu` - 处理器
- `cache` - 缓存

### 命名示例
- `ds.linear.array.basic` - 数据结构 > 线性表 > 数组 > 基础概念
- `ds.graph.mst.kruskal` - 数据结构 > 图 > 最小生成树 > Kruskal算法
- `os.process.schedule.fcfs` - 操作系统 > 进程 > 调度 > FCFS算法

### 命名原则
1. 使用小写英文，单词间用下划线连接
2. 层级一般为3-4层，保持简洁
3. 优先使用常见的英文缩写
4. 同一章节的知识点应有共同前缀

## 输出要求

1. **只为真正的知识点创建条目**，跳过:
   - 前言、目录、绪论概述等非核心内容
   - 习题、小结、思考题等辅助内容
   - 纯理论介绍无实质知识点的章节

2. **适当聚合**:
   - 太细的知识点应合并
   - 每章约产出5-15个条目

3. **知识点名称**:
   - 使用中文
   - 简洁明了，一般不超过15字
   - 可以包含英文术语，如"Dijkstra算法"

4. **覆盖完整**:
   - 确保所有资料文件的重要内容都有对应条目
   - 不要遗漏核心算法、定理、概念

## 效率提示

1. **优先使用索引文件** - 如果存在，它包含完整的章节结构
2. **批量提取标题** - 用 grep 快速获取结构，避免逐行读取
3. **最小化读取** - 只在必要时读取文件内容
4. **尽快完成** - 使用最少的工具调用次数完成分析

完成分析后，调用 `submit_progress` 提交结果。"""

    async def _shell(self, command: str, **kwargs: Any) -> str:
        """Execute a read-only shell command in the category directory."""
        # Security check - block dangerous operations
        dangerous_patterns = [
            ">", ">>",  # Redirection
            "rm ", "rm\t", "rmdir",  # Delete
            "mv ", "mv\t",  # Move
            "cp ", "cp\t",  # Copy (could overwrite)
            "chmod", "chown",  # Permissions
            "dd ",  # Disk operations
            "tee ",  # Write to file
            "truncate",  # Truncate file
            "shred",  # Secure delete
            "mkfs", "fdisk",  # Disk formatting
            "sudo", "su ",  # Privilege escalation
            "curl", "wget",  # Network (could download malicious)
            "eval", "exec",  # Code execution
            "; rm", "| rm", "&& rm",  # Chained delete
            "$(", "`",  # Command substitution (could hide dangerous ops)
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return f"安全限制: 不允许使用 '{pattern.strip()}' 操作。只允许读取命令。"

        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(self.category_path),  # Set working directory
                ),
                timeout=30,
            )
            stdout, stderr = await result.communicate()

            output = stdout.decode("utf-8", errors="replace")
            if len(output) > 50000:
                output = output[:50000] + f"\n... (输出截断)"

            if result.returncode != 0 and stderr:
                error = stderr.decode("utf-8", errors="replace")
                if error.strip():
                    output += f"\n[stderr]: {error[:500]}"

            return output if output.strip() else "(无输出)"

        except asyncio.TimeoutError:
            return "命令超时 (30秒)"
        except Exception as e:
            return f"执行失败: {e}"

    async def _submit_progress(
        self, entries: list[dict[str, str]], **kwargs: Any
    ) -> str:
        """Submit the generated progress entries."""
        self.set_result(entries)
        return f"已提交 {len(entries)} 个进度条目，任务完成。"
