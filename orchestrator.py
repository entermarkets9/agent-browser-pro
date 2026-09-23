"""Browser test orchestrator — Sys2 plans, Sys1 picks, agent-browser executes."""

import json
import time
import os
from typing import Any, Optional
from datetime import datetime

from sys1_von import pick_element
from sys2_mimo import plan_steps
import ab_executor


SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def run_test(instruction: str) -> dict[str, Any]:
    """Run a full browser test from natural language instruction.

    Pipeline:
    1. Sys2 (mimo) generates step plan
    2. For each step: Sys1 (Von) picks element → agent-browser executes
    3. Capture timing, screenshots, results

    Returns:
        Test report dict with steps, timing, pass/fail, screenshots.
    """
    report = {
        "instruction": instruction,
        "started_at": datetime.now().isoformat(),
        "steps": [],
        "screenshots": [],
        "total_duration_ms": 0,
        "pass": True,
    }

    total_start = time.time()

    # Step 1: Sys2 generates plan
    print(f"[Sys2] Planning: {instruction}")
    snapshot = ab_executor.snapshot_compact()
    plan = plan_steps(instruction, snapshot)
    print(f"[Sys2] Plan: {len(plan)} steps")

    # Step 2: Execute each step
    for i, step in enumerate(plan):
        step_result = _execute_step(i, step)
        report["steps"].append(step_result)

        if not step_result["success"]:
            report["pass"] = False
            print(f"[Step {i}] FAILED: {step_result.get('error', 'unknown')}")
            break
        else:
            print(f"[Step {i}] OK: {step.get('note', step.get('action', ''))}")

    report["total_duration_ms"] = int((time.time() - total_start) * 1000)
    report["finished_at"] = datetime.now().isoformat()

    return report


def _execute_step(index: int, step: dict) -> dict:
    """Execute a single test step.

    Returns step result dict with timing, success, details.
    """
    action = step.get("action", "")
    target = step.get("target", "")
    value = step.get("value", "")
    note = step.get("note", "")

    step_result = {
        "index": index,
        "action": action,
        "target": target,
        "value": value,
        "note": note,
        "success": False,
        "duration_ms": 0,
        "screenshot": None,
    }

    start = time.time()

    try:
        if action == "navigate":
            result = ab_executor.navigate(target)
            step_result["success"] = "error" not in result.lower()
            step_result["result"] = result

        elif action == "click":
            # Get snapshot, parse elements, ask Von to pick
            snapshot = ab_executor.snapshot_compact()
            elements = ab_executor.parse_interactive_elements(snapshot)
            chosen = pick_element(snapshot, f"Click the {target}", elements, filter_role="button")
            if not chosen:
                # Fallback: try all interactive elements
                chosen = pick_element(snapshot, f"Click the {target}", elements)
            if chosen:
                result = ab_executor.click(chosen["ref"])
                step_result["success"] = True
                step_result["chosen_ref"] = chosen["ref"]
                step_result["chosen_text"] = chosen.get("text", "")
                step_result["confidence"] = chosen.get("confidence", 0)
                step_result["result"] = result
            else:
                step_result["error"] = f"No element found for: {target}"

        elif action == "fill":
            # Get snapshot, find input fields, ask Von to pick
            snapshot = ab_executor.snapshot_compact()
            elements = ab_executor.parse_interactive_elements(snapshot)
            # Filter to input-like elements
            inputs = [e for e in elements if e["role"] in ("textbox", "input", "combobox")]
            if not inputs:
                inputs = elements  # fallback to all
            chosen = pick_element(snapshot, f"Fill the {target} field", inputs)
            if chosen:
                result = ab_executor.fill(chosen["ref"], value)
                step_result["success"] = True
                step_result["chosen_ref"] = chosen["ref"]
                step_result["chosen_text"] = chosen.get("text", "")
                step_result["confidence"] = chosen.get("confidence", 0)
                step_result["result"] = result
            else:
                step_result["error"] = f"No input found for: {target}"

        elif action == "press_key":
            result = ab_executor.press_key(target)
            step_result["success"] = True
            step_result["result"] = result

        elif action == "screenshot":
            filename = f"step_{index}_{int(time.time())}.png"
            filepath = os.path.join(SCREENSHOT_DIR, filename)
            result = ab_executor.screenshot(filepath)
            step_result["success"] = True
            step_result["screenshot"] = filepath
            step_result["result"] = result

        elif action == "done":
            step_result["success"] = True
            step_result["note"] = "Test complete"

        else:
            step_result["error"] = f"Unknown action: {action}"

    except Exception as e:
        step_result["error"] = str(e)

    step_result["duration_ms"] = int((time.time() - start) * 1000)
    return step_result


def run_single(action: str, target: str = "", value: str = "") -> dict:
    """Execute a single browser action via Sys1 (Von) + agent-browser.

    For when the caller already knows what to do but needs Von to find the element.
    """
    start = time.time()

    if action == "navigate":
        result = ab_executor.navigate(target)
        return {"success": True, "result": result, "duration_ms": int((time.time() - start) * 1000)}

    if action == "click":
        snapshot = ab_executor.snapshot_compact()
        elements = ab_executor.parse_interactive_elements(snapshot)
        chosen = pick_element(snapshot, f"Click the {target}", elements, filter_role="button")
        if not chosen:
            chosen = pick_element(snapshot, f"Click the {target}", elements)
        if chosen:
            result = ab_executor.click(chosen["ref"])
            return {
                "success": True,
                "ref": chosen["ref"],
                "text": chosen.get("text", ""),
                "confidence": chosen.get("confidence", 0),
                "result": result,
                "duration_ms": int((time.time() - start) * 1000),
            }
        return {"success": False, "error": f"No element found for: {target}"}

    if action == "fill":
        snapshot = ab_executor.snapshot_compact()
        elements = ab_executor.parse_interactive_elements(snapshot)
        inputs = [e for e in elements if e["role"] in ("textbox", "input", "combobox")]
        if not inputs:
            inputs = elements
        chosen = pick_element(snapshot, f"Fill the {target} field", inputs)
        if chosen:
            result = ab_executor.fill(chosen["ref"], value)
            return {
                "success": True,
                "ref": chosen["ref"],
                "text": chosen.get("text", ""),
                "confidence": chosen.get("confidence", 0),
                "result": result,
                "duration_ms": int((time.time() - start) * 1000),
            }
        return {"success": False, "error": f"No input found for: {target}"}

    if action == "press_key":
        result = ab_executor.press_key(target)
        return {
            "success": True,
            "result": result,
            "duration_ms": int((time.time() - start) * 1000),
        }

    return {"success": False, "error": f"Unknown action: {action}"}
