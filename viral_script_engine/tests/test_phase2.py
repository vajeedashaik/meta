import json
import pytest
from unittest.mock import MagicMock, patch

from viral_script_engine.agents.defender import DefenderAgent, DefenderOutput, DefenderParseError
from viral_script_engine.agents.critic import CritiqueClaim
from viral_script_engine.environment.actions import ActionType, ArbitratorAction
from viral_script_engine.rewards.r3_cultural_alignment import CulturalAlignmentReward
from viral_script_engine.rewards.r4_debate_resolution import DebateResolutionReward, DebateResolutionResult
from viral_script_engine.rewards.r5_defender_preservation import DefenderPreservationReward
from viral_script_engine.rewards.reward_aggregator import RewardAggregator, AntiGamingLog
from viral_script_engine.environment.observations import RewardComponents


# ─── fixtures ────────────────────────────────────────────────────────────────

MOCK_DEFENDER_RESPONSE = json.dumps({
    "core_strength": "Relatable hook about saving money",
    "core_strength_quote": "Let me tell you a secret",
    "defense_argument": "This creates immediate viewer curiosity and should not be changed.",
    "flagged_critic_claims": ["C2"],
    "regional_voice_elements": ["yaar", "ek dum solid"],
})

MOCK_CRITIQUE_CLAIMS = [
    CritiqueClaim(
        claim_id="C1",
        critique_class="hook_weakness",
        claim_text="Weak hook.",
        timestamp_range="0:00-0:03",
        evidence="Let me tell you a secret",
        is_falsifiable=True,
        severity="high",
    ),
    CritiqueClaim(
        claim_id="C2",
        critique_class="cta_buried",
        claim_text="CTA at end.",
        timestamp_range="0:45-0:50",
        evidence="Like and save this video",
        is_falsifiable=True,
        severity="medium",
    ),
]


@pytest.fixture
def mock_defender_llm(monkeypatch):
    monkeypatch.setattr(
        "viral_script_engine.agents.llm_backend.LLMBackend.generate",
        lambda self, sys_prompt, usr_prompt, **kw: MOCK_DEFENDER_RESPONSE,
    )


# ─── Step 1: DefenderAgent ────────────────────────────────────────────────────

def test_defender_parses_output(mock_defender_llm):
    agent = DefenderAgent()
    result = agent.defend(
        script="Let me tell you a secret about saving money. yaar, ek dum solid plan.",
        critic_claims=MOCK_CRITIQUE_CLAIMS,
        region="mumbai_gen_z",
        platform="instagram",
    )
    assert isinstance(result, DefenderOutput)
    assert result.core_strength_quote == "Let me tell you a secret"
    assert "C2" in result.flagged_critic_claims
    assert "yaar" in result.regional_voice_elements


