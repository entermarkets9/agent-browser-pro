"""Sys1 (Von) element picker — calls local Von server for element classification."""

import json
import requests
from typing import Any, Optional

VON_URL = "http://127.0.0.1:8765/v1/systemone"


def pick_element(
    snapshot_text: str,
    goal: str,
    candidates: list[dict[str, Any]],
    none_option: str = "No matching element found",
    filter_role: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Ask Von to pick the best element for a goal.

    Args:
        snapshot_text: Compact page snapshot (accessibility tree).
        goal: What to do (e.g. "Click the Log In button").
        candidates: List of element dicts with at least 'id', 'ref', 'text'.
        none_option: Description for "none of the above".
        filter_role: Optional role filter (e.g. "button" to only consider buttons).

    Returns:
        The chosen candidate dict with 'confidence' added, or None if no match.
    """
    if not candidates:
        return None

    # Pre-filter by role if specified
    if filter_role:
        candidates = [c for c in candidates if c.get("role", "").lower() == filter_role.lower()]
        if not candidates:
            return None

    # Build compact state from candidates only (not full snapshot)
    state_lines = []
    for c in candidates:
        state_lines.append(f'- {c.get("role", "element")} "{c.get("text", "")}" [ref={c["ref_id"]}]')
    state = "\n".join(state_lines)

    criteria = {}
    for c in candidates:
        criteria[c["ref_id"]] = {
            "ref": c["ref_id"],
            "text": c.get("text", ""),
            "role": c.get("role", ""),
        }
    criteria["__none__"] = none_option

    payload = {
        "model": "von-1.0",
        "state": state,
        "questions": {
            "action": {
                "type": "choice",
                "instructions": goal,
                "criteria": criteria,
            }
        },
    }

    try:
        resp = requests.post(VON_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        answer = data["answers"]["action"]
        choice_ref = answer["choice"]
        confidence = answer.get("confidence", 0.0)

        if choice_ref == "__none__":
            return None

        for c in candidates:
            if c["ref_id"] == choice_ref:
                return {**c, "confidence": confidence}
    except Exception as e:
        print(f"[Sys1] Von error: {e}")
        return None

    return None
