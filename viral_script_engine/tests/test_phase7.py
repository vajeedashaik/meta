"""
Phase 7 tests — Process-Aware Reward Shaping
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.agents.critic import CritiqueClaim
from viral_script_engine.agents.defender import DefenderOutput
from viral_script_engine.agents.reasoning_parser import (
    ArbitratorParseError,
    ReasoningChain,
    ReasoningParser,
)
from viral_script_engine.environment.actions import ArbitratorAction, ActionType
from viral_script_engine.environment.observations import RewardComponents
from viral_script_engine.rewards.process_reward import ProcessReward, ProcessRewardResult
from viral_script_engine.rewards.process_verifier import ProcessVerifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def parser():
    return ReasoningParser()


@pytest.fixture
def verifier():
    return ProcessVerifier()


@pytest.fixture
def process_reward():
    return ProcessReward()


def _make_claim(claim_id: str, critique_class: str, severity: str) -> CritiqueClaim:
    return CritiqueClaim(
        claim_id=claim_id,
        critique_class=critique_class,
        claim_text=f"Test claim for {critique_class}",
        timestamp_range="0:00-0:05",
        evidence="test evidence",
        is_falsifiable=True,
        severity=severity,
    )


def _make_action(
    action_type: str = "hook_rewrite",
    target_section: str = "hook",
) -> ArbitratorAction:
    return ArbitratorAction(
        action_type=action_type,
        target_section=target_section,
        instruction="Test instruction",
        critique_claim_id="C1",
        reasoning="Test reasoning",
    )


def _make_defender(core_strength_quote: str = "The hook is strong and engaging") -> DefenderOutput:
    return DefenderOutput(
        core_strength="Great opening hook",
        core_strength_quote=core_strength_quote,
        defense_argument="This element should be preserved",
        flagged_critic_claims=["C2"],
        regional_voice_elements=["local phrase"],
    )


def _make_components(**kwargs) -> RewardComponents:
    rc = RewardComponents(**kwargs)
    rc.compute_total()
    return rc


# ---------------------------------------------------------------------------
# ReasoningParser tests
# ---------------------------------------------------------------------------

_FULL_JSON = json.dumps({
    "priority_assessment": "hook_weakness is highest severity (high) — opens weakly",
    "conflict_check": "yes — hook rewrite risks R3 cultural alignment",
    "defender_consideration": "yes — core strength is in hook section",
    "action_type": "hook_rewrite",
    "target_section": "hook",
    "instruction": "Replace generic opener with Mumbai local reference",
    "critique_claim_id": "C1",
    "reasoning": "Hook is highest severity, must be fixed first",
})

_MINIMAL_JSON = json.dumps({
    "action_type": "hook_rewrite",
    "target_section": "hook",
    "instruction": "Fix the hook",
    "critique_claim_id": "C1",
    "reasoning": "default",
})


def test_reasoning_parser_full_json(parser):
    chain = parser.parse(_FULL_JSON)
    assert isinstance(chain, ReasoningChain)
    assert "hook_weakness" in chain.priority_assessment
    assert chain.conflict_check_answer == "yes"
    assert chain.defender_consideration_answer == "yes"
    assert chain.action.action_type == ActionType.HOOK_REWRITE


def test_reasoning_parser_fallback_missing_reasoning(parser):
    """Baseline model output without reasoning fields should parse without error."""
    chain = parser.parse(_MINIMAL_JSON)
    assert chain.priority_assessment == ""
    assert chain.conflict_check_answer == ""
    assert chain.defender_consideration_answer == ""
    assert chain.action.action_type == ActionType.HOOK_REWRITE


def test_reasoning_parser_raises_on_invalid_action(parser):
    bad_json = json.dumps({"action_type": "invalid_action", "target_section": "hook"})
    with pytest.raises(ArbitratorParseError):
        parser.parse(bad_json)


def test_reasoning_parser_raises_on_missing_action(parser):
    bad_json = json.dumps({"priority_assessment": "something"})
    with pytest.raises(ArbitratorParseError):
        parser.parse(bad_json)


# ---------------------------------------------------------------------------
# ProcessVerifier.verify_priority_assessment tests
# ---------------------------------------------------------------------------

def test_verify_priority_high_severity_mention(verifier):
    claims = [
        _make_claim("C1", "hook_weakness", "high"),
        _make_claim("C2", "pacing_issue", "medium"),
        _make_claim("C3", "cta_buried", "low"),
    ]
    rc = _make_components(r1_hook_strength=0.5)
    score = verifier.verify_priority_assessment(
        priority_assessment="hook_weakness is the most urgent issue",
        critic_claims=claims,
        current_reward_components=rc,
    )
    assert score == 1.0


def test_verify_priority_medium_severity_mention(verifier):
    claims = [
        _make_claim("C1", "hook_weakness", "high"),
        _make_claim("C2", "pacing_issue", "medium"),
    ]
    rc = _make_components(r1_hook_strength=0.5)
    score = verifier.verify_priority_assessment(
        priority_assessment="pacing_issue should be addressed",
        critic_claims=claims,
        current_reward_components=rc,
    )
    assert score == 0.5


def test_verify_priority_random_mention_scores_zero(verifier):
    claims = [
        _make_claim("C1", "hook_weakness", "high"),
        _make_claim("C2", "pacing_issue", "medium"),
    ]
    rc = _make_components(r1_hook_strength=0.5)
    score = verifier.verify_priority_assessment(
        priority_assessment="we should just make this better",
        critic_claims=claims,
        current_reward_components=rc,
    )
    assert score == 0.0


def test_verify_priority_empty_assessment(verifier):
    claims = [_make_claim("C1", "hook_weakness", "high")]
    rc = _make_components()
    score = verifier.verify_priority_assessment("", claims, rc)
    assert score == 0.0


# ---------------------------------------------------------------------------
# ProcessVerifier.verify_conflict_check tests — all 4 known patterns
# ---------------------------------------------------------------------------

def test_conflict_check_hook_rewrite_with_high_r3(verifier):
    action = _make_action("hook_rewrite", "hook")
    start = _make_components(r1_hook_strength=0.6, r3_cultural_alignment=0.75)
    current = _make_components(r1_hook_strength=0.6, r3_cultural_alignment=0.80)
    # r3 >= 0.7 → conflict exists → correct answer is "yes"
    score = verifier.verify_conflict_check("yes — hook rewrite risks cultural refs", "", action, current, start)
    assert score == 1.0
    score_wrong = verifier.verify_conflict_check("no — no conflict", "", action, current, start)
    assert score_wrong == 0.0


def test_conflict_check_section_reorder_with_low_r2(verifier):
    action = _make_action("section_reorder", "body")
    start = _make_components(r2_coherence=0.5)
    current = _make_components(r2_coherence=0.5)
    # r2 <= 0.6 → conflict exists
    score = verifier.verify_conflict_check("yes", "", action, current, start)
    assert score == 1.0


def test_conflict_check_cultural_ref_sub_with_low_r5(verifier):
    action = _make_action("cultural_ref_sub", "full")
    start = _make_components(r5_defender_preservation=0.4)
    current = _make_components(r5_defender_preservation=0.4)
    # r5 <= 0.5 → conflict exists
    score = verifier.verify_conflict_check("yes", "", action, current, start)
    assert score == 1.0


def test_conflict_check_cta_placement_with_low_r1(verifier):
    action = _make_action("cta_placement", "cta")
    start = _make_components(r1_hook_strength=0.3)
    current = _make_components(r1_hook_strength=0.3)
    # r1 <= 0.4 → conflict exists
    score = verifier.verify_conflict_check("yes — CTA premature while hook is weak", "", action, current, start)
    assert score == 1.0
    score_wrong = verifier.verify_conflict_check("no conflict detected", "", action, current, start)
    assert score_wrong == 0.0


def test_conflict_check_no_conflict_scenario(verifier):
    # hook_rewrite when r3 < 0.7 → no conflict → correct answer is "no"
    action = _make_action("hook_rewrite", "hook")
    start = _make_components(r3_cultural_alignment=0.5)
    current = _make_components(r3_cultural_alignment=0.5)
    score = verifier.verify_conflict_check("no — r3 is low, no conflict", "", action, current, start)
    assert score == 1.0


# ---------------------------------------------------------------------------
# ProcessVerifier.verify_defender_consideration tests
# ---------------------------------------------------------------------------

def test_defender_consideration_yes_when_core_in_target(verifier):
    # Core strength is in hook, action targets hook → should say yes
    action = _make_action("hook_rewrite", "hook")
    defender = _make_defender(core_strength_quote="The opening hook draws viewers immediately")
    score = verifier.verify_defender_consideration("yes", "", action, defender)
    assert score == 1.0


def test_defender_consideration_no_when_core_not_in_target(verifier):
    # Core strength is in CTA section, action targets hook → should say no
    action = _make_action("hook_rewrite", "hook")
    defender = _make_defender(core_strength_quote="The ending call to action is very strong")
    score = verifier.verify_defender_consideration("no", "", action, defender)
    assert score == 1.0


def test_defender_consideration_wrong_answer_scores_zero(verifier):
    action = _make_action("hook_rewrite", "hook")
    defender = _make_defender(core_strength_quote="The opening hook draws viewers immediately")
    score = verifier.verify_defender_consideration("no — no overlap", "", action, defender)
    assert score == 0.0


def test_defender_consideration_empty_answer(verifier):
    action = _make_action("hook_rewrite", "hook")
    defender = _make_defender()
    score = verifier.verify_defender_consideration("", "", action, defender)
    assert score == 0.0


# ---------------------------------------------------------------------------
# ProcessReward.score() weighted total
# ---------------------------------------------------------------------------

def test_process_reward_correct_weighted_total(process_reward):
    claims = [
        _make_claim("C1", "hook_weakness", "high"),
        _make_claim("C2", "pacing_issue", "medium"),
    ]
    defender = _make_defender(core_strength_quote="The opening hook draws viewers immediately")
    rc = _make_components(r1_hook_strength=0.5, r2_coherence=0.5, r3_cultural_alignment=0.8)
    start = _make_components(r1_hook_strength=0.5, r2_coherence=0.5, r3_cultural_alignment=0.8)

    chain = ReasoningChain(
        priority_assessment="hook_weakness is highest severity",
        conflict_check_answer="yes",
        conflict_check_reason="hook rewrite risks r3",
        defender_consideration_answer="yes",
        defender_consideration_reason="core strength is in hook",
        action=_make_action("hook_rewrite", "hook"),
    )

    result = process_reward.score(chain, claims, defender, rc, start)
    assert isinstance(result, ProcessRewardResult)
    # All three checks should score 1.0 → process_score = 1.0, contribution = 0.15
    assert result.priority_score == 1.0
    assert result.conflict_score == 1.0     # hook_rewrite + r3 >= 0.7 → conflict, model says yes
    assert result.defender_score == 1.0
    assert abs(result.process_score - 1.0) < 1e-6
    assert abs(result.weighted_contribution - 0.15) < 1e-6


def test_process_reward_zero_for_empty_reasoning(process_reward):
    claims = [_make_claim("C1", "hook_weakness", "high")]
    defender = _make_defender()
    rc = _make_components(r1_hook_strength=0.5)
    start = _make_components(r1_hook_strength=0.5)

    chain = ReasoningChain(
        priority_assessment="",
        conflict_check_answer="",
        conflict_check_reason="",
        defender_consideration_answer="",
        defender_consideration_reason="",
        action=_make_action("hook_rewrite", "hook"),
    )

    result = process_reward.score(chain, claims, defender, rc, start)
    assert result.process_score == 0.0
    assert result.weighted_contribution == 0.0


# ---------------------------------------------------------------------------
# env.step() integration — process_reward in RewardComponents
# ---------------------------------------------------------------------------

_ACTION = {
    "action_type": "hook_rewrite",
    "target_section": "hook",
    "instruction": "Make the hook more engaging.",
    "critique_claim_id": "C1",
    "reasoning": "Test",
}

_SCRIPTS_PATH = str(Path(__file__).parent.parent / "data" / "test_scripts" / "scripts.json")
_CULTURAL_KB = str(Path(__file__).parent.parent / "data" / "cultural_kb.json")

_MOCK_CRITIC = json.dumps({
    "claims": [
        {
            "claim_id": "C1",
            "critique_class": "hook_weakness",
            "claim_text": "Weak hook.",
            "timestamp_range": "0:00-0:03",
            "evidence": "generic opener",
            "is_falsifiable": True,
            "severity": "high",
        }
    ],
    "overall_severity": "high",
})

_MOCK_DEFENDER = json.dumps({
    "core_strength": "Strong regional authenticity",
    "core_strength_quote": "The hook draws viewers immediately",
    "defense_argument": "Regional voice is valuable",
    "flagged_critic_claims": [],
    "regional_voice_elements": ["local phrase"],
})

_MOCK_REWRITER = json.dumps({
    "rewritten_script": "Better script content here.",
    "changes_made": ["improved hook"],
})


def _multi_mock(sys_prompt, usr_prompt, **kw):
    """Return appropriate mock JSON based on which agent is calling."""
    if "core_strength" in sys_prompt or "defender" in sys_prompt.lower():
        return _MOCK_DEFENDER
    if "rewriter" in sys_prompt.lower() or "rewrite" in sys_prompt.lower()[:50]:
        return _MOCK_REWRITER
    return _MOCK_CRITIC


@pytest.fixture
def env_mock_llm(monkeypatch):
    monkeypatch.setattr(
        "viral_script_engine.agents.llm_backend.LLMBackend.generate",
        lambda self, sys_prompt, usr_prompt, **kw: _multi_mock(sys_prompt, usr_prompt, **kw),
    )


def _make_env():
    from viral_script_engine.environment.env import ViralScriptEnv
    return ViralScriptEnv(
        scripts_path=_SCRIPTS_PATH,
        cultural_kb_path=_CULTURAL_KB,
        max_steps=1,
        difficulty="easy",
        use_escalation=False,
    )


def test_env_step_has_process_reward_key(env_mock_llm):
    """env.step() must include process_reward key in reward_components."""
    env = _make_env()
    env.reset()
    _, _, _, _, info = env.step(_ACTION)
    rc = info["reward_components"]
    assert "process_reward" in rc


def test_env_step_process_reward_graceful_zero(env_mock_llm):
    """process_reward is None when no raw_output is supplied (graceful zero)."""
    env = _make_env()
    env.reset()
    _, _, _, _, info = env.step(_ACTION)   # no raw_output
    rc = info["reward_components"]
    assert rc.get("process_reward") is None
    assert info.get("process_reward_result") is None
