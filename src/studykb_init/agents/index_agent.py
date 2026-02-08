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
                description="提交生成的索引内容。这是最终输出工具，调用后Agent任务完成。索引内容必须是完整的CSV格式。",
                parameters={
                    "type": "object",
                    "properties": {
                        "index_content": {
                            "type": "string",
                            "description": "完整的CSV格式索引内容",
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
        return f"""你是一位专业的文档索引专家，擅长分析大型文本文件并创建完整、精确的基于行号的导航索引。作为linux专家，你会灵活使用shell命令高效完成读取操作，就像使用自己工作台一样轻松高效。

## 当前任务

为资料 **"{self.material_name}"** 生成完整章节索引。
文件路径: `{self.file_path}`

## 核心原则

**完整性是第一优先级。** 索引的价值在于覆盖文档的每一个章节、每一个小节，遗漏任何一个都会导致后续检索失败。宁可索引冗长，不可遗漏条目。

**高效是第二优先级。** 单次调用获取尽可能多的所需信息。有把握的操作一次完成，不要拆分。

## 可用工具

1. **shell** - 执行只读shell命令分析文件
2. **submit_index** - 提交最终索引（调用后任务完成）

## Shell使用哲学

**管道组合优于多次调用。** 一条命令通过管道完成提取、过滤、格式化，而非分三次调用。

**精准切割优于保守截断。** 除非是初次试探文件结构，否则不要使用 `head -50` 这类无意义截断。当你已知目标范围，就完整获取。

**试探性读取像外科手术：** 最小切口，快进快出。确定性读取像收割：一次扫完。


## 示例工作流程（根据实际使用最优工作流）

### 阶段1: 文件评估
```bash
wc -l "{self.file_path}" && grep -c "^#" "{self.file_path}" && grep -n "^#" "{self.file_path}" | head -30
```
这一次调用就能知道：总行数、标题总数、前30个标题的样貌。

### 阶段2: 详细内容索引
        
索引与验证：带行号输出指定区间  
```bash                                  
sed -n '起始行,结束行p' "文件名.md" | awk '{{print NR+起始行-1" | "$0}}'                                        
```

对于有粗略结构的文件，不需要分块完整读取，使用 grep 搜索潜在的标题特征。
对于非Markdown格式，识别模式后进行提取。
对于没有任何标题的长篇内容，需读入后进行总结。

### 阶段3: 补充验证
        
### 阶段4: 构建完整索引

### 阶段5: 快速验证后立即提交

进行1-2次关键抽查，确认无误后**立即**调用submit_index。不要逐条验证，不要反复确认。

## 索引格式

CSV格式，逗号分隔。标题含逗号时用双引号包裹。

**行类型：**
- `#meta` — 元信息
- `#type` — 字段声明（仅一次）
- `overview` — 文档结构概览（按大的部分划分）
- `chapter` — 章节条目，depth表示层级（0=章, 1=节, 2=小节, 3=更深层级...）
- `lookup` — 快速查找条目

**完整示例（注意：实际索引中每个章节都必须出现）：**

```
#meta,source,example_book.md
#meta,total_lines,15420
#meta,title_count,127
#type,depth,number,title,start,end,tags
overview,0,,前置内容,1,89,封面;版权;序言
overview,0,,第一部分 基础篇,90,5230,第1-4章
overview,0,,第二部分 进阶篇,5231,12000,第5-9章
overview,0,,第三部分 实战篇,12001,15420,第10-12章
chapter,0,1,初识Python,90,892,入门;环境搭建
chapter,1,1.1,Python的历史与特点,95,156,
chapter,2,1.1.1,Python的诞生背景,98,112,Guido
chapter,2,1.1.2,Python的设计哲学,113,142,
chapter,2,1.1.3,Python的应用领域,143,156,
chapter,1,1.2,开发环境搭建,157,289,安装;配置
chapter,2,1.2.1,Windows环境配置,160,198,
chapter,2,1.2.2,macOS环境配置,199,237,
chapter,2,1.2.3,Linux环境配置,238,276,
chapter,2,1.2.4,IDE选择与配置,277,289,PyCharm;VSCode
chapter,1,1.3,第一个Python程序,290,412,Hello World
chapter,2,1.3.1,编写代码,293,320,
chapter,2,1.3.2,运行程序,321,358,
chapter,2,1.3.3,常见错误排查,359,412,
chapter,0,2,数据类型与变量,413,1156,
chapter,1,2.1,变量与命名规范,418,512,
chapter,2,2.1.1,变量的定义,420,456,
chapter,2,2.1.2,命名规则,457,489,PEP8
chapter,2,2.1.3,保留字,490,512,
chapter,1,2.2,基本数据类型,513,845,
chapter,2,2.2.1,数字类型,516,612,int;float;complex
chapter,2,2.2.2,字符串,613,756,str;编码
chapter,2,2.2.3,布尔类型,757,798,bool;True;False
chapter,2,2.2.4,None类型,799,845,
lookup,,,,2156,2198,列表推导式;list comprehension|3.2.4
lookup,,,,4523,4612,装饰器;decorator;@|5.3
lookup,,,,8934,9012,GIL;全局解释器锁|7.2.1
```

## 完整性检查清单

在提交前**快速**确认（心理检查即可，不需要为每项都执行shell命令）：
- [ ] grep提取的每一个标题都已转换为chapter条目
- [ ] 章节编号连续无跳跃（如有1.1、1.2，检查是否遗漏1.3）
- [ ] depth层级正确反映文档结构
- [ ] overview条目覆盖文档从头到尾的所有区域
- [ ] lookup包含文档中最重要的5-15个核心概念

## 效率要求

- **禁止过度验证**：信息充分后立即构建索引并提交，1-2次关键抽查足矣
- **禁止反复试探同一区域**：一次获取足够信息，不要对同一范围多次读取
- **典型工具调用次数：3-12次**（评估1次 + 完整提取1-8次 + 可疑区间验证0-1次 + 抽查1-2次 + 提交1次）

## 禁止事项

- **禁止省略任何章节**：即使文档有100个小节，索引中也必须出现100个小节条目
- **禁止使用省略号或"等"来代替实际内容**
- **禁止跳过"看起来不重要"的章节**
- **禁止合并多个章节为一个条目**
- **禁止无意义的截断**：不要对已知需要完整获取的内容使用head/tail限制

## 完成标志

当且仅当索引覆盖了文档的全部章节结构后，调用submit_index提交。"""

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
        import re as _re

        # Security check - block dangerous operations
        # 先剥离引号和 awk/sed 脚本内容，避免脚本内的 > 等字符被误拦
        # 移除单引号包裹的内容（awk '{...}', sed 's/.../.../' 等）
        stripped = _re.sub(r"'[^']*'", "''", command)
        # 移除双引号包裹的内容
        stripped = _re.sub(r'"[^"]*"', '""', stripped)

        dangerous_patterns = [
            (">>", ">>"),       # Append redirect
            (" > ", ">"),       # Output redirect (with spaces)
            ("\t>", ">"),       # Output redirect (after tab)
            ("1>", ">"),        # fd redirect
            ("2>", ">"),        # stderr redirect
            ("rm ", "rm"),
            ("rm\t", "rm"),
            ("rmdir", "rmdir"),
            ("mv ", "mv"),
            ("mv\t", "mv"),
            ("cp ", "cp"),
            ("cp\t", "cp"),
            ("chmod", "chmod"),
            ("chown", "chown"),
            ("dd ", "dd"),
            ("tee ", "tee"),
            ("truncate", "truncate"),
            ("shred", "shred"),
            ("mkfs", "mkfs"),
            ("fdisk", "fdisk"),
            ("sudo", "sudo"),
            ("su ", "su"),
            ("curl", "curl"),
            ("wget", "wget"),
            ("; rm", "rm"),
            ("| rm", "rm"),
            ("&& rm", "rm"),
        ]

        stripped_lower = stripped.lower()
        for pattern, label in dangerous_patterns:
            if pattern in stripped_lower:
                return f"安全限制: 不允许使用 '{label}' 操作。只允许读取命令。"

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
