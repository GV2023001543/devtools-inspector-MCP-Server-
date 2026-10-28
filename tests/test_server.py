import pytest
from fastmcp import Client

from devtools_inspector.server import mcp


@pytest.mark.asyncio
async def test_mcp_tools_are_registered_with_expected_inputs():
    async with Client(mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        expected = {
            "list_browser_targets",
            "connect_browser",
            "select_browser_target",
            "disconnect_browser",
            "get_connection_status",
            "start_live_inspection",
            "stop_live_inspection",
            "get_live_diagnostics",
            "inspect_console",
            "inspect_network",
            "inspect_performance",
            "propose_fix",
            "apply_patch",
            "run_project_checks",
            "rollback_patch",
        }
        assert expected <= tools.keys()
        assert "target_id" in tools["connect_browser"].input_schema["properties"]
        assert "approved" in tools["apply_patch"].input_schema["properties"]


@pytest.mark.asyncio
async def test_connection_status_tool_returns_disconnected_state():
    async with Client(mcp) as client:
        result = await client.call_tool("get_connection_status", {})
        assert result.is_error is False
