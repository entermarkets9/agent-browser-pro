"""MCP server for browser test automation — Sys2 (mimo) + Sys1 (Von) + agent-browser."""

import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp import types

from orchestrator import run_test, run_single
import ab_executor


TOOLS = [
    Tool(
        name="browser_test",
        description="Run a full browser test from natural language. Sys2 (mimo) plans the steps, Sys1 (Von) picks elements, agent-browser executes. Returns a test report with timing and pass/fail.",
        inputSchema={
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "Test instruction, e.g. 'Login with test@example.com, go to leads, note first lead, logout'",
                }
            },
            "required": ["instruction"],
        },
    ),
    Tool(
        name="browser_step",
        description="Execute a single browser action. Von picks the element from the page snapshot.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "click", "fill", "press_key", "screenshot", "snapshot"],
                },
                "target": {"type": "string", "description": "Element description or URL or key name"},
                "value": {"type": "string", "description": "Value to fill (fill action only)"},
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="browser_open",
        description="Open a URL in the browser.",
        inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    ),
    Tool(
        name="browser_close",
        description="Close the browser session.",
        inputSchema={"type": "object", "properties": {}},
    ),
]


async def handle_list_tools(ctx, request):
    return types.ListToolsResult(tools=TOOLS)


async def handle_call_tool(ctx, request):
    name = request.name
    arguments = request.arguments or {}

    if name == "browser_test":
        result = await asyncio.to_thread(run_test, arguments["instruction"])
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(result, indent=2))])

    elif name == "browser_step":
        action = arguments["action"]
        target = arguments.get("target", "")
        value = arguments.get("value", "")

        if action == "snapshot":
            snapshot = await asyncio.to_thread(ab_executor.snapshot_compact)
            elements = await asyncio.to_thread(ab_executor.parse_interactive_elements, snapshot)
            result = {"snapshot": snapshot, "elements": elements, "element_count": len(elements)}
        elif action == "screenshot":
            filepath = arguments.get("target", f"screenshots/manual_{int(__import__('time').time())}.png")
            res = await asyncio.to_thread(ab_executor.screenshot, filepath)
            result = {"screenshot": filepath, "result": res}
        else:
            result = await asyncio.to_thread(run_single, action, target, value)

        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(result, indent=2))])

    elif name == "browser_open":
        res = await asyncio.to_thread(ab_executor.navigate, arguments["url"])
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"ok": True, "url": arguments["url"], "result": res}))])

    elif name == "browser_close":
        res = await asyncio.to_thread(ab_executor.close)
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"ok": True, "result": res}))])

    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))], isError=True)


async def main():
    server = Server(
        "browser-test",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
