"""
Submission check for the Viral Script Debugging Engine.
Run:  python scripts/submission_check.py

Prints PASS or FAIL for each requirement.
Distinguishes BLOCKING failures (disqualify) from WARNINGS (hurt score).
Final line: SUBMISSION READY  or  SUBMISSION INCOMPLETE — fix the above before submitting
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
VSE = ROOT / "viral_script_engine"

REQUIRED_README_SECTIONS = [
    "The Problem",
    "What We Built",
    "Reward Functions",
    "Anti-Gaming",
    "Results",
]

BLOCKING = {
    "openenv.yaml has no reserved tool names",
    "README HF Space URL is not a placeholder",
    "scripts/smoke_test_remote.py exists",
}

results: list[tuple[str, bool, str]] = []


def check(label: str, passed: bool, detail: str = ""):
    is_blocking = label in BLOCKING
    if passed:
        status = "[PASS]"
    elif is_blocking:
        status = "[BLOCKING FAIL]"
    else:
        status = "[WARNING]"
    line = f"  {status}  {label}"
    if detail:
        line += f"  — {detail}"
    print(line)
    results.append((label, passed, detail))


# ---------------------------------------------------------------------------
# 1. openenv.yaml exists and parses
# ---------------------------------------------------------------------------
yaml_path = ROOT / "openenv.yaml"
if yaml_path.exists():
    try:
        import yaml  # type: ignore
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        check("openenv.yaml exists and parses", True, f"name={data.get('name')}")
    except ImportError:
        # yaml not installed — do a minimal manual check
        content = yaml_path.read_text()
        ok = "name:" in content and "entry_point:" in content
        check("openenv.yaml exists and parses", ok, "PyYAML not installed — checked key fields only")
    except Exception as e:
        check("openenv.yaml exists and parses", False, str(e))
else:
    check("openenv.yaml exists and parses", False, "file not found")

# ---------------------------------------------------------------------------
# 2. app.py starts without error (3-second subprocess timeout)
# ---------------------------------------------------------------------------
app_path = ROOT / "app.py"
if not app_path.exists():
    check("app.py starts without error", False, "app.py not found")
else:
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, r'{ROOT}'); import app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ROOT),
        )
        try:
            stdout, stderr = proc.communicate(timeout=10)
            rc = proc.returncode
            if rc == 0:
                check("app.py starts without error", True)
            else:
                err_snippet = stderr.decode(errors="replace")[-200:]
                check("app.py starts without error", False, err_snippet)
        except subprocess.TimeoutExpired:
            proc.kill()
            # If it's still running after 10s, the import succeeded (server started)
            check("app.py starts without error", True, "process running (server started)")
    except Exception as e:
        check("app.py starts without error", False, str(e))

# ---------------------------------------------------------------------------
# 3. README contains huggingface.co/spaces link
# ---------------------------------------------------------------------------
readme_path = ROOT / "README.md"
if readme_path.exists():
    content = readme_path.read_text(encoding="utf-8")
    has_link = "huggingface.co/spaces" in content
    check("README contains huggingface.co/spaces link", has_link)
else:
    check("README contains huggingface.co/spaces link", False, "README.md not found")

# ---------------------------------------------------------------------------
# 4. logs/baseline_reward_curves.png exists
# ---------------------------------------------------------------------------
baseline_png = VSE / "logs" / "baseline_reward_curves.png"
check(
    "logs/baseline_reward_curves.png exists",
    baseline_png.exists(),
    str(baseline_png) if not baseline_png.exists() else "",
)

# ---------------------------------------------------------------------------
# 5. logs/training_vs_baseline.png exists
# ---------------------------------------------------------------------------
training_png = VSE / "logs" / "training_vs_baseline.png"
check(
    "logs/training_vs_baseline.png exists",
    training_png.exists(),
    "run eval_trained_model.py after GRPO training" if not training_png.exists() else "",
)

# ---------------------------------------------------------------------------
# 6. logs/escalation_chart.png exists
# ---------------------------------------------------------------------------
escalation_png = VSE / "logs" / "escalation_chart.png"
check(
    "logs/escalation_chart.png exists",
    escalation_png.exists(),
    str(escalation_png) if not escalation_png.exists() else "",
)

# ---------------------------------------------------------------------------
# 7. notebooks/training_colab.ipynb exists
# ---------------------------------------------------------------------------
colab_path = ROOT / "notebooks" / "training_colab.ipynb"
if colab_path.exists():
    try:
        with open(colab_path) as f:
            nb = json.load(f)
        cell_count = len(nb.get("cells", []))
        check("notebooks/training_colab.ipynb exists", True, f"{cell_count} cells")
    except Exception as e:
        check("notebooks/training_colab.ipynb exists", False, f"invalid JSON: {e}")
else:
    check("notebooks/training_colab.ipynb exists", False, "file not found")

# ---------------------------------------------------------------------------
# 8. README contains all required sections
# ---------------------------------------------------------------------------
if readme_path.exists():
    content = readme_path.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_README_SECTIONS if s not in content]
    if missing:
        check("README contains all required sections", False, f"missing: {missing}")
    else:
        check("README contains all required sections", True)
else:
    check("README contains all required sections", False, "README.md not found")

# ---------------------------------------------------------------------------
# 9. requirements.txt is complete
# ---------------------------------------------------------------------------
req_path = ROOT / "requirements.txt"
if not req_path.exists():
    req_path = VSE / "requirements.txt"

REQUIRED_PACKAGES = [
    "anthropic",
    "sentence-transformers",
    "trl",
    "numpy",
    "pydantic",
    "fastapi",
    "uvicorn",
    "rich",
]

if req_path.exists():
    req_text = req_path.read_text(encoding="utf-8").lower()
    missing_pkgs = [p for p in REQUIRED_PACKAGES if p.lower() not in req_text]
    if missing_pkgs:
        check("requirements.txt is complete", False, f"missing: {missing_pkgs}")
    else:
        check("requirements.txt is complete", True)
else:
    check("requirements.txt is complete", False, "requirements.txt not found")

# ---------------------------------------------------------------------------
# 10. All tests pass (pytest exit code 0)
# ---------------------------------------------------------------------------
try:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(VSE / "tests"), "-q", "--tb=short"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    passed_tests = proc.returncode == 0
    # Extract summary line from pytest output
    lines = (proc.stdout + proc.stderr).strip().splitlines()
    summary = next((l for l in reversed(lines) if "passed" in l or "failed" in l or "error" in l), "")
    check("All tests pass (pytest)", passed_tests, summary)
except subprocess.TimeoutExpired:
    check("All tests pass (pytest)", False, "pytest timed out after 120s")
except Exception as e:
    check("All tests pass (pytest)", False, str(e))

# ---------------------------------------------------------------------------
# 11. openenv.yaml has no reserved tool names
# ---------------------------------------------------------------------------
try:
    import yaml
    with open(yaml_path) as f:
        manifest = yaml.safe_load(f)
    tool_names = [t["name"] for t in manifest.get("tools", [])]
    reserved = {"reset", "step", "state", "close"}
    reserved_found = reserved.intersection(set(tool_names))
    check("openenv.yaml has no reserved tool names", len(reserved_found) == 0,
          f"Found reserved: {reserved_found}" if reserved_found else "")
except Exception as e:
    check("openenv.yaml has no reserved tool names", False, str(e))

# ---------------------------------------------------------------------------
# 12. README HF Space URL is not a placeholder
# ---------------------------------------------------------------------------
if readme_path.exists():
    content = readme_path.read_text(encoding="utf-8")
    has_real_hf_url = "huggingface.co/spaces" in content
    is_placeholder = "YOUR-SPACE-URL" in content or "YOUR_TEAM" in content
    check("README HF Space URL is not a placeholder", has_real_hf_url and not is_placeholder,
          "Replace placeholder URL with real Space URL" if is_placeholder else "")
else:
    check("README HF Space URL is not a placeholder", False, "README.md not found")

# ---------------------------------------------------------------------------
# 13. Training plot exists and looks real (>80KB)
# ---------------------------------------------------------------------------
training_png2 = VSE / "logs" / "training_vs_baseline.png"
plot_exists = training_png2.exists()
plot_size_kb = os.path.getsize(str(training_png2)) / 1024 if plot_exists else 0
plot_looks_real = plot_size_kb > 80
check("Training plot exists", plot_exists, "")
check("Training plot looks real (>80KB)", plot_looks_real,
      f"Current size: {plot_size_kb:.0f}KB — may still be synthetic placeholder. Replace after onsite training."
      if not plot_looks_real else "")

# ---------------------------------------------------------------------------
# 14. scripts/smoke_test_remote.py exists
# ---------------------------------------------------------------------------
check("scripts/smoke_test_remote.py exists",
      (ROOT / "scripts" / "smoke_test_remote.py").exists(), "")

# ---------------------------------------------------------------------------
# 15. client/env_client.py exists (client/server separation)
# ---------------------------------------------------------------------------
check("client/env_client.py exists",
      (ROOT / "client" / "env_client.py").exists(), "")

# ---------------------------------------------------------------------------
# 16. Colab notebook uses ViralScriptEnvClient
# ---------------------------------------------------------------------------
colab_path2 = ROOT / "notebooks" / "training_colab.ipynb"
if colab_path2.exists():
    try:
        with open(colab_path2) as f:
            nb = json.load(f)
        nb_source = " ".join(
            "".join(cell.get("source", [])) for cell in nb.get("cells", [])
        )
        check("Colab notebook uses ViralScriptEnvClient",
              "ViralScriptEnvClient" in nb_source,
              "Add a cell showing client usage against deployed Space URL")
    except Exception as e:
        check("Colab notebook uses ViralScriptEnvClient", False, str(e))
else:
    check("Colab notebook uses ViralScriptEnvClient", False, "notebook not found")

# ---------------------------------------------------------------------------
# Final verdict
# ---------------------------------------------------------------------------
print()
all_passed = all(r[1] for r in results)
blocking_failed = [r for r in results if not r[1] and r[0] in BLOCKING]
warnings = [r for r in results if not r[1] and r[0] not in BLOCKING]
pass_count = sum(1 for r in results if r[1])
fail_count = len(results) - pass_count

if blocking_failed:
    print(f"  SUBMISSION BLOCKED — {len(blocking_failed)} blocking failure(s) must be fixed:")
    for label, _, detail in blocking_failed:
        print(f"    - {label}" + (f": {detail}" if detail else ""))
elif warnings:
    print(f"  SUBMISSION READY (with warnings) — {pass_count}/{len(results)} checks passed")
    print(f"  {len(warnings)} warning(s) may hurt score but will not disqualify:")
    for label, _, detail in warnings:
        print(f"    - {label}" + (f": {detail}" if detail else ""))
else:
    print(f"  SUBMISSION READY [PASS]  ({pass_count}/{len(results)} checks passed)")

sys.exit(0 if not blocking_failed else 1)
