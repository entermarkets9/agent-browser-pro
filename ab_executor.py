"""Agent-browser executor — calls agent-browser CLI for browser actions."""

import json
import subprocess
import re
import os
import shutil
from typing import Any, Optional

# Find agent-browser executable
_AB_PATH = shutil.which("agent-browser") or "agent-browser"
if os.name == "nt" and not _AB_PATH.endswith(".cmd"):
    cmd_path = _AB_PATH + ".cmd"
    if os.path.exists(cmd_path):
        _AB_PATH = cmd_path


def _run_ab(args: list[str], timeout: int = 15) -> str:
    """Run agent-browser command and return stdout."""
    cmd = [_AB_PATH] + args
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, shell=(os.name == "nt")
    )
    return result.stdout.strip()


def snapshot_compact() -> str:
    """Get compact interactive-only snapshot (~200-400 tokens)."""
    return _run_ab(["snapshot", "-i", "-c"], timeout=10)


def snapshot_full() -> str:
    """Get full page snapshot."""
    return _run_ab(["snapshot"], timeout=10)


def parse_interactive_elements(snapshot: str) -> list[dict[str, Any]]:
    """Parse agent-browser snapshot into structured element list.

    Input format (from `snapshot -i -c`):
        - button "Log In" [ref=e4]
        - textbox "Email" [ref=e5]
        - link "Learn more" [ref=e6]

    Returns list of dicts with ref, role, text, tag.
    Only returns actionable elements (button, textbox, link, input, combobox).
    """
    elements = []
    INTERACTIVE_ROLES = {"button", "textbox", "input", "link", "combobox", "checkbox", "radio", "switch", "tab", "menuitem", "spinbutton"}
    pattern = r'- (\w+)\s+"([^"]*)"\s+\[[^\]]*ref=(\w+)'
    for match in re.finditer(pattern, snapshot):
        role = match.group(1)
        if role.lower() not in INTERACTIVE_ROLES:
            continue
        text = match.group(2)
        ref_id = match.group(3)
        elements.append({
            "ref": f"@{ref_id}",
            "ref_id": ref_id,
            "role": role,
            "text": text,
            "tag": role,
        })
    return elements


def snapshot_to_von_text(elements: list[dict]) -> str:
    """Convert parsed elements to compact text for Von."""
    lines = []
    for e in elements:
        lines.append(f'- {e["role"]} "{e["text"]}" [ref={e["ref_id"]}]')
    return "\n".join(lines)


def navigate(url: str) -> str:
    """Navigate to a URL and wait for SPA to render."""
    result = _run_ab(["open", url], timeout=15)
    import time
    time.sleep(2)  # Wait for React SPA to render
    return result


def click(ref: str) -> str:
    """Click an element by @ref."""
    return _run_ab(["click", ref], timeout=10)


def fill(ref: str, value: str) -> str:
    """Fill an input field."""
    return _run_ab(["fill", ref, value], timeout=10)


def press_key(key: str) -> str:
    """Press a keyboard key."""
    return _run_ab(["press", key], timeout=10)


def screenshot(filename: Optional[str] = None) -> str:
    """Take a screenshot."""
    args = ["screenshot"]
    if filename:
        args.extend(["--output", filename])
    return _run_ab(args, timeout=10)


def get_url() -> str:
    """Get current page URL."""
    result = _run_ab(["eval", "window.location.href"], timeout=5)
    return result.strip('"')


def close() -> str:
    """Close the browser session."""
    return _run_ab(["close"], timeout=5)