def test_defender_retries_on_invalid_json(monkeypatch):
    call_count = {"n": 0}

    def fake_generate(self, sys_prompt, usr_prompt, **kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "NOT JSON AT ALL"
        return MOCK_DEFENDER_RESPONSE

    monkeypatch.setattr(
        "viral_script_engine.agents.llm_backend.LLMBackend.generate",
        fake_generate,
    )
    agent = DefenderAgent()
    result = agent.defend("script", MOCK_CRITIQUE_CLAIMS, "mumbai_gen_z", "instagram")
    assert isinstance(result, DefenderOutput)
    assert call_count["n"] == 2


def test_defender_raises_after_two_failures(monkeypatch):
    monkeypatch.setattr(
        "viral_script_engine.agents.llm_backend.LLMBackend.generate",
        lambda self, sys_prompt, usr_prompt, **kw: "BAD JSON",
    )
    agent = DefenderAgent()
    with pytest.raises(DefenderParseError):
        agent.defend("script", MOCK_CRITIQUE_CLAIMS, "mumbai_gen_z", "instagram")


# ─── Step 2: R3 CulturalAlignmentReward ──────────────────────────────────────

@pytest.fixture
def r3(tmp_path):
    kb = {
        "mumbai_gen_z": {
            "valid_refs": ["Bandra", "CSMT", "local train", "Swiggy", "IPL"],
            "correct_idioms": ["ek dum solid", "kya scene hai", "full on"],
            "invalid_signals": ["trunk call", "VHS", "walkman"],
            "anachronistic_signals": [],
        },
        "tier2_hindi_belt": {
            "valid_refs": ["kirana store", "sabzi mandi", "jugaad", "panchayat", "mela"],
            "correct_idioms": ["bilkul sahi", "arey bhai", "seedha baat"],
            "invalid_signals": ["SaaS", "venture capital", "coworking space"],
            "anachronistic_signals": [],
        },
    }
    kb_path = tmp_path / "test_kb.json"
    kb_path.write_text(json.dumps(kb), encoding="utf-8")
    return CulturalAlignmentReward(knowledge_base_path=str(kb_path))


def test_r3_scores_regional_script(r3):
    script = "Take the local train to Bandra. IPL is on at night. ek dum solid plan yaar."
    result = r3.score(script, "mumbai_gen_z")
    assert result.score > 0.0
    assert "local train" in result.valid_refs_found or "Bandra" in result.valid_refs_found


def test_r3_scores_non_regional_script_lower(r3):
    script = "Buy on Amazon. Use your credit card. Free delivery available nationwide."
    regional = r3.score(
        "Take local train to Bandra. IPL is on. ek dum solid.", "mumbai_gen_z"
    )
    non_regional = r3.score(script, "mumbai_gen_z")
    assert regional.score >= non_regional.score


def test_r3_penalises_invalid_signals(r3):
    script = "This is like an old VHS walkman trunk call era."
    result = r3.score(script, "mumbai_gen_z")
    assert result.score == 0.0
    assert len(result.invalid_signals_found) > 0


def test_r3_neutral_for_unknown_region(r3):
    result = r3.score("any script", "unknown_region_xyz")
    assert result.score == 0.5


def test_r3_tier2_valid(r3):
    script = "Went to kirana store, met at sabzi mandi, pure jugaad. bilkul sahi plan."
    result = r3.score(script, "tier2_hindi_belt")
    assert result.score > 0.0


def test_r3_tier2_penalises_metro_jargon(r3):
    script = "We raised SaaS venture capital at a coworking space."
    result = r3.score(script, "tier2_hindi_belt")
    assert len(result.invalid_signals_found) > 0


# ─── Step 3: R4 DebateResolutionReward ───────────────────────────────────────

def _make_critique_output(claims):
    from viral_script_engine.agents.critic import CritiqueOutput
    return CritiqueOutput(claims=claims, overall_severity="medium", raw_response="")


def _make_claim(claim_id, critique_class, timestamp_range, severity="high"):
    return CritiqueClaim(
        claim_id=claim_id,
        critique_class=critique_class,
        claim_text="test claim",
        timestamp_range=timestamp_range,
        evidence="evidence text",
        is_falsifiable=True,
        severity=severity,
    )


def _make_action():
    return ArbitratorAction(
        action_type=ActionType.HOOK_REWRITE,
        target_section="hook",
        instruction="fix hook",
        critique_claim_id="C1",
        reasoning="test",
    )


def test_r4_resolved_when_no_matching_claim():
    mock_critic = MagicMock()
    mock_critic.critique.return_value = _make_critique_output([
        _make_claim("C1", "cta_buried", "0:45-0:50"),
    ])
    r4 = DebateResolutionReward(critic_agent=mock_critic)
    original_claim = _make_claim("C1", "hook_weakness", "0:00-0:03", "high")
    result = r4.score("new script", _make_action(), original_claim,
                      "mumbai_gen_z", "instagram", "finance")
    assert result.score == 1.0
    assert result.resolution_status == "resolved"


def test_r4_partially_resolved_when_severity_drops():
    mock_critic = MagicMock()
    mock_critic.critique.return_value = _make_critique_output([
        _make_claim("C1", "hook_weakness", "0:01-0:04", "low"),
    ])
    r4 = DebateResolutionReward(critic_agent=mock_critic)
    original_claim = _make_claim("C1", "hook_weakness", "0:00-0:03", "high")
    result = r4.score("new script", _make_action(), original_claim,
                      "mumbai_gen_z", "instagram", "finance")
    assert result.score == 0.5
    assert result.resolution_status == "partially_resolved"


def test_r4_persists_when_same_severity():
    mock_critic = MagicMock()
    mock_critic.critique.return_value = _make_critique_output([
        _make_claim("C1", "hook_weakness", "0:01-0:03", "high"),
    ])
    r4 = DebateResolutionReward(critic_agent=mock_critic)
    original_claim = _make_claim("C1", "hook_weakness", "0:00-0:03", "high")
    result = r4.score("new script", _make_action(), original_claim,
                      "mumbai_gen_z", "instagram", "finance")
    assert result.score == 0.0
    assert result.resolution_status == "persists"


# ─── Step 4: R5 DefenderPreservationReward ───────────────────────────────────

def _make_defender_output(quote: str) -> DefenderOutput:
    return DefenderOutput(
        core_strength="Strong opening",
        core_strength_quote=quote,
        defense_argument="Should be preserved.",
        flagged_critic_claims=[],
        regional_voice_elements=[],
    )


def test_r5_high_score_when_quote_present():
    r5 = DefenderPreservationReward()
    quote = "Let me tell you a secret about saving money every month."
    script = "Let me tell you a secret about saving money every month. This is the key insight."
    defender_out = _make_defender_output(quote)
    result = r5.score(defender_out, script)
    assert result.score >= 0.85


def test_r5_zero_score_when_quote_absent():
    r5 = DefenderPreservationReward()
    quote = "Completely different text that shares nothing with rewrite."
    script = "Today we discuss quantum physics and neutron stars in distant galaxies."
    defender_out = _make_defender_output(quote)
    result = r5.score(defender_out, script)
    assert result.score < 0.65


# ─── Step 5/6: AntiGamingLog and RewardAggregator ────────────────────────────

def _make_components(**kwargs) -> RewardComponents:
    defaults = dict(
        r1_hook_strength=0.7, r2_coherence=0.7,
        r3_cultural_alignment=0.7,
        r4_debate_resolution=None,
        r5_defender_preservation=None,
    )
    defaults.update(kwargs)
    rc = RewardComponents(**defaults)
    rc.compute_total()
    return rc


def test_anti_gaming_catastrophic_drop_zeroes_reward():
    aggregator = RewardAggregator()
    start = _make_components(r2_coherence=0.8)
    current = _make_components(r2_coherence=0.4)

    result, log = aggregator.compute(current, start, [], episode_id="ep1", step_num=1)

    assert result.total == 0.0
    assert log.triggered is True
    assert log.rule_triggered == "catastrophic_drop"
    assert log.component_that_dropped == "r2_coherence"
    assert log.post_penalty_total == 0.0


def test_anti_gaming_diversity_penalty_fires_on_3x_same():
    aggregator = RewardAggregator()
    start = _make_components()
    current = _make_components()
    history = [ActionType.HOOK_REWRITE] * 3

    result, log = aggregator.compute(current, start, history, episode_id="ep2", step_num=2)

    assert log.triggered is True
    assert log.rule_triggered == "action_repetition"
    assert log.penalty_applied == 0.15


def test_anti_gaming_log_not_triggered_clean():
    aggregator = RewardAggregator()
    start = _make_components()
    current = _make_components()
    history = [ActionType.HOOK_REWRITE, ActionType.CTA_PLACEMENT, ActionType.SECTION_REORDER]

    result, log = aggregator.compute(current, start, history, episode_id="ep3", step_num=1)

    assert log.triggered is False
    assert log.rule_triggered is None
    assert log.penalty_applied == 0.0


def test_anti_gaming_log_fields_populated():
    aggregator = RewardAggregator()
    start = _make_components(r1_hook_strength=0.9)
    current = _make_components(r1_hook_strength=0.5)

    _, log = aggregator.compute(current, start, [], episode_id="myep", step_num=3)

    assert log.episode_id == "myep"
    assert log.step_num == 3
    assert isinstance(log, AntiGamingLog)
