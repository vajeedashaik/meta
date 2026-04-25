#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.agents.critic import CriticAgent, CriticParseError
from viral_script_engine.evaluation.critic_evaluator import CriticEvaluator

console = Console()
BASE_DIR = Path(__file__).parent.parent


def load_scripts(dry_run: bool) -> list:
    scripts_path = BASE_DIR / "data" / "test_scripts" / "scripts.json"
    with open(scripts_path) as f:
        scripts = json.load(f)
    if dry_run:
        scripts = scripts[:2]
    return scripts


def run_gate(max_retries: int = 3, dry_run: bool = False, backend: str = "qwen", model_name: str = "Qwen/Qwen2.5-1.5B-Instruct") -> bool:
    agent = CriticAgent(backend=backend, model_name=model_name)
    evaluator = CriticEvaluator()
    scripts = load_scripts(dry_run)

    table = Table(title="Critic Gate Results", box=box.ROUNDED)
    table.add_column("Script ID", style="cyan", no_wrap=True)
    table.add_column("Claims", justify="center")
    table.add_column("Specificity", justify="center")
    table.add_column("Falsifiability", justify="center")
    table.add_column("Gate", justify="center")

    outputs = []
    all_results = []

    with console.status("[bold green]Running CriticAgent on scripts...") as status:
        for entry in scripts:
            sid = entry["script_id"]
            status.update(f"[bold green]Processing {sid}...")

            critique_output = None
            for attempt in range(max_retries):
                try:
                    critique_output = agent.critique(
                        script=entry["script_text"],
                        region=entry["region"],
                        platform=entry["platform"],
                        niche=entry["niche"],
                    )
                    break
                except CriticParseError as e:
                    if attempt == max_retries - 1:
                        console.print(f"[red]FAILED {sid} after {max_retries} attempts: {e}")
                    else:
                        console.print(f"[yellow]Retry {attempt + 1} for {sid}")

            if critique_output is None:
                continue

            result = evaluator.evaluate(critique_output, entry["script_text"], script_id=sid)
            all_results.append(result)
            outputs.append((sid, entry, critique_output))

            gate_str = "[green]PASS[/green]" if result.passes_gate else "[red]FAIL[/red]"
            table.add_row(
                sid,
                str(result.claim_count),
                f"{result.specificity_score:.2f}",
                f"{result.falsifiability_score:.2f}",
                gate_str,
            )

    console.print(table)

    pass_count = sum(1 for r in all_results if r.passes_gate)
    pass_rate = pass_count / len(all_results) if all_results else 0.0
    overall_pass = pass_rate >= 0.8

    if overall_pass:
        fixtures_dir = BASE_DIR / "data" / "golden_fixtures"
        fixtures_dir.mkdir(exist_ok=True)
        for sid, entry, critique_output in outputs:
            fixture_path = fixtures_dir / f"fixture_{sid}.json"
            fixture_data = {
                "script_id": sid,
                "region": entry["region"],
                "platform": entry["platform"],
                "niche": entry["niche"],
                "critique": critique_output.model_dump(),
            }
            with open(fixture_path, "w") as f:
                json.dump(fixture_data, f, indent=2)
        console.print(f"[green]Golden fixtures saved to {fixtures_dir}")

    failing = [r.script_id for r in all_results if not r.passes_gate]
    if failing:
        console.print(f"[red]Failing scripts: {', '.join(failing)}")
        for r in all_results:
            if not r.passes_gate:
                console.print(
                    f"  [yellow]{r.script_id}[/yellow]: "
                    f"claims={r.claim_count}, specificity={r.specificity_score:.2f}, "
                    f"falsifiability={r.falsifiability_score:.2f}"
                )

    gate_label = f"PHASE 0 GATE: {'PASS' if overall_pass else 'FAIL'}"
    style = "bold green" if overall_pass else "bold red"
    console.print(Panel(f"[{style}]{gate_label}[/{style}]  ({pass_count}/{len(all_results)} scripts passed)"))

    return overall_pass


def main():
    parser = argparse.ArgumentParser(description="Run Critic quality gate")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backend", default="qwen", choices=["qwen", "anthropic", "openai"])
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-1.5B-Instruct")
    args = parser.parse_args()

    passed = run_gate(max_retries=args.max_retries, dry_run=args.dry_run, backend=args.backend, model_name=args.model_name)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
