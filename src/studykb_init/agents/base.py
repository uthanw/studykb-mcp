"""Base agent class for LLM-powered initialization tasks."""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

import httpx
import tiktoken
from rich.console import Console
from rich.live import Live
from rich.text import Text

from studykb_init.config import LLMConfig


def _count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # 对于未知模型，使用 cl100k_base（GPT-4 使用的编码）
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def _count_messages_tokens(messages: list[dict[str, Any]], model: str = "gpt-4") -> int:
    """Count tokens in a list of messages."""
    total = 0
    for msg in messages:
        # 每条消息有固定开销
        total += 4  # <|im_start|>{role}\n ... <|im_end|>\n
        if "content" in msg and msg["content"]:
            total += _count_tokens(str(msg["content"]), model)
        if "tool_calls" in msg:
            # tool_calls 序列化计算
            total += _count_tokens(json.dumps(msg["tool_calls"], ensure_ascii=False), model)
    total += 2  # 结尾
    return total


def _format_tokens(n: int) -> str:
    """Format token count with K/M suffix for large numbers."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}k"
    else:
        return str(n)


@dataclass
class ToolDefinition:
    """Definition of a tool that can be used by an agent."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, str]]
    is_terminal: bool = False  # If True, calling this tool ends the agent loop


@dataclass
class AgentContext:
    """Context passed to tool handlers."""

    console: Console
    file_path: Optional[str] = None
    work_dir: Optional[str] = None  # Working directory for shell commands
    category: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for LLM-powered agents.

    Agents use tools to complete tasks. The agent runs in a loop:
    1. Call LLM with messages and available tools
    2. If LLM returns tool calls, execute them and add results to messages
    3. Repeat until LLM returns a final response or a terminal tool is called
    """

    def __init__(
        self,
        config: LLMConfig,
        console: Console,
        context: Optional[AgentContext] = None,
    ):
        """Initialize the agent.

        Args:
            config: LLM API configuration.
            console: Rich console for output.
            context: Optional context for tool handlers.
        """
        self.config = config
        self.console = console
        self.context = context or AgentContext(console=console)
        self.tools: dict[str, ToolDefinition] = {}
        self._result: Any = None  # Store terminal tool result
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._current_context_tokens = 0  # 当前 messages 上下文大小
        self._setup_tools()

    @abstractmethod
    def _setup_tools(self) -> None:
        """Register available tools. Subclasses must implement this."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent. Subclasses must implement this."""
        pass

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool for the agent to use."""
        self.tools[tool.name] = tool

    async def run(self, user_message: str, max_iterations: int = 100) -> Any:
        """Run the agent with the given user message.

        Args:
            user_message: Initial user message to send to the agent.
            max_iterations: Maximum number of LLM calls to prevent infinite loops.

        Returns:
            The result from the terminal tool, or the final LLM response.
        """
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": user_message},
        ]

        self._result = None
        self._start_time = time.time()
        iteration = 0

        # 启动总计时器显示任务
        self._timer_running = True
        timer_task = asyncio.create_task(self._show_elapsed_timer())

        try:
            while iteration < max_iterations:
                iteration += 1

                response = await self._call_llm(messages)

                # Check if response has tool calls
                tool_calls = response.get("tool_calls")

                if tool_calls:
                    # Add assistant message with tool calls
                    messages.append(response)

                    # Execute each tool call
                    for tool_call in tool_calls:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])

                        # 显示工具调用和参数
                        if tool_name == "shell" and "command" in tool_args:
                            # shell 工具直接显示命令
                            self.console.print(f"  [cyan]$ {tool_args['command']}[/cyan]")
                        elif tool_args:
                            # 其他工具显示 JSON 参数
                            args_str = json.dumps(tool_args, ensure_ascii=False)
                            if len(args_str) > 200:
                                args_str = args_str[:200] + "..."
                            self.console.print(f"  [dim]→ {tool_name}({args_str})[/dim]")
                        else:
                            self.console.print(f"  [dim]→ {tool_name}()[/dim]")

                        # Execute tool
                        result = await self._execute_tool(tool_name, tool_args)

                        # Display tool result preview (truncated)
                        result_preview = result[:300] if len(result) > 300 else result
                        if len(result) > 300:
                            result_preview += f"... ({len(result)} 字符)"
                        # Show result in gray/dim
                        for line in result_preview.split("\n")[:5]:
                            self.console.print(f"    [dim]{line}[/dim]")
                        if result_preview.count("\n") > 5:
                            self.console.print(f"    [dim]... (更多行省略)[/dim]")

                        # Add tool result to messages
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result,
                            }
                        )

                        # Check if this was a terminal tool
                        if tool_name in self.tools and self.tools[tool_name].is_terminal:
                            return self._result

                else:
                    # No tool calls, return the content
                    return response.get("content", "")

            self.console.print("[yellow]警告: 达到最大迭代次数[/yellow]")
            return self._result

        finally:
            # 停止计时器
            self._timer_running = False
            timer_task.cancel()
            try:
                await timer_task
            except asyncio.CancelledError:
                pass
            # 显示最终耗时和 token 统计
            total_time = time.time() - self._start_time
            self.console.print(
                f"\n[green]✓ 任务完成，总耗时 {total_time:.1f}s[/green] "
                f"[dim](↑{_format_tokens(self._total_input_tokens)} ↓{_format_tokens(self._total_output_tokens)} tokens)[/dim]"
            )

    def _is_websocket_console(self) -> bool:
        """检测 console 是否为 WebSocketConsole（非 Rich Console）。"""
        return not isinstance(self.console, Console)

    async def _show_elapsed_timer(self) -> None:
        """显示持续运行的总计时器和 token 统计。"""
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spinner_idx = 0

        if self._is_websocket_console():
            # WebSocket 模式：定期通过 print 发送进度消息
            while self._timer_running:
                elapsed = time.time() - self._start_time
                spinner = spinner_chars[spinner_idx % len(spinner_chars)]
                spinner_idx += 1

                status_text = (
                    f"{spinner} 分析中 [{elapsed:.1f}s] "
                    f"ctx:{_format_tokens(self._current_context_tokens)} "
                    f"↑{_format_tokens(self._total_input_tokens)} "
                    f"↓{_format_tokens(self._total_output_tokens)}"
                )
                self.console.print(status_text)
                await asyncio.sleep(2)  # WebSocket 模式下降低频率，避免消息过多
        else:
            # Rich Console 模式：使用 Live 实时刷新
            with Live(console=self.console, refresh_per_second=4, transient=True) as live:
                while self._timer_running:
                    elapsed = time.time() - self._start_time
                    spinner = spinner_chars[spinner_idx % len(spinner_chars)]
                    spinner_idx += 1

                    text = Text()
                    text.append(f"{spinner} ", style="cyan")
                    text.append("分析中 ", style="bold")
                    text.append(f"[{elapsed:.1f}s] ", style="cyan dim")
                    text.append(f"ctx:{_format_tokens(self._current_context_tokens)} ", style="magenta dim")
                    text.append(f"↑{_format_tokens(self._total_input_tokens)} ", style="yellow dim")
                    text.append(f"↓{_format_tokens(self._total_output_tokens)}", style="green dim")
                    live.update(text)

                    await asyncio.sleep(0.25)

    async def _call_llm(
        self, messages: list[dict[str, Any]], max_retries: int = 3
    ) -> dict[str, Any]:
        """Call the LLM API with retry logic.

        Args:
            messages: List of messages to send.
            max_retries: Maximum number of retry attempts.

        Returns:
            The assistant message from the response.
        """
        # 计算输入 tokens (messages)
        messages_tokens = _count_messages_tokens(messages, self.config.model)

        # Build tools schema
        tools_schema = []
        for tool in self.tools.values():
            tools_schema.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )

        # tools schema 也算输入 tokens
        tools_tokens = 0
        if tools_schema:
            tools_tokens = _count_tokens(json.dumps(tools_schema, ensure_ascii=False), self.config.model)

        input_tokens = messages_tokens + tools_tokens
        # 更新当前上下文大小
        self._current_context_tokens = messages_tokens

        request_body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if tools_schema:
            request_body["tools"] = tools_schema

        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.config.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.config.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=request_body,
                        timeout=120.0,
                    )
                    response.raise_for_status()
                    result = response.json()

                # 累计输入 tokens
                self._total_input_tokens += input_tokens

                # 计算输出 tokens
                assistant_msg = result["choices"][0]["message"]
                output_tokens = 0
                if assistant_msg.get("content"):
                    output_tokens += _count_tokens(assistant_msg["content"], self.config.model)
                if assistant_msg.get("tool_calls"):
                    output_tokens += _count_tokens(
                        json.dumps(assistant_msg["tool_calls"], ensure_ascii=False),
                        self.config.model
                    )
                self._total_output_tokens += output_tokens

                return assistant_msg

            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                    self.console.print(
                        f"  [yellow]连接错误，{wait_time}秒后重试 ({attempt + 1}/{max_retries})...[/yellow]"
                    )
                    await asyncio.sleep(wait_time)
                continue

        raise last_error or Exception("LLM API 调用失败")

    async def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments to pass to the tool.

        Returns:
            Tool execution result as string.
        """
        if tool_name not in self.tools:
            return f"错误: 未知工具 '{tool_name}'"

        tool = self.tools[tool_name]

        try:
            result = await tool.handler(**arguments)
            return result
        except Exception as e:
            return f"工具执行错误: {e}"

    def set_result(self, result: Any) -> None:
        """Set the result to be returned when a terminal tool is called.

        This should be called by terminal tool handlers.
        """
        self._result = result
