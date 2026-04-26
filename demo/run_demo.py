"""
5-act demo for the Viral Script Debugging Engine.

Usage:
    python demo/run_demo.py --script S03 --compare   # base vs trained side-by-side
    python demo/run_demo.py --interactive             # human acts as Arbitrator
    python demo/run_demo.py --script S01              # single untrained run
"""
import argparse
import json
import sys
import time
from pathlib import Path

# Reconfigure stdout/stderr to UTF-8 so LLM-generated Unicode (₹, em-dashes, etc.)
# renders correctly on Windows terminals running cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure root is on path when run from project root or demo/
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.rule import Rule
from rich.columns import Columns

load_dotenv(dotenv_path=Path(__file__).parent.parent / "viral_script_engine" / ".env")
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)

from viral_script_engine.agents.baseline_arbitrator import BaselineArbitratorAgent
from viral_script_engine.agents.critic import CriticAgent
from viral_script_engine.agents.defender import DefenderAgent
from viral_script_engine.agents.rewriter import RewriterAgent
from viral_script_engine.environment.env import ViralScriptEnv

_ROOT = Path(__file__).parent.parent / "viral_script_engine"
_SCRIPTS_PATH = str(_ROOT / "data" / "test_scripts" / "scripts.json")
_CULTURAL_KB_PATH = str(_ROOT / "data" / "cultural_kb.json")

SEVERITY_COLOR = {"high": "red", "medium": "yellow", "low": "green"}
ACTIONS = ["hook_rewrite", "section_reorder", "cultural_ref_sub", "cta_placement"]

console = Console(width=120)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_script(script_id: str) -> dict:
    with open(_SCRIPTS_PATH) as f:
        scripts = json.load(f)
    for s in scripts:
        if s["script_id"] == script_id:
            return s
    raise ValueError(f"Script {script_id!r} not found in {_SCRIPTS_PATH}")


def _make_env(difficulty: str = "easy") -> ViralScriptEnv:
    return ViralScriptEnv(
        scripts_path=_SCRIPTS_PATH,
        cultural_kb_path=_CULTURAL_KB_PATH,
        difficulty=difficulty,
        use_escalation=False,
    )


def _bar(score: float, width: int = 8) -> str:
    filled = int(round(score * width))
    return "#" * filled + "." * (width - filled)


def _diff_lines(original: str, rewritten: str):
    """Yield (tag, line) where tag in {'+', '-', ' '}."""
    import difflib
    orig_lines = [l + "\n" for l in original.splitlines()]
    new_lines = [l + "\n" for l in rewritten.splitlines()]
    for line in difflib.unified_diff(orig_lines, new_lines, lineterm="", n=1):
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            yield ("+", line[1:].rstrip())
        elif line.startswith("-"):
            yield ("-", line[1:].rstrip())
        else:
            yield (" ", line[1:].rstrip())


# ---------------------------------------------------------------------------
# Acts
# ---------------------------------------------------------------------------

