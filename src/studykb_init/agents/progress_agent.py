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
                                    "related_sections": {
                                        "type": "array",
                                        "description": "关联的资料片段列表",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "material": {
                                                    "type": "string",
                                                    "description": "资料文件名（含 .md 后缀）",
                                                },
                                                "start_line": {
                                                    "type": "integer",
                                                    "description": "起始行号",
                                                },
                                                "end_line": {
                                                    "type": "integer",
                                                    "description": "结束行号",
                                                },
                                                "desc": {
                                                    "type": "string",
                                                    "description": "片段描述，如'教材正文'、'习题'等",
                                                },
                                            },
                                            "required": ["material", "start_line", "end_line"],
                                        },
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

                # Check if index exists (CSV or MD)
                index_csv = f.with_name(f.stem + "_index.csv")
                index_md = f.with_name(f.stem + "_index.md")
                has_index = index_csv.exists() or index_md.exists()
                idx_mark = " [IDX]" if has_index else ""

                files.append(f"  - {f.name} ({line_count} 行){idx_mark}")

        return "\n".join(files) if files else "  (无文件)"

    def get_system_prompt(self) -> str:
        """Get the system prompt for progress initialization."""
        file_list = self._get_file_list()

        return f"""你是学习进度规划专家。你必须使用工具完成任务，禁止直接输出文字回复。

## 任务
为分类 "{self.category}" 生成学习进度条目。

## 工作目录
`{self.category_path}`

资料文件:
{file_list}

[IDX] = 有索引文件（文件名_index.md）

## 工具
1. **shell** - 执行只读shell命令（ls/grep/cat/sed等）
2. **submit_progress** - 提交进度条目（必须调用此工具结束任务）

## 工作流程

1. 用 shell 探索文件结构
2. 用 shell 分析内容（优先读索引文件，或用 grep -n 提取标题）
3. 调用 submit_progress 提交结果

## progress_id 格式
点分层级: `学科缩写.章节.小节.知识点`

缩写: ds(数据结构), os(操作系统), co(组成原理), cn(网络), math, phys, chem

示例: `ds.graph.mst.kruskal`, `os.process.schedule.fcfs`

## 输出要求

1. 只为核心知识点创建条目，跳过前言/目录/习题小结
2. 每章约5-15个条目
3. 名称用中文，可含英文术语
4. 每个条目必须有 related_sections 关联资料片段

## related_sections 格式

```json
{{
  "progress_id": "ds.graph.mst.kruskal",
  "name": "Kruskal算法",
  "related_sections": [
    {{"material": "图论.md", "start_line": 150, "end_line": 220, "desc": "正文"}},
    {{"material": "图论.md", "start_line": 450, "end_line": 480, "desc": "习题"}}
  ]
}}
```

⚠️ 重要：分析完成后必须调用 submit_progress 工具提交结果，不要直接输出文字。"""

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
