"""Integration tests for MCP server."""

import pytest

from studykb_mcp.server import HANDLERS, TOOLS, call_tool, list_tools


class TestMCPServer:
    """Integration tests for MCP server."""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test that list_tools returns all tools."""
        tools = await list_tools()

        assert len(tools) == 6
        tool_names = [t.name for t in tools]
        assert "read_overview" in tool_names
        assert "read_progress" in tool_names
        assert "update_progress" in tool_names
        assert "read_index" in tool_names
        assert "read_file" in tool_names
        assert "grep" in tool_names

    @pytest.mark.asyncio
    async def test_tool_definitions_have_descriptions(self):
        """Test that all tools have descriptions."""
        for tool in TOOLS:
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} description too short"

    @pytest.mark.asyncio
    async def test_tool_definitions_have_input_schema(self):
        """Test that all tools have input schema."""
        for tool in TOOLS:
            assert tool.inputSchema, f"Tool {tool.name} missing inputSchema"
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"

    @pytest.mark.asyncio
    async def test_all_tools_have_handlers(self):
        """Test that all tools have handlers."""
        tool_names = [t.name for t in TOOLS]
        for name in tool_names:
            assert name in HANDLERS, f"Tool {name} missing handler"

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Test calling an unknown tool."""
        result = await call_tool("unknown_tool", {})

        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_read_overview(self, sample_kb, monkeypatch):
        """Test calling read_overview through server."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await call_tool("read_overview", {})

        assert len(result) == 1
        assert "Knowledge Base Overview" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_read_progress(self, sample_progress, monkeypatch):
        """Test calling read_progress through server."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "progress_path", sample_progress)

        result = await call_tool("read_progress", {"category": "数据结构"})

        assert len(result) == 1
        assert "Progress: 数据结构" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_grep(self, sample_kb, monkeypatch):
        """Test calling grep through server."""
        from studykb_mcp.config import settings

        monkeypatch.setattr(settings, "kb_path", sample_kb)

        result = await call_tool("grep", {
            "category": "数据结构",
            "pattern": "Kruskal",
        })

        assert len(result) == 1
        assert "grep" in result[0].text


class TestToolSchemas:
    """Tests for tool input schemas."""

    def test_read_overview_schema(self):
        """Test read_overview has no required params."""
        tool = next(t for t in TOOLS if t.name == "read_overview")
        assert tool.inputSchema["required"] == []

    def test_read_progress_schema(self):
        """Test read_progress requires category."""
        tool = next(t for t in TOOLS if t.name == "read_progress")
        assert "category" in tool.inputSchema["required"]
        assert "category" in tool.inputSchema["properties"]

    def test_update_progress_schema(self):
        """Test update_progress required params."""
        tool = next(t for t in TOOLS if t.name == "update_progress")
        required = tool.inputSchema["required"]
        assert "category" in required
        assert "progress_id" in required
        assert "status" in required
        assert "comment" in required

    def test_read_index_schema(self):
        """Test read_index required params."""
        tool = next(t for t in TOOLS if t.name == "read_index")
        required = tool.inputSchema["required"]
        assert "category" in required
        assert "material" in required

    def test_read_file_schema(self):
        """Test read_file required params."""
        tool = next(t for t in TOOLS if t.name == "read_file")
        required = tool.inputSchema["required"]
        assert "category" in required
        assert "material" in required
        assert "start_line" in required
        assert "end_line" in required

    def test_grep_schema(self):
        """Test grep required params."""
        tool = next(t for t in TOOLS if t.name == "grep")
        required = tool.inputSchema["required"]
        assert "category" in required
        assert "pattern" in required
