"""Benchmark: Login → Theme Toggle → Leads → Note Lead → Logout"""
import ab_executor
from sys1_von import pick_element
import json, time, os

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

results = []

def step(name, fn):
    start = time.time()
    try:
        result = fn()
        elapsed = (time.time() - start) * 1000
        results.append({"step": name, "ok": True, "ms": elapsed, "detail": result})
        print(f"  [{elapsed:.0f}ms] {name}: OK")
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        results.append({"step": name, "ok": False, "ms": elapsed, "error": str(e)})
        print(f"  [{elapsed:.0f}ms] {name}: FAIL - {e}")

def von_pick(goal, elements, snapshot):
    chosen = pick_element(snapshot, goal, elements)
    if not chosen:
        raise Exception(f"No element found for: {goal}")
    return chosen

total_start = time.time()
print("=== BENCHMARK: Login > Theme > Leads > Logout ===\n")

# 1. Navigate to nabra.ai
def do_nav():
    return ab_executor.navigate("https://nabra.ai")
step("Navigate to nabra.ai", do_nav)

# 2. Snapshot + pick Log In
def do_pick_login():
    snap = ab_executor.snapshot_compact()
    elems = ab_executor.parse_interactive_elements(snap)
    return von_pick("Click the Log In button", elems, snap)
login_pick = None
def do_login_step():
    global login_pick
    login_pick = do_pick_login()
    return login_pick
step("Pick Log In (Sys1)", do_login_step)

# 3. Click Log In
def do_click_login():
    return ab_executor.click(login_pick["ref"])
step("Click Log In", do_click_login)

import time as _time
_time.sleep(1)

# 4. Fill email
def do_fill_email():
    snap = ab_executor.snapshot_compact()
    elems = ab_executor.parse_interactive_elements(snap)
    inputs = [e for e in elems if e["role"] in ("textbox", "input")]
    chosen = von_pick("Fill the email/username field", inputs, snap)
    return ab_executor.fill(chosen["ref"], "ateeq@freedesk.org")
step("Fill email", do_fill_email)

# 5. Fill password
def do_fill_pass():
    snap = ab_executor.snapshot_compact()
    elems = ab_executor.parse_interactive_elements(snap)
    inputs = [e for e in elems if e["role"] in ("textbox", "input")]
    chosen = von_pick("Fill the password field", inputs, snap)
    return ab_executor.fill(chosen["ref"], "Ateeq123@")
step("Fill password", do_fill_pass)

# 6. Click Sign In
def do_click_signin():
    snap = ab_executor.snapshot_compact()
    elems = ab_executor.parse_interactive_elements(snap)
    chosen = von_pick("Click the Sign In button", elems, snap)
    return ab_executor.click(chosen["ref"])
step("Click Sign In", do_click_signin)

_time.sleep(2)

# 7. Navigate to Settings
def do_nav_settings():
    return ab_executor.navigate("https://nabra.ai/settings")
step("Navigate to Settings", do_nav_settings)

# 8. Toggle theme
def do_toggle_theme():
    snap = ab_executor.snapshot_compact()
    elems = ab_executor.parse_interactive_elements(snap)
    theme_btns = [e for e in elems if "Switch" in e.get("text", "") or "mode" in e.get("text", "").lower()]
    if not theme_btns:
        theme_btns = elems
    chosen = von_pick("Click the theme toggle button (dark/light mode)", theme_btns, snap)
    return ab_executor.click(chosen["ref"])
step("Toggle theme (Sys1)", do_toggle_theme)

# 9. Navigate to Leads
def do_nav_leads():
    return ab_executor.navigate("https://nabra.ai/leads")
step("Navigate to Leads", do_nav_leads)

_time.sleep(2)

# 10. Snapshot leads page
def do_leads_snapshot():
    snap = ab_executor.snapshot_compact()
    return f"snapshot_size={len(snap)}"
step("Snapshot Leads page", do_leads_snapshot)

# 11. Logout
def do_logout():
    snap = ab_executor.snapshot_compact()
    elems = ab_executor.parse_interactive_elements(snap)
    signout = [e for e in elems if "Sign out" in e.get("text", "") or "Logout" in e.get("text", "")]
    if signout:
        return ab_executor.click(signout[0]["ref"])
    chosen = von_pick("Click the Sign Out button", elems, snap)
    return ab_executor.click(chosen["ref"])
step("Logout", do_logout)

# Summary
total_ms = (time.time() - total_start) * 1000
print(f"\n=== SUMMARY ===")
print(f"Total: {total_ms:.0f}ms ({total_ms/1000:.1f}s)")
print(f"Steps: {len(results)}")
ok_count = sum(1 for r in results if r["ok"])
print(f"Pass: {ok_count}/{len(results)}")
for r in results:
    status = "OK" if r["ok"] else "FAIL"
    print(f"  [{r['ms']:.0f}ms] {r['step']}: {status}")