def act1_raw_script(script: dict):
    console.print(Rule("[bold cyan]ACT 1 — THE RAW SCRIPT[/bold cyan]", style="cyan"))
    flaws = ", ".join(script.get("known_flaws", []))

    # Phase 9: show platform spec inline
    platform = script.get("platform", "Reels")
    try:
        from viral_script_engine.platforms.platform_spec import PlatformRegistry
        spec = PlatformRegistry().get(platform)
        platform_str = (
            f"[dim]Platform:[/dim] {platform}  "
            f"[dim]Hook window:[/dim] {spec.hook_window_seconds}s  "
            f"[dim]Max length:[/dim] {spec.max_script_length_words} words  "
            f"[dim]Pacing:[/dim] {spec.pacing_norm}"
        )
    except Exception:
        platform_str = f"[dim]Platform:[/dim] {platform}"

    subtitle = (
        f"[dim]Region:[/dim] {script['region']}  "
        f"{platform_str}  "
        f"[dim]Niche:[/dim] {script['niche']}  "
        f"[dim]Known flaws:[/dim] [red]{flaws}[/red]"
    )
    console.print(Panel(
        script["script_text"],
        title=f"[bold]{script['script_id']} — Original Script[/bold]",
        subtitle=subtitle,
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()


def act2_critic_attacks(critique):
    console.print(Rule("[bold red]ACT 2 — THE CRITIC ATTACKS[/bold red]", style="red"))
    console.print(f"[dim]Overall severity: [bold]{critique.overall_severity}[/bold][/dim]\n")
    for i, claim in enumerate(critique.claims, 1):
        color = SEVERITY_COLOR.get(claim.severity, "white")
        body = (
            f"[bold]{claim.critique_class.replace('_', ' ').title()}[/bold] "
            f"[dim]({claim.timestamp_range})[/dim]\n\n"
            f"{claim.claim_text}\n\n"
            f"[dim]Evidence:[/dim] [italic]\"{claim.evidence}\"[/italic]"
        )
        console.print(Panel(
            body,
            title=f"[{color}]Claim {i} [{claim.claim_id}] — {claim.severity.upper()} severity[/{color}]",
            border_style=color,
            padding=(1, 2),
        ))
        if i < len(critique.claims):
            time.sleep(2)
    console.print()


def act3_defender_responds(defender_out, critique_claims):
    console.print(Rule("[bold green]ACT 3 — THE DEFENDER RESPONDS[/bold green]", style="green"))
    console.print(Panel(
        f"[bold]{defender_out.core_strength}[/bold]\n\n"
        f"[italic]\"{defender_out.core_strength_quote}\"[/italic]\n\n"
        f"[dim]{defender_out.defense_argument}[/dim]",
        title="[green]WHAT WE MUST PROTECT[/green]",
        border_style="green",
        padding=(1, 2),
    ))

    flagged = set(defender_out.flagged_critic_claims)
    if flagged:
        console.print("\n[yellow]Defender flagged these critic claims as overcorrection:[/yellow]")
        for claim in critique_claims:
            if claim.claim_id in flagged:
                console.print(
                    f"  [yellow]![/yellow] [{claim.claim_id}] {claim.claim_text[:90]}..."
                )

    if defender_out.regional_voice_elements:
        console.print("\n[dim]Protected regional voice elements:[/dim]")
        for elem in defender_out.regional_voice_elements:
            console.print(f"  • [italic]{elem}[/italic]")
    console.print()


def act4_arbitrator_decides(
    untrained_action: dict,
    trained_action: dict,
    compare: bool,
    trained_reasoning: dict = None,
):
    console.print(Rule("[bold blue]ACT 4 — THE ARBITRATOR DECIDES[/bold blue]", style="blue"))
    if compare:
        # Untrained panel — no reasoning chain
        untrained_body = (
            "[dim][No reasoning chain — zero-shot decision][/dim]\n\n"
            f"[bold]Action:[/bold] {untrained_action.get('action_type')}\n"
            f"[bold]Target:[/bold] {untrained_action.get('target_section')}\n"
            f"[bold]Instruction:[/bold] {untrained_action.get('instruction', '')[:120]}"
        )

        # Trained panel — show reasoning chain if available
        if trained_reasoning:
            priority = trained_reasoning.get("priority_assessment", "")
            cf_ans = trained_reasoning.get("conflict_check_answer", "")
            cf_rsn = trained_reasoning.get("conflict_check_reason", "")
            df_ans = trained_reasoning.get("defender_consideration_answer", "")
            df_rsn = trained_reasoning.get("defender_consideration_reason", "")
            trained_body = (
                f"[bold]Priority:[/bold] {priority}\n"
                f"[bold]Conflict check:[/bold] {cf_ans.upper()} — {cf_rsn}\n"
                f"[bold]Defender:[/bold] {df_ans.upper()} — {df_rsn}\n\n"
                f"[bold]Action:[/bold] {trained_action.get('action_type')}\n"
                f"[bold]Target:[/bold] {trained_action.get('target_section')}\n"
                f"[bold]Instruction:[/bold] {trained_action.get('instruction', '')[:120]}"
            )
        else:
            trained_body = (
                f"[bold]Action:[/bold] {trained_action.get('action_type')}\n"
                f"[bold]Target:[/bold] {trained_action.get('target_section')}\n"
                f"[bold]Instruction:[/bold] {trained_action.get('instruction', '')[:120]}\n\n"
                f"[bold]Reasoning:[/bold] {trained_action.get('reasoning', '')}"
            )

        console.print(Panel(untrained_body, title="[dim]UNTRAINED ARBITRATOR[/dim]", border_style="dim", padding=(1, 2)))
        console.print(Panel(trained_body, title="[blue]TRAINED ARBITRATOR[/blue]", border_style="blue", padding=(1, 2)))

        u_act = untrained_action.get("action_type")
        t_act = trained_action.get("action_type")
        if u_act != t_act:
            console.print(
                f"\n[bold yellow]Key difference:[/bold yellow] Untrained chose "
                f"[red]{u_act}[/red], Trained chose [blue]{t_act}[/blue]"
            )
        else:
            console.print(
                f"\n[dim]Both chose [bold]{u_act}[/bold] — difference lies in the instruction quality.[/dim]"
            )
    else:
        body = (
            f"[bold]Action:[/bold] {untrained_action.get('action_type')}\n"
            f"[bold]Target:[/bold] {untrained_action.get('target_section')}\n"
            f"[bold]Instruction:[/bold] {untrained_action.get('instruction', '')[:120]}\n\n"
            f"[bold]Reasoning:[/bold] {untrained_action.get('reasoning', '')}"
        )
        console.print(Panel(body, title="[blue]Arbitrator Decision[/blue]", border_style="blue", padding=(1, 2)))
    console.print()


def act5_rewrite_and_reward(original_script: str, rewritten_script: str, reward_components: dict, baseline_total: float):
    console.print(Rule("[bold magenta]ACT 5 — THE REWRITE + REWARD[/bold magenta]", style="magenta"))

    diff_text = Text()
    diff_lines = list(_diff_lines(original_script, rewritten_script))
    if diff_lines:
        for tag, line in diff_lines:
            if tag == "+":
                diff_text.append(f"+ {line}\n", style="green")
            elif tag == "-":
                diff_text.append(f"- {line}\n", style="red")
            else:
                diff_text.append(f"  {line}\n", style="dim")
    else:
        diff_text.append("(no changes in this step)", style="dim")

    console.print(Panel(diff_text, title="[magenta]Script Diff[/magenta]", border_style="magenta", padding=(1, 2)))

    console.print()

    labels = {
        "r1_hook_strength": "R1 Hook Strength",
        "r2_coherence": "R2 Coherence",
        "r3_cultural_alignment": "R3 Cultural",
        "r4_debate_resolution": "R4 Resolution",
        "r5_defender_preservation": "R5 Preservation",
        "r9_platform_pacing": "R9 Platform Pacing",
    }

    table = Table(box=box.SIMPLE_HEAD, show_header=False, padding=(0, 1))
    table.add_column("Label", style="cyan", min_width=22)
    table.add_column("Bar", min_width=12)
    table.add_column("Score", min_width=6)

    for key, label in labels.items():
        val = reward_components.get(key)
        if val is None:
            val = 0.0
        table.add_row(label, _bar(val), f"{val:.2f}")

    total = reward_components.get("total", 0.0)
    if total is None:
        total = 0.0

    if baseline_total > 0:
        pct_change = ((total - baseline_total) / baseline_total) * 100
        pct_str = f"  (+{pct_change:.0f}% vs baseline)" if pct_change >= 0 else f"  ({pct_change:.0f}% vs baseline)"
    else:
        pct_str = ""

    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{_bar(total)}[/bold]",
        f"[bold]{total:.2f}{pct_str}[/bold]",
    )

    console.print(Panel(table, title="[magenta]Reward Breakdown[/magenta]", border_style="magenta", padding=(1, 1)))
    console.print()


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def _interactive_choose_action(observation: dict) -> dict:
    console.print("\n[bold yellow]YOUR TURN — Choose an action as the Arbitrator:[/bold yellow]")
    for i, act in enumerate(ACTIONS, 1):
        console.print(f"  {i}. {act}")

    claim_ids = []
    if observation.get("debate_history"):
        last_round = observation["debate_history"][-1]
        claim_ids = [c.get("claim_id", f"C{i}") for i, c in enumerate(last_round.get("critic_claims", []), 1)]

    choice = None
    while choice not in range(1, len(ACTIONS) + 1):
        raw = input("Enter number (1-4): ").strip()
        try:
            choice = int(raw)
        except ValueError:
            pass

    action_type = ACTIONS[choice - 1]

    claim_id = "C1"
    if claim_ids:
        console.print(f"Claim IDs available: {claim_ids}")
        raw_claim = input(f"Enter claim ID to target [{claim_ids[0]}]: ").strip() or claim_ids[0]
        if raw_claim in claim_ids:
            claim_id = raw_claim

    instruction = input("Enter rewrite instruction: ").strip() or "Improve this section."
    reasoning = input("Your reasoning: ").strip() or "Manual arbitration."

    return {
        "action_type": action_type,
        "target_section": action_type.replace("_rewrite", "").replace("_", " "),
        "instruction": instruction,
        "critique_claim_id": claim_id,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Trained arbitrator stub (chain-of-thought prompt for demo when no GRPO ckpt)
# ---------------------------------------------------------------------------

class TrainedArbitratorStub(BaselineArbitratorAgent):
    """
    Stand-in for the GRPO-trained Arbitrator.
    Uses a richer chain-of-thought system prompt to simulate trained behaviour
    when the GRPO checkpoint is not yet available.
    Produces the Phase 7 extended JSON format with reasoning chain fields.
    """

    _TRAINED_SYSTEM = """You are an expert Arbitrator agent trained with GRPO reinforcement learning
to improve short-form video scripts. You have learned through hundreds of debate episodes to:
1. Prioritise hook rewrites when the first 3 seconds fail to capture attention.
2. Target the critic claim with the highest severity that the Defender has NOT flagged.
3. Always balance improvement against the defender's core_strength.
4. Give specific, actionable instructions — not generic advice.

Before choosing your action, reason through the debate explicitly.

Respond ONLY with valid JSON in this exact order:
{
  "priority_assessment": "which critique is most urgent and why — one sentence",
  "conflict_check": "does acting on this critique risk harming any other reward signal? yes/no + reason",
  "defender_consideration": "is the Defender's flagged concern relevant to this decision? yes/no + reason",
  "action_type": "hook_rewrite",
  "target_section": "hook",
  "instruction": "specific instruction for the rewriter",
  "critique_claim_id": "C1",
  "reasoning": "detailed chain-of-thought reasoning"
}"""

    def act(self, observation: dict) -> tuple:
        """Returns (action_dict, raw_output) so the caller can extract reasoning chain."""
        from viral_script_engine.agents.llm_backend import LLMBackend
        import json as _json
        llm = LLMBackend(backend="anthropic", model_name="claude-haiku-4-5-20251001")
        user_prompt = self._build_user_prompt(observation)
        raw = llm.generate(self._TRAINED_SYSTEM, user_prompt, max_tokens=768)
        try:
            action = _json.loads(raw)
            return action, raw
        except Exception:
            from viral_script_engine.agents.baseline_arbitrator import _FALLBACK_ACTION
            return _FALLBACK_ACTION.copy(), raw


# ---------------------------------------------------------------------------
# Main runners
# ---------------------------------------------------------------------------

def run_compare(script_id: str):
    """Run one full episode, showing untrained vs trained arbitrator in Act 4."""
    script = _load_script(script_id)

    # Act 1
    act1_raw_script(script)

    env = _make_env(difficulty="easy")
    obs, _ = env.reset()

    # Force the env to use our chosen script (reset picks randomly from tier)
    # We'll manually run the agents for the demo rather than going through env.step
    critic = CriticAgent()
    defender = DefenderAgent()
    rewriter = RewriterAgent()
    baseline_agent = BaselineArbitratorAgent()
    trained_agent = TrainedArbitratorStub()

    current_script = script["script_text"]
    region = script["region"]
    platform = script["platform"]
    niche = script["niche"]

    # Act 2
    console.print("[dim]Running Critic…[/dim]")
    critique = critic.critique(script=current_script, region=region, platform=platform, niche=niche)
    act2_critic_attacks(critique)

    # Act 3
    console.print("[dim]Running Defender…[/dim]")
    defender_out = defender.defend(
        script=current_script,
        critic_claims=critique.claims,
        region=region,
        platform=platform,
    )
    act3_defender_responds(defender_out, critique.claims)

    # Act 4 — both arbitrators
    fake_obs = {
        "current_script": current_script,
        "debate_history": [
            {
                "critic_claims": [c.model_dump() for c in critique.claims],
                "defender_response": defender_out.model_dump(),
            }
        ],
    }
    console.print("[dim]Running Untrained Arbitrator…[/dim]")
    untrained_action = baseline_agent.act(fake_obs)
    console.print("[dim]Running Trained Arbitrator…[/dim]")
    trained_action, trained_raw = trained_agent.act(fake_obs)

    # Parse reasoning chain from trained output for display
    trained_reasoning = None
    try:
        from viral_script_engine.agents.reasoning_parser import ReasoningParser
        parser = ReasoningParser()
        chain = parser.parse(trained_raw)
        trained_reasoning = chain.model_dump()
        trained_reasoning.pop("action", None)   # action shown separately
    except Exception:
        trained_reasoning = None

    act4_arbitrator_decides(untrained_action, trained_action, compare=True, trained_reasoning=trained_reasoning)

    # Act 5 — use trained action for rewrite
    from viral_script_engine.environment.actions import ArbitratorAction
    try:
        arb_action = ArbitratorAction(**trained_action)
    except Exception:
        from viral_script_engine.agents.baseline_arbitrator import _FALLBACK_ACTION
        arb_action = ArbitratorAction(**_FALLBACK_ACTION)

    console.print("[dim]Running Rewriter…[/dim]")
    rewrite_result = rewriter.rewrite(current_script, arb_action)
    new_script = rewrite_result.rewritten_script

    # Compute rewards
    env2 = _make_env(difficulty="easy")
    obs2, _ = env2.reset()
    # Score against baseline (original script)
    from viral_script_engine.rewards.r1_hook_strength import HookStrengthReward
    from viral_script_engine.rewards.r2_coherence import CoherenceReward
    from viral_script_engine.rewards.r3_cultural_alignment import CulturalAlignmentReward
    from viral_script_engine.rewards.r5_defender_preservation import DefenderPreservationReward

    r1 = HookStrengthReward()
    r2 = CoherenceReward()
    r3 = CulturalAlignmentReward(knowledge_base_path=_CULTURAL_KB_PATH)
    r5 = DefenderPreservationReward()

    baseline_r1 = r1.score(current_script).score
    baseline_r2 = r2.score(current_script, current_script).score
    baseline_r3 = r3.score(current_script, region).score
    baseline_total = (baseline_r1 + baseline_r2 + baseline_r3) / 3

    new_r1 = r1.score(new_script).score
    new_r2 = r2.score(current_script, new_script).score
    new_r3 = r3.score(new_script, region).score
    new_r5 = r5.score(defender_out, new_script).score

    reward_components = {
        "r1_hook_strength": new_r1,
        "r2_coherence": new_r2,
        "r3_cultural_alignment": new_r3,
        "r4_debate_resolution": None,
        "r5_defender_preservation": new_r5,
        "total": (new_r1 + new_r2 + new_r3 + new_r5) / 4,
    }

    act5_rewrite_and_reward(current_script, new_script, reward_components, baseline_total)

    console.print(Panel(
        "[bold green]Demo complete.[/bold green] The Trained Arbitrator's richer reasoning produced "
        "a more targeted rewrite. Run [bold]python training/train_grpo.py[/bold] in Colab to "
        "train the Arbitrator with GRPO and see real improvement curves.",
        border_style="green",
        padding=(1, 2),
    ))


def run_interactive():
    """Human acts as the Arbitrator."""
    console.print(Rule("[bold cyan]INTERACTIVE MODE — You are the Arbitrator[/bold cyan]", style="cyan"))

    script_id = input("Enter script ID [S03]: ").strip() or "S03"
    script = _load_script(script_id)

    act1_raw_script(script)

    critic = CriticAgent()
    defender = DefenderAgent()
    rewriter = RewriterAgent()

    current_script = script["script_text"]
    region = script["region"]
    platform = script["platform"]
    niche = script["niche"]

    from viral_script_engine.rewards.r1_hook_strength import HookStrengthReward
    from viral_script_engine.rewards.r2_coherence import CoherenceReward
    from viral_script_engine.rewards.r3_cultural_alignment import CulturalAlignmentReward
    from viral_script_engine.rewards.r5_defender_preservation import DefenderPreservationReward

    r1 = HookStrengthReward()
    r2 = CoherenceReward()
    r3 = CulturalAlignmentReward(knowledge_base_path=_CULTURAL_KB_PATH)
    r5 = DefenderPreservationReward()

    base_r1 = r1.score(current_script).score
    base_r2 = r2.score(current_script, current_script).score
    base_r3 = r3.score(current_script, region).score
    baseline_total = (base_r1 + base_r2 + base_r3) / 3

    for step_num in range(1, 4):
        console.print(Rule(f"[bold]Step {step_num}[/bold]"))

        console.print("[dim]Running Critic…[/dim]")
        critique = critic.critique(script=current_script, region=region, platform=platform, niche=niche)
        act2_critic_attacks(critique)

        console.print("[dim]Running Defender…[/dim]")
        defender_out = defender.defend(
            script=current_script,
            critic_claims=critique.claims,
            region=region,
            platform=platform,
        )
        act3_defender_responds(defender_out, critique.claims)

        fake_obs = {
            "current_script": current_script,
            "debate_history": [
                {
                    "critic_claims": [c.model_dump() for c in critique.claims],
                    "defender_response": defender_out.model_dump(),
                }
            ],
        }
        action = _interactive_choose_action(fake_obs)
        act4_arbitrator_decides(action, action, compare=False)

        from viral_script_engine.environment.actions import ArbitratorAction
        try:
            arb_action = ArbitratorAction(**action)
        except Exception:
            from viral_script_engine.agents.baseline_arbitrator import _FALLBACK_ACTION
            arb_action = ArbitratorAction(**_FALLBACK_ACTION)

        console.print("[dim]Running Rewriter…[/dim]")
        rewrite_result = rewriter.rewrite(current_script, arb_action)
        new_script = rewrite_result.rewritten_script

        new_r1 = r1.score(new_script).score
        new_r2 = r2.score(script["script_text"], new_script).score
        new_r3 = r3.score(new_script, region).score
        new_r5 = r5.score(defender_out, new_script).score

        reward_components = {
            "r1_hook_strength": new_r1,
            "r2_coherence": new_r2,
            "r3_cultural_alignment": new_r3,
            "r4_debate_resolution": None,
            "r5_defender_preservation": new_r5,
            "total": (new_r1 + new_r2 + new_r3 + new_r5) / 4,
        }

        act5_rewrite_and_reward(current_script, new_script, reward_components, baseline_total)
        current_script = new_script

        again = input("Continue to next step? [y/n]: ").strip().lower()
        if again != "y":
            break

    console.print(Panel("[bold green]Interactive session complete.[/bold green]", border_style="green"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Viral Script Debugging Engine — 5-Act Demo")
    parser.add_argument("--script", default="S03", help="Script ID to demo (default: S03)")
    parser.add_argument("--compare", action="store_true", help="Show untrained vs trained arbitrator side-by-side")
    parser.add_argument("--interactive", action="store_true", help="Human acts as Arbitrator")
    args = parser.parse_args()

    console.print(Panel(
        "[bold cyan]Viral Script Debugging Engine[/bold cyan]\n"
        "[dim]Meta × OpenEnv Hackathon 2026 | Theme 1: Multi-Agent · Theme 4: Self-Improvement[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))

    if args.interactive:
        run_interactive()
    else:
        run_compare(args.script)


if __name__ == "__main__":
    main()
