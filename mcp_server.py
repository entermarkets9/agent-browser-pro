"""MCP server for browser test automation — Sys2 (mimo) + Sys1 (Von) + agent-browser."""

import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from orchestrator import run_test, run_single
import ab_executor

app = Server("browser-test")


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="browser_test",
            description="Run a full browser test from natural language. Sys2 (mimo) plans the steps, Sys1 (Von) picks elements, agent-browser executes. Returns a test report with timing and pass/fail.",
            inputSchema={
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Test instruction in natural language, e.g. 'Login with test@example.com, go to leads, note first lead, logout'",
                    }
                },
                "required": ["instruction"],
            },
        ),
        Tool(
            name="browser_step",
            description="Execute a single browser action. Von picks the element from the page snapshot. Use for step-by-step control.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["navigate", "click", "fill", "press_key", "screenshot", "snapshot"],
                        "description": "Action to perform",
                    },
                    "target": {
                        "type": "string",
                        "description": "Element description (for click/fill), URL (for navigate), or key name (for press_key)",
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to fill (for fill action only)",
                    },
                },
                "required": ["action"],
            },
        ),
        Tool(
            name="browser_open",
            description="Open a URL in the browser.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open"}
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="browser_close",
            description="Close the browser session.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "browser_test":
        result = await asyncio.to_thread(run_test, arguments["instruction"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

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
            result = await asyncio.to_thread(ab_executor.screenshot, filepath)
            result = {"screenshot": filepath, "result": result}
        else:
            result = await asyncio.to_thread(run_single, action, target, value)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "browser_open":
        result = await asyncio.to_thread(ab_executor.navigate, arguments["url"])
        return [TextContent(type="text", text=json.dumps({"ok": True, "url": arguments["url"], "result": result}))]

    elif name == "browser_close":
        result = await asyncio.to_thread(ab_executor.close)
        return [TextContent(type="text", text=json.dumps({"ok": True, "result": result}))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
