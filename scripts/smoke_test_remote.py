"""
Remote smoke test for the deployed HuggingFace Space.
Run this AFTER deploying to HF Spaces to confirm the environment is reachable.

Usage:
  python scripts/smoke_test_remote.py --url https://YOUR-SPACE-URL.hf.space
  python scripts/smoke_test_remote.py --url http://localhost:7860  (for local test)
"""

import argparse
import requests
import uuid
import sys
from rich.console import Console
from rich.table import Table

console = Console()


def check(label: str, passed: bool, detail: str = ""):
    status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
    console.print(f"  {status}  {label}" + (f" — {detail}" if detail else ""))
    return passed


def run_smoke_test(base_url: str) -> bool:
    base_url = base_url.rstrip("/")
    session_id = f"smoke-{uuid.uuid4().hex[:8]}"
    all_pass = True

    console.print(f"\n[bold]Smoke testing:[/bold] {base_url}\n")

    # Check 1: Health endpoint
    try:
        r = requests.get(f"{base_url}/health", timeout=10)
        all_pass &= check("Health endpoint reachable", r.status_code == 200, f"status={r.status_code}")
        all_pass &= check("Health returns 'ok' status", r.json().get("status") == "ok")
    except Exception as e:
        all_pass &= check("Health endpoint reachable", False, str(e))

    # Check 2: Reset
    try:
        r = requests.post(f"{base_url}/reset", json={"session_id": session_id, "difficulty": "easy"}, timeout=30)
        all_pass &= check("POST /reset returns 200", r.status_code == 200, f"status={r.status_code}")
        obs = r.json().get("observation", {})
        all_pass &= check("Observation contains current_script", "current_script" in obs)
        all_pass &= check("Observation contains episode_id", "episode_id" in obs)
        all_pass &= check("Observation contains reward_components", "reward_components" in obs)
    except Exception as e:
        all_pass &= check("POST /reset returns 200", False, str(e))
        obs = {}

    # Check 3: Step with a valid action
    try:
        action = {
            "action_type": "hook_rewrite",
            "target_section": "hook",
            "instruction": "Make the opening line more specific with a concrete number",
            "critique_claim_id": "C1",
            "reasoning": "smoke test action"
        }
        r = requests.post(f"{base_url}/step", json={"session_id": session_id, "action": action}, timeout=60)
        all_pass &= check("POST /step returns 200", r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        all_pass &= check("Step returns reward float", isinstance(data.get("reward"), (int, float)))
        all_pass &= check("Step returns terminated bool", isinstance(data.get("terminated"), bool))
        all_pass &= check("Step reward is in [0, 1]", 0.0 <= float(data.get("reward", -1)) <= 1.0)
    except Exception as e:
        all_pass &= check("POST /step returns 200", False, str(e))

    # Check 4: State
    try:
        r = requests.get(f"{base_url}/state/{session_id}", timeout=15)
        all_pass &= check("GET /state returns 200", r.status_code == 200, f"status={r.status_code}")
        state = r.json()
        all_pass &= check("State contains step_num", "step_num" in state)
        all_pass &= check("State contains debate_history", "debate_history" in state)
    except Exception as e:
        all_pass &= check("GET /state returns 200", False, str(e))

    # Check 5: Unknown session returns 404
    try:
        r = requests.post(f"{base_url}/step", json={"session_id": "nonexistent-999", "action": {}}, timeout=10)
        all_pass &= check("Unknown session returns 404", r.status_code == 404)
    except Exception as e:
        all_pass &= check("Unknown session returns 404", False, str(e))

    console.print()
    if all_pass:
        console.print("[bold green]SMOKE TEST: ALL PASS — environment is remotely callable[/bold green]")
    else:
        console.print("[bold red]SMOKE TEST: FAILURES DETECTED — fix before submitting[/bold red]")

    return all_pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:7860", help="Base URL of deployed Space or local server")
    args = parser.parse_args()
    success = run_smoke_test(args.url)
    sys.exit(0 if success else 1)
