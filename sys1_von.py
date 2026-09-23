"""Sys1 (Von) element picker — local fuzzy-text matcher with optional Von fallback."""

import json
import re
import requests
from typing import Any, Optional

VON_URL = "http://127.0.0.1:8765/v1/systemone"
_VON_AVAILABLE: Optional[bool] = None


def _check_von() -> bool:
    """Check if Von server is reachable (cached after first call)."""
    global _VON_AVAILABLE
    if _VON_AVAILABLE is not None:
        return _VON_AVAILABLE
    try:
        resp = requests.post(VON_URL, json={"ping": True}, timeout=2)
        _VON_AVAILABLE = resp.status_code < 500
    except Exception:
        _VON_AVAILABLE = False
    if not _VON_AVAILABLE:
        print("[Sys1] Von server unavailable, using local fuzzy matcher")
    return _VON_AVAILABLE


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower())).strip()


def _fuzzy_score(goal: str, text: str, role: str) -> float:
    """Score how well a candidate matches the goal. Higher is better.

    Strategy:
    - Exact substring match on text: high score
    - Word overlap: moderate score
    - Role hint bonus (e.g. "click the X button" → prefer role=button)
    """
    goal_norm = _normalize(goal)
    text_norm = _normalize(text)
    score = 0.0

    # Remove action verbs from goal to get the target concept
    # "Click the Log In button" → "Log In button" → "log in"
    target = re.sub(
        r"^(click|fill|press|select|tap|check|uncheck|toggle|enter|type)\s+(the\s+)?",
        "",
        goal_norm,
    )
    # Strip role suffix from target for matching
    target_core = re.sub(
        r"\s*(button|link|field|input|textbox|checkbox|radio|tab|menu|dropdown|element|box)$",
        "",
        target,
    ).strip()

    # Exact match on full text
    if text_norm == target_core:
        score += 100

    # Target is substring of text or vice versa
    if target_core and target_core in text_norm:
        score += 80
    elif target_core and text_norm in target_core:
        score += 70

    # Word overlap
    target_words = set(target_core.split())
    text_words = set(text_norm.split())
    if target_words and text_words:
        overlap = target_words & text_words
        score += len(overlap) / max(len(target_words), 1) * 60

    # Role hint: if goal mentions "button" and candidate is a button, bonus
    role_hints = {
        "button": {"button"},
        "link": {"link"},
        "field": {"textbox", "input", "combobox"},
        "input": {"textbox", "input", "combobox"},
        "textbox": {"textbox", "input"},
        "checkbox": {"checkbox"},
        "radio": {"radio"},
        "tab": {"tab"},
        "dropdown": {"combobox"},
        "select": {"combobox"},
    }
    for hint, roles in role_hints.items():
        if hint in goal_norm and role.lower() in roles:
            score += 15
            break

    return score


def _fuzzy_pick(
    goal: str,
    candidates: list[dict[str, Any]],
    threshold: float = 20.0,
) -> Optional[dict[str, Any]]:
    """Pick the best matching element using fuzzy text scoring."""
    if not candidates:
        return None

    scored = []
    for c in candidates:
        s = _fuzzy_score(goal, c.get("text", ""), c.get("role", ""))
        scored.append((s, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best = scored[0]

    if best_score < threshold:
        print(f"[Sys1] Best match score {best_score:.1f} below threshold {threshold}")
        return None

    print(f"[Sys1] Picked: {best.get('text', '')!r} (ref={best['ref_id']}, score={best_score:.1f})")
    return {**best, "confidence": min(best_score / 100, 1.0)}


def pick_element(
    snapshot_text: str,
    goal: str,
    candidates: list[dict[str, Any]],
    none_option: str = "No matching element found",
    filter_role: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Pick the best element for a goal.

    Tries Von server first if available, falls back to local fuzzy matching.

    Args:
        snapshot_text: Compact page snapshot (accessibility tree).
        goal: What to do (e.g. "Click the Log In button").
        candidates: List of element dicts with at least 'ref_id', 'ref', 'text'.
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

    # Try Von server first
    if _check_von():
        result = _pick_via_von(snapshot_text, goal, candidates, none_option)
        if result is not None:
            return result

    # Fallback: local fuzzy matcher
    return _fuzzy_pick(goal, candidates)


def _pick_via_von(
    snapshot_text: str,
    goal: str,
    candidates: list[dict[str, Any]],
    none_option: str,
) -> Optional[dict[str, Any]]:
    """Ask Von server to pick the best element."""
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
        resp = requests.post(VON_URL, json=payload, timeout=10)
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
        # Mark Von as unavailable for subsequent calls
        global _VON_AVAILABLE
        _VON_AVAILABLE = False

    return None
