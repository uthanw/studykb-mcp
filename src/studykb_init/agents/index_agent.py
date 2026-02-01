"""Index creation agent for analyzing large files and generating chapter indexes."""

import asyncio
import shlex
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

from studykb_init.config import LLMConfig
from studykb_init.agents.base import AgentContext, BaseAgent, ToolDefinition


class IndexAgent(BaseAgent):
    """Agent for analyzing large Markdown files and generating chapter indexes.

    This agent uses native shell tools (wc, grep, sed, head, tail) to efficiently
    analyze file structure without loading the entire file into memory.
    All tools are read-only and cannot modify files.
    """

    def __init__(
        self,
        config: LLMConfig,
        console: Console,
        file_path: Path,
        material_name: str,
    ):
        """Initialize the index agent.

        Args:
            config: LLM API configuration.
            console: Rich console for output.
            file_path: Path to the file to analyze.
            material_name: Name of the material (for display in index).
        """
        self.file_path = file_path
        self.material_name = material_name
        context = AgentContext(console=console, file_path=str(file_path))
        super().__init__(config, console, context)

    def _setup_tools(self) -> None:
        """Register shell-based file analysis tools."""
        # shell - 通用只读shell命令
        self.register_tool(
            ToolDefinition(
                name="shell",
                description="""执行只读shell命令进行文件分析。
⚠️ 安全限制: 只允许读取操作，禁止任何写入/删除/修改命令。

允许的命令: wc, grep, sed, awk, head, tail, cat, sort, uniq, cut, tr, less, more
禁止的操作: >, >>, rm, mv, cp, chmod, chown, dd, tee 等任何写入操作

文件路径会自动替换: 在命令中使用 "file" 或 "$FILE" 代表目标文件。

常用命令示例:
  wc -l file                      # 统计文件行数
  grep -n "^# " file              # 提取所有一级标题及行号
  grep -n "^## " file             # 提取所有二级标题及行号
  grep -c "^# " file              # 统计标题数量
  sed -n '1,50p' file             # 读取第1-50行
  sed -n '100p' file              # 读取第100行
  head -50 file                   # 查看开头50行
  tail -50 file                   # 查看结尾50行
  tail -n +100 file               # 从第100行开始显示到末尾

管道组合示例:
  grep -n "^# " file | head -100  # 查看前100个标题
  sed -n '100,200p' file | grep "keyword"  # 在指定范围内搜索""",
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

        # submit_index - 提交索引
        self.register_tool(
            ToolDefinition(
                name="submit_index",
                description="提交生成的索引内容。这是最终输出工具，调用后Agent任务完成。索引内容必须是完整的Markdown格式。",
                parameters={
                    "type": "object",
                    "properties": {
                        "index_content": {
                            "type": "string",
                            "description": "完整的Markdown格式索引内容",
                        },
                    },
                    "required": ["index_content"],
                },
                handler=self._submit_index,
                is_terminal=True,
            )
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for index creation."""
        return f"""你是一位专业的文档索引专家，擅长分析大型文本文件并创建精确的、基于行号的导航索引。作为linux专家，你会灵活使用或组合shell命令，就像操作自己工作台一样顺手的执行读取操作。

## 当前任务

为资料 **"{self.material_name}"** 生成章节索引。
文件路径: `{self.file_path}`

## 核心职责

将大型 Markdown/文本文档转化为结构清晰、可精确检索的索引参考材料。

## 可用工具

1. **shell** - 执行只读 shell 命令分析文件
2. **submit_index** - 提交最终索引（调用后任务完成）

## 工作流程

### 阶段1: 文件评估
首先确定文件规模:
```bash
wc -l
```

### 阶段2: 快速标题提取
**关键技巧**: 对于有粗略结构的文件，不需要分块完整读取，使用 grep 搜索潜在的标题特征:
```bash
grep -n "^# "           # 提取所有 # 开头的标题及行号
grep -n "^## "          # 提取二级标题
grep -c "^#"            # 统计标题总数
```

### 阶段3: 详细检查
验证特定位置的内容:

当需要确认某个区间的具体内容时：

```bash
# 带行号输出指定区间
sed -n '起始行,结束行p' "文件名.md" | awk '{{print NR+起始行-1" | "$0}}'
```

### 阶段4: 构建索引
按标准格式创建索引（见下方格式要求）

### 阶段5: 验证并提交
- 随机抽查3-5个索引条目
- 用 sed 确认行号与内容匹配
- 调用 `submit_index` 提交最终索引

## 索引格式要求

```markdown
# 《{self.material_name}》章节索引

> 源文件: `{self.file_path.name}`
> 总行数: XXXX
> 格式: `起始行-结束行 | 描述`

## 📚 文件结构概览

| 部分 | 行号范围 | 说明 |
|------|---------|------|
| 前置内容 | 1-xxx | 封面、版权、前言等 |
| 目录 | xxx-xxx | 全书目录 |
| 正文 | xxx-xxx | N章正文内容 |
| 附录 | xxx-xxx | 附加内容(如有) |

## 第1章 章节名（起始行-结束行）

| 行号范围 | 内容 |
|---------|------|
| xxx-xxx | **1.1 节名** |
| xxx-xxx | 1.1.1 子节 |

[继续列出所有章节...]

## 🔍 快速查找

| 知识点 | 行号 | 章节 |
|-------|------|------|
| 重要概念1 | xxx-xxx | x.x |
| 核心算法1 | xxx-xxx | x.x |
```

## 关键提醒

1. **务必验证**: 创建索引后抽查多个条目确认准确性
2. **注意格式不一致**: 原文件可能有不规则的标题格式
3. **记录假设**: 在索引中注明任何不明确的情况（但应尽可能探明）
4. **高效工作**: 优先使用 grep 批量提取，仅在文档结构混乱或无结构时逐行读取
5. **少量读入**: 外科手术般，最小化接触读取
6. **尽快完成**: 每次工具调用应尽可能考虑高效，使用最少的工具调用次数完成探索

## 质量标准

- 每个索引条目必须包含准确的行号
- 描述简洁但信息丰富
- 相关章节逻辑分组
- 包含快速参考概览表
- 注明源文件名和总行数
- 快速查找表包含若干最重要的知识点

完成分析后，调用 `submit_index` 提交最终索引。"""

    async def _run_command(
        self, cmd: list[str], timeout: int = 30, max_output: int = 50000
    ) -> str:
        """Run a shell command and return output.

        Args:
            cmd: Command and arguments as list.
            timeout: Command timeout in seconds.
            max_output: Maximum output length.

        Returns:
            Command output or error message.
        """
        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ),
                timeout=timeout,
            )
            stdout, stderr = await result.communicate()

            output = stdout.decode("utf-8", errors="replace")
            if len(output) > max_output:
                output = output[:max_output] + f"\n... (输出截断，共 {len(stdout)} 字节)"

            if result.returncode != 0 and stderr:
                error = stderr.decode("utf-8", errors="replace")
                if error.strip():
                    output += f"\n[stderr]: {error[:500]}"

            return output if output.strip() else "(无输出)"

        except asyncio.TimeoutError:
            return f"命令超时 ({timeout}秒)"
        except Exception as e:
            return f"执行失败: {e}"

    async def _shell(self, command: str, **kwargs: Any) -> str:
        """Execute a read-only shell command."""
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

        # Replace placeholder with actual file path
        # Allow referencing the file as "file", "$FILE", or the actual filename
        actual_command = command.replace("$FILE", shlex.quote(str(self.file_path)))
        actual_command = actual_command.replace("file.md", shlex.quote(str(self.file_path)))
        actual_command = actual_command.replace("filename.md", shlex.quote(str(self.file_path)))

        # If command doesn't reference the file, append it for common commands
        if str(self.file_path) not in actual_command:
            # Check if it's a command that needs the file
            first_word = command.split()[0] if command.split() else ""
            if first_word in ["grep", "sed", "head", "tail", "cat", "wc", "awk"]:
                actual_command = f"{actual_command} {shlex.quote(str(self.file_path))}"

        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    actual_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
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

    async def _submit_index(self, index_content: str, **kwargs: Any) -> str:
        """Submit the generated index content."""
        self.set_result(index_content)
        return "索引已提交，任务完成。"
