"""TUI CLI for StudyKB initialization tools."""

import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from studykb_init.config import InitSettings, ensure_api_configured, load_config, save_config
from studykb_init.agents.index_agent import IndexAgent
from studykb_init.agents.progress_agent import ProgressAgent
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
from studykb_init.services.progress_service import ProgressService

console = Console()


class InitCLI:
    """Interactive CLI for StudyKB initialization."""

    def __init__(self) -> None:
        """Initialize the CLI."""
        self.settings = load_config()
        self.progress_service = ProgressService()

    async def run(self) -> None:
        """Run the main CLI loop."""
        console.print(
            Panel.fit(
                "[bold blue]StudyKB 知识库初始化工具[/bold blue]\n"
                "用于创建分类、导入资料、生成索引和初始化进度",
                border_style="blue",
            )
        )

        while True:
            console.print("\n[bold]请选择操作:[/bold]")
            console.print("  1. 创建新分类")
            console.print("  2. 导入资料文件")
            console.print("  3. 为资料生成索引 [dim](Agent)[/dim]")
            console.print("  4. 初始化学习进度 [dim](Agent)[/dim]")
            console.print("  5. 完整初始化流程 [dim](1-4一键完成)[/dim]")
            console.print("  6. 配置 LLM API")
            console.print("  0. 退出")

            choice = Prompt.ask(
                "\n请输入选项", choices=["0", "1", "2", "3", "4", "5", "6"], default="0"
            )

            try:
                if choice == "0":
                    console.print("[dim]再见！[/dim]")
                    break
                elif choice == "1":
                    await self.handle_create_category()
                elif choice == "2":
                    await self.handle_import_file()
                elif choice == "3":
                    await self.handle_create_index()
                elif choice == "4":
                    await self.handle_init_progress()
                elif choice == "5":
                    await self.handle_full_init()
                elif choice == "6":
                    await self.handle_configure_api()
            except KeyboardInterrupt:
                console.print("\n[yellow]操作已取消[/yellow]")
            except Exception as e:
                console.print(f"[red]错误: {e}[/red]")

    async def handle_create_category(self) -> None:
        """Handle category creation."""
        console.print("\n[bold]== 创建新分类 ==[/bold]")

        # Show existing categories
        categories = await list_categories()
        if categories:
            console.print(f"现有分类: {', '.join(categories)}")

        name = Prompt.ask("请输入新分类名称")
        if not name:
            console.print("[yellow]已取消[/yellow]")
            return

        success, message = await create_category(name)
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")

    async def handle_import_file(self) -> Optional[tuple[str, str]]:
        """Handle file import.

        Returns:
            Tuple of (category, material_name) if successful, None otherwise.
        """
        console.print("\n[bold]== 导入资料文件 ==[/bold]")

        # Select category
        category = await self._select_category()
        if not category:
            return None

        # Get source file path
        source_path_str = Prompt.ask("请输入 MD 文件路径")
        if not source_path_str:
            console.print("[yellow]已取消[/yellow]")
            return None

        source_path = Path(source_path_str).expanduser().resolve()

        # Check if file exists in category
        target_name = source_path.stem
        existing_info = await get_file_info(category, target_name)

        overwrite = False
        if existing_info:
            overwrite = Confirm.ask(
                f"文件 '{target_name}.md' 已存在 ({existing_info['line_count']} 行)，是否覆盖?"
            )
            if not overwrite:
                console.print("[yellow]已取消[/yellow]")
                return None

        # Import file
        success, message, file_info = await import_file(
            source_path, category, overwrite=overwrite
        )

        if success:
            console.print(f"[green]✓ {message}[/green]")
            if file_info:
                console.print(f"  文件大小: {file_info['line_count']} 行")

                # Ask about generating index for large files
                if file_info["line_count"] > 1000:
                    if Confirm.ask("文件较大，是否立即生成索引?"):
                        await self.handle_create_index(category, file_info["name"])

            return category, target_name
        else:
            console.print(f"[red]✗ {message}[/red]")
            return None

    async def handle_create_index(
        self, category: Optional[str] = None, material: Optional[str] = None
    ) -> Optional[str]:
        """Handle index creation with agent.

        Returns:
            Index content if successful, None otherwise.
        """
        console.print("\n[bold]== 生成资料索引 ==[/bold]")

        # Check API configuration
        if not ensure_api_configured(self.settings):
            console.print("[yellow]请先配置 LLM API (选项 6)[/yellow]")
            return None

        # Select category and material if not provided
        if not category:
            category = await self._select_category()
            if not category:
                return None

        if not material:
            material = await self._select_material(category)
            if not material:
                return None

        # Get file info
        file_info = await get_file_info(category, material)
        if not file_info:
            console.print(f"[red]资料 '{material}' 不存在[/red]")
            return None

        # Check for existing index
        existing_index = await read_index(category, material)
        if existing_index:
            if not Confirm.ask("索引文件已存在，是否重新生成?"):
                return existing_index

        file_path = Path(file_info["path"])

        console.print(f"\n目标: {category}/{material}.md ({file_info['line_count']} 行)")

        # Create and run agent
        agent = IndexAgent(
            config=self.settings.llm,
            console=console,
            file_path=file_path,
            material_name=material,
        )

        index_content = None
        try:
            index_content = await agent.run(f"请为文件 {material}.md 生成章节索引")
        except Exception as e:
            console.print(f"[red]Agent 执行失败: {e}[/red]")
            return None

        if not index_content:
            console.print("[red]Agent 未返回索引内容[/red]")
            return None

        # Show preview
        console.print("\n[bold]索引预览:[/bold]")
        preview = index_content[:2000]
        if len(index_content) > 2000:
            preview += f"\n... (共 {len(index_content)} 字符)"
        console.print(Panel(preview, border_style="dim"))

        # Ask to save
        if Confirm.ask("是否保存此索引?"):
            success, message = await save_index(
                category, material, index_content, overwrite=True
            )
            if success:
                console.print(f"[green]✓ {message}[/green]")
                return index_content
            else:
                console.print(f"[red]✗ {message}[/red]")
                return None
        else:
            console.print("[yellow]已取消保存[/yellow]")
            return index_content

    async def handle_init_progress(
        self, category: Optional[str] = None
    ) -> bool:
        """Handle progress initialization with agent.

        Args:
            category: Optional category name. If not provided, user will be prompted.

        Returns:
            True if successful, False otherwise.
        """
        console.print("\n[bold]== 初始化学习进度 ==[/bold]")

        # Check API configuration
        if not ensure_api_configured(self.settings):
            console.print("[yellow]请先配置 LLM API (选项 6)[/yellow]")
            return False

        # Select category if not provided
        if not category:
            category = await self._select_category()
            if not category:
                return False

        # Get category path
        category_path = self.settings.kb_path / category

        if not category_path.exists():
            console.print(f"[red]分类目录不存在: {category_path}[/red]")
            return False

        # Check if there are material files
        materials = await get_category_materials(category)
        if not materials:
            console.print(f"[yellow]分类 '{category}' 中没有资料文件[/yellow]")
            return False

        # Show materials info
        console.print(f"\n目标分类: {category}")
        console.print(f"资料文件:")
        for m in materials:
            idx_mark = "[IDX]" if m["has_index"] else ""
            console.print(f"  - {m['name']} ({m['line_count']} 行) {idx_mark}")

        # Create and run agent
        agent = ProgressAgent(
            config=self.settings.llm,
            console=console,
            category=category,
            category_path=category_path,
        )

        entries = None
        try:
            entries = await agent.run(f"请为分类 '{category}' 生成学习进度条目")
        except Exception as e:
            console.print(f"[red]Agent 执行失败: {e}[/red]")
            return False

        if not entries or not isinstance(entries, list):
            console.print("[red]Agent 未返回有效的进度条目[/red]")
            return False

        # Show preview
        table = Table(title=f"生成的进度条目 ({len(entries)} 个)")
        table.add_column("progress_id", style="cyan")
        table.add_column("name", style="green")

        for entry in entries[:20]:
            table.add_row(entry.get("progress_id", ""), entry.get("name", ""))

        if len(entries) > 20:
            table.add_row("...", f"还有 {len(entries) - 20} 个")

        console.print(table)

        # Ask to save
        if Confirm.ask("是否保存这些进度条目?"):
            # Create progress entries
            created_count = 0
            for entry in entries:
                try:
                    await self.progress_service.update_progress(
                        category=category,
                        progress_id=entry["progress_id"],
                        status="pending",
                        name=entry["name"],
                        comment="",
                    )
                    created_count += 1
                except Exception as e:
                    console.print(f"[red]创建失败: {entry.get('progress_id')}: {e}[/red]")

            console.print(f"[green]✓ 已创建 {created_count} 个进度条目[/green]")
            return True
        else:
            console.print("[yellow]已取消保存[/yellow]")
            return False

    async def handle_full_init(self) -> None:
        """Handle full initialization flow."""
        console.print("\n[bold]== 完整初始化流程 ==[/bold]")
        console.print("此流程将引导你完成: 创建分类 → 导入文件 → 生成索引 → 初始化进度")

        # Check API configuration
        if not ensure_api_configured(self.settings):
            console.print("[yellow]请先配置 LLM API[/yellow]")
            await self.handle_configure_api()
            if not ensure_api_configured(self.settings):
                console.print("[red]API 未配置，无法继续[/red]")
                return

        if not Confirm.ask("\n是否继续?"):
            return

        # Step 1: Create or select category
        console.print("\n[bold cyan]步骤 1/4: 分类[/bold cyan]")
        categories = await list_categories()

        if categories:
            console.print(f"现有分类: {', '.join(categories)}")
            use_existing = Confirm.ask("是否使用现有分类?")
            if use_existing:
                category = await self._select_category()
            else:
                name = Prompt.ask("请输入新分类名称")
                success, message = await create_category(name)
                if not success:
                    console.print(f"[red]{message}[/red]")
                    return
                console.print(f"[green]✓ {message}[/green]")
                category = name
        else:
            name = Prompt.ask("请输入新分类名称")
            success, message = await create_category(name)
            if not success:
                console.print(f"[red]{message}[/red]")
                return
            console.print(f"[green]✓ {message}[/green]")
            category = name

        if not category:
            return

        # Step 2: Import file
        console.print("\n[bold cyan]步骤 2/4: 导入资料[/bold cyan]")

        # Check if materials already exist
        materials = await get_category_materials(category)
        material = None

        if materials:
            console.print("该分类已有以下资料:")
            for m in materials:
                idx_mark = "[IDX]" if m["has_index"] else ""
                console.print(f"  - {m['name']} ({m['line_count']} 行) {idx_mark}")

            use_existing = Confirm.ask("是否使用现有资料?")
            if use_existing:
                material = await self._select_material(category)
            else:
                result = await self.handle_import_file()
                if result:
                    _, material = result
        else:
            source_path_str = Prompt.ask("请输入 MD 文件路径")
            if source_path_str:
                source_path = Path(source_path_str).expanduser().resolve()
                success, message, file_info = await import_file(source_path, category)
                if success:
                    console.print(f"[green]✓ {message}[/green]")
                    material = file_info["name"]
                else:
                    console.print(f"[red]{message}[/red]")
                    return

        if not material:
            console.print("[red]未选择资料，流程终止[/red]")
            return

        # Step 3: Generate index
        console.print("\n[bold cyan]步骤 3/4: 生成索引[/bold cyan]")
        file_info = await get_file_info(category, material)

        if file_info and file_info.get("has_index"):
            console.print(f"索引文件已存在")
            if not Confirm.ask("是否重新生成?"):
                pass
            else:
                await self.handle_create_index(category, material)
        else:
            await self.handle_create_index(category, material)

        # Step 4: Initialize progress
        console.print("\n[bold cyan]步骤 4/4: 初始化进度[/bold cyan]")
        await self.handle_init_progress(category)

        console.print("\n[bold green]✓ 初始化流程完成![/bold green]")

    async def handle_configure_api(self) -> None:
        """Handle API configuration."""
        console.print("\n[bold]== 配置 LLM API ==[/bold]")

        current = self.settings.llm
        console.print(f"\n当前配置:")
        console.print(f"  Base URL: {current.base_url}")
        console.print(f"  API Key: {'*' * 8 if current.api_key else '(未设置)'}")
        console.print(f"  Model: {current.model}")

        console.print("\n请输入新配置 (直接回车保持当前值):")

        base_url = Prompt.ask("Base URL", default=current.base_url)
        api_key = Prompt.ask("API Key", default=current.api_key)
        model = Prompt.ask("Model", default=current.model)
        temperature = float(
            Prompt.ask("Temperature", default=str(current.temperature))
        )
        max_tokens = int(Prompt.ask("Max Tokens", default=str(current.max_tokens)))

        self.settings.llm.base_url = base_url
        self.settings.llm.api_key = api_key
        self.settings.llm.model = model
        self.settings.llm.temperature = temperature
        self.settings.llm.max_tokens = max_tokens

        save_config(self.settings)
        console.print(f"[green]✓ 配置已保存到 {self.settings.config_path}[/green]")

    async def _select_category(self) -> Optional[str]:
        """Show category selection prompt.

        Returns:
            Selected category name or None.
        """
        categories = await list_categories()

        if not categories:
            console.print("[yellow]没有可用的分类，请先创建分类[/yellow]")
            return None

        console.print("\n可用分类:")
        for i, cat in enumerate(categories, 1):
            materials = await get_category_materials(cat)
            console.print(f"  {i}. {cat} ({len(materials)} 个资料)")

        choices = [str(i) for i in range(1, len(categories) + 1)]
        idx = Prompt.ask("选择分类", choices=choices)

        return categories[int(idx) - 1]

    async def _select_material(
        self, category: str, require_index: bool = False
    ) -> Optional[str]:
        """Show material selection prompt.

        Args:
            category: Category to list materials from.
            require_index: If True, only show materials with index.

        Returns:
            Selected material name or None.
        """
        materials = await get_category_materials(category)

        if require_index:
            materials = [m for m in materials if m["has_index"]]

        if not materials:
            msg = "没有可用的资料"
            if require_index:
                msg += " (需要索引文件)"
            console.print(f"[yellow]{msg}[/yellow]")
            return None

        console.print(f"\n分类 '{category}' 中的资料:")
        for i, m in enumerate(materials, 1):
            idx_mark = "[IDX]" if m["has_index"] else ""
            console.print(f"  {i}. {m['name']} ({m['line_count']} 行) {idx_mark}")

        choices = [str(i) for i in range(1, len(materials) + 1)]
        idx = Prompt.ask("选择资料", choices=choices)

        return materials[int(idx) - 1]["name"]


def main() -> None:
    """CLI entry point."""
    cli = InitCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()
