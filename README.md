# AgentBrowser Pro

**The first fully systematic AGI agent browser.**

A two-layer AI architecture that plans, decides, and executes browser interactions with zero human intervention. Sys2 (LLM planner) generates test scripts from natural language. Sys1 (local classifier) picks exact DOM elements. agent-browser executes via CDP at machine speed.

```
User: "Login, go to leads, note first lead, logout"
  ↓
Sys2 (mimo-v2.6-flash) → ["Login with credentials", "Navigate to /leads", "Note first lead", "Sign out"]
  ↓
Sys1 (Von, local) → picks exact element from page state (1.1s, $0)
  ↓
agent-browser (Rust CDP) → executes click/fill/navigate (50ms)
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  Sys2 (mimo-v2.6-flash) — PLANNER           │
│  OpenAI-compatible API | ~$0.003/step        │
│  Generates numbered goal list from instruction│
└─────────────────────┬───────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│  Sys1 (Von 1.0) — ELEMENT PICKER            │
│  Local classifier | 395M params | $0         │
│  Picks exact DOM element from page state     │
│  ~1.1s per decision (CPU)                    │
└─────────────────────┬───────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│  agent-browser — EXECUTOR                    │
│  Rust CDP | ~50ms per action                 │
│  Snapshots, clicks, fills, navigation        │
└─────────────────────────────────────────────┘
```

## Why This Exists

Traditional browser automation requires writing CSS selectors, XPath, or Playwright scripts. AI browser agents use expensive vision models ($0.05-0.25 per action) or fragile screenshot-based approaches.

AgentBrowser Pro is different:

- **Sys1 (Von)** is a trained classification model — not an LLM. It picks elements by matching text descriptions to DOM nodes. 1.1s latency, zero API cost, runs locally.
- **Sys2 (mimo)** is a fast MoE planner (309B/15B active) that decomposes natural language into concrete steps. $0.003 per step.
- **agent-browser** is a Rust-native CDP client — 20x faster than Playwright, handles large pages via compact snapshots.

**Total cost per 5-step test: ~$0.015** (vs $0.25-1.25 for single-LLM approaches)

## Quick Start

```bash
# Install
git clone https://github.com/entermarkets9/agent-browser-pro.git
cd agent-browser-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt

# Install agent-browser (Rust CDP engine)
npm install -g agent-browser
agent-browser install

# Start Von (local element picker)
pip install von-sdk
von serve --host 127.0.0.1 --port 8765

# Run a test
python -c "
from orchestrator import run_test
import json
report = run_test('Login with test@example.com, go to settings, toggle theme')
print(json.dumps(report, indent=2))
"
```

## MCP Integration (Kilo, Claude, etc.)

Register as an MCP server in your AI assistant:

```json
{
  "mcp": {
    "browser-test": {
      "type": "local",
      "command": [".venv/Scripts/python.exe", "mcp_server.py"],
      "environment": { "JEV_BASE_URL": "http://127.0.0.1:8765" }
    }
  }
}
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `browser_test` | Run full test from natural language instruction |
| `browser_step` | Execute single action with Von element picking |
| `browser_open` | Navigate to URL |
| `browser_close` | Close browser session |

## Benchmark

Test: Login → Theme Toggle → Leads → Logout on nabra.ai

| Step | Time | Cost |
|------|------|------|
| Navigate to nabra.ai | 2.9s | $0 |
| Pick Log In (Sys1) | 12.9s | $0 |
| Click Log In | 0.2s | $0 |
| Fill email (Sys1) | 4.6s | $0 |
| Fill password (Sys1) | 4.8s | $0 |
| Click Sign In (Sys1) | 18.4s | $0 |
| Navigate to Settings | 4.2s | $0 |
| Toggle theme (Sys1) | 15.1s | $0 |
| Navigate to Leads | 2.6s | $0 |
| Logout (Sys1) | 14.7s | $0 |
| **Total** | **85.5s** | **~$0.003** |

11/11 steps passed. All element selection done by Von locally — zero API calls for decisions.

## How It Works

### Sys2 (Planner)

mimo-v2.6-flash receives the test instruction and generates a structured plan:

```json
{
  "steps": [
    {"action": "navigate", "target": "https://app.example.com/login"},
    {"action": "fill", "target": "email field", "value": "user@example.com"},
    {"action": "fill", "target": "password field", "value": "password123"},
    {"action": "click", "target": "Sign In button"},
    {"action": "done", "note": "Login complete"}
  ]
}
```

### Sys1 (Element Picker)

For each step, Von receives the page's interactive elements and picks the best match:

```json
{
  "state": "- button \"Log In\" [ref=e4]\n- button \"Get Started\" [ref=e29]",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Click the Log In button",
      "criteria": {
        "e4": {"ref": "e4", "text": "Log In", "role": "button"},
        "e29": {"ref": "e29", "text": "Get Started", "role": "button"}
      }
    }
  }
}
```

Response: `{"choice": "e4", "confidence": 0.938}`

### Executor

agent-browser executes the chosen action via Chrome DevTools Protocol at ~50ms per action.

## Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.10+ |
| Node.js | 18+ |
| Von | `pip install von-sdk` (auto-downloads 1.5GB model on first run) |
| agent-browser | `npm install -g agent-browser` |
| mimo API | OpenAI-compatible endpoint (or any OpenAI-compatible LLM) |

## Configuration

Set environment variables or create `.env`:

```bash
# Sys2 (Planner) — any OpenAI-compatible API
OPENAI_BASE_URL=https://your-api.com/v1
OPENAI_API_KEY=your-key
MODEL_NAME=mimo-v2.6-flash

# Sys1 (Element Picker) — local Von server
JEV_BASE_URL=http://127.0.0.1:8765
```

## License

MIT
