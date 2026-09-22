"""Sys2 (mimo) plan generator — calls mimo-v2.6-flash via OpenAI-compatible API."""

import json
from openai import OpenAI

MIMO_BASE_URL = "https://token-plan-sgp.xiaomimimo.com/v1"
MIMO_API_KEY = "tp-s68ox6lzznblmt5on73awj8lap5rd1eh0c8luttduvcfdsu7"
MIMO_MODEL = "mimo-v2.6-flash"

PLANNER_SYSTEM = """You are a browser test planner. Given a test instruction and the current page state, generate a numbered list of concrete browser actions to accomplish the goal.

RULES:
- Each step must be ONE atomic action: click, fill, navigate, or screenshot
- Be specific about WHAT to interact with (button text, field label, URL)
- Do NOT include "take a snapshot" or "observe" — the system handles that
- For fill actions, specify the value to enter
- Include screenshot steps ONLY for UI verification (design checks, visual regressions)
- Stop when the goal is complete — do not add extra steps

OUTPUT FORMAT (strict JSON):
{
  "steps": [
    {"action": "navigate", "target": "https://example.com/login", "note": "Go to login page"},
    {"action": "fill", "target": "email field", "value": "user@example.com", "note": "Enter email"},
    {"action": "click", "target": "Sign In button", "note": "Submit login form"},
    {"action": "screenshot", "note": "Verify login page design"},
    {"action": "done", "note": "All steps complete"}
  ]
}

ACTIONS:
- navigate: Go to a URL. target = URL.
- click: Click an element. target = description of element.
- fill: Fill an input. target = description of field, value = text to enter.
- press_key: Press a keyboard key. target = key name (Enter, Tab, etc.).
- screenshot: Take a screenshot. note = what to verify.
- done: All steps complete.
"""


def plan_steps(instruction: str, page_snapshot: str = "") -> list[dict]:
    """Generate a test plan from a high-level instruction.

    Args:
        instruction: User's test instruction (e.g. "Login and check leads").
        page_snapshot: Current page state (optional, helps planner see what's available).

    Returns:
        List of step dicts with 'action', 'target', optional 'value', 'note'.
    """
    client = OpenAI(base_url=MIMO_BASE_URL, api_key=MIMO_API_KEY)

    user_msg = f"Test instruction: {instruction}"
    if page_snapshot:
        user_msg += f"\n\nCurrent page state:\n{page_snapshot[:2000]}"

    response = client.chat.completions.create(
        model=MIMO_MODEL,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    try:
        plan = json.loads(content)
        return plan.get("steps", [])
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code block
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
            plan = json.loads(json_str)
            return plan.get("steps", [])
        raise ValueError(f"Failed to parse plan: {content}")
