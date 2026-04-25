"""
Submission check for the Viral Script Debugging Engine.
Run:  python scripts/submission_check.py

Prints PASS or FAIL for each of the 10 requirements.
Final line: SUBMISSION READY ✓  or  SUBMISSION INCOMPLETE — fix the above before submitting
"""
import json
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

results: list[tuple[str, bool, str]] = []


def check(label: str, passed: bool, detail: str = ""):
    status = "[PASS]" if passed else "[FAIL]"
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
# Final verdict
# ---------------------------------------------------------------------------
print()
all_passed = all(r[1] for r in results)
pass_count = sum(1 for r in results if r[1])
fail_count = len(results) - pass_count

if all_passed:
    print(f"  SUBMISSION READY [PASS]  ({pass_count}/{len(results)} checks passed)")
else:
    print(f"  SUBMISSION INCOMPLETE -- fix the above before submitting")
    print(f"  ({pass_count}/{len(results)} passed, {fail_count} failed)")

sys.exit(0 if all_passed else 1)
