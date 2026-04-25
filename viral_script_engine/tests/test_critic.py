import json
import pytest
from unittest.mock import MagicMock, patch

from viral_script_engine.agents.critic import CritiqueClaim, CritiqueOutput
from viral_script_engine.evaluation.critic_evaluator import CriticEvaluator, EvaluationResult


# ── Task 2: Model parsing tests ───────────────────────────────────────────────

def test_critique_claim_parses_valid_json():
    data = {
        "claim_id": "C1",
        "critique_class": "hook_weakness",
        "claim_text": "The hook is too slow.",
        "timestamp_range": "0:00-0:03",
        "evidence": "Let me tell you a secret",
        "is_falsifiable": True,
        "severity": "high",
    }
    claim = CritiqueClaim(**data)
    assert claim.claim_id == "C1"
    assert claim.severity == "high"


def test_critique_output_parses_valid_json():
    data = {
        "claims": [
            {
                "claim_id": "C1",
                "critique_class": "hook_weakness",
                "claim_text": "Weak hook.",
                "timestamp_range": "0:00-0:03",
                "evidence": "Let me tell you",
                "is_falsifiable": True,
                "severity": "high",
            }
        ],
        "overall_severity": "high",
        "raw_response": '{"claims": []}',
    }
    output = CritiqueOutput(**data)
    assert len(output.claims) == 1


# ── Task 4: CriticEvaluator tests ────────────────────────────────────────────

SCRIPT_TEXT = "Let me tell you a secret about money. First, save twenty percent. Second, invest in index funds. Finally, avoid lifestyle inflation. That is all."


def _make_output(claims_data, overall="medium"):
    claims = [CritiqueClaim(**c) for c in claims_data]
    return CritiqueOutput(claims=claims, overall_severity=overall, raw_response="{}")


def test_evaluator_passes_good_critique():
    output = _make_output([
        {"claim_id": "C1", "critique_class": "hook_weakness", "claim_text": "x", "timestamp_range": "0:00-0:03", "evidence": "Let me tell you a secret", "is_falsifiable": True, "severity": "high"},
        {"claim_id": "C2", "critique_class": "cta_buried", "claim_text": "x", "timestamp_range": "0:10-0:15", "evidence": "That is all", "is_falsifiable": True, "severity": "medium"},
        {"claim_id": "C3", "critique_class": "pacing_issue", "claim_text": "x", "timestamp_range": "N/A", "evidence": "save twenty percent", "is_falsifiable": True, "severity": "low"},
    ])
    evaluator = CriticEvaluator()
    result = evaluator.evaluate(output, SCRIPT_TEXT)
    assert result.passes_gate is True
    assert result.claim_count == 3
    assert result.specificity_score >= 0.6
    assert result.falsifiability_score >= 0.7


def test_evaluator_fails_too_few_claims():
    output = _make_output([
        {"claim_id": "C1", "critique_class": "hook_weakness", "claim_text": "x", "timestamp_range": "0:00-0:03", "evidence": "Let me tell you", "is_falsifiable": True, "severity": "high"},
        {"claim_id": "C2", "critique_class": "cta_buried", "claim_text": "x", "timestamp_range": "0:10", "evidence": "invest", "is_falsifiable": True, "severity": "medium"},
    ])
    evaluator = CriticEvaluator()
    result = evaluator.evaluate(output, SCRIPT_TEXT)
    assert result.passes_gate is False
    assert result.claim_count == 2


def test_evaluator_fails_low_specificity():
    output = _make_output([
        {"claim_id": "C1", "critique_class": "hook_weakness", "claim_text": "x", "timestamp_range": "0:00-0:03", "evidence": "this quote is not in the script", "is_falsifiable": True, "severity": "high"},
        {"claim_id": "C2", "critique_class": "cta_buried", "claim_text": "x", "timestamp_range": "0:10", "evidence": "also not in script", "is_falsifiable": False, "severity": "medium"},
        {"claim_id": "C3", "critique_class": "pacing_issue", "claim_text": "x", "timestamp_range": "N/A", "evidence": "still not in script", "is_falsifiable": False, "severity": "low"},
    ])
    evaluator = CriticEvaluator()
    result = evaluator.evaluate(output, SCRIPT_TEXT)
    assert result.passes_gate is False


# ── Task 5: CLI exit-code test ────────────────────────────────────────────────

import os
import subprocess
import sys


def test_cli_dry_run_exits_zero_or_one():
    """CLI must exit 0 (pass) or 1 (fail) — never crash with unhandled exception."""
    result = subprocess.run(
        [sys.executable, "scripts/run_critic_gate.py", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(__import__("pathlib").Path(__file__).parent.parent),
        env={**os.environ, "ANTHROPIC_API_KEY": "sk-fake-key-for-test"},
    )
    assert result.returncode in (0, 1), (
        f"Unexpected exit code: {result.returncode}\nSTDERR: {result.stderr}"
    )


# ── Task 6: Mocked CriticAgent tests ─────────────────────────────────────────

from viral_script_engine.agents.critic import CriticAgent, CriticParseError

MOCK_VALID_JSON = json.dumps({
    "claims": [
        {"claim_id": "C1", "critique_class": "hook_weakness", "claim_text": "Weak hook.", "timestamp_range": "0:00-0:03", "evidence": "Let me tell you a secret", "is_falsifiable": True, "severity": "high"},
        {"claim_id": "C2", "critique_class": "cta_buried", "claim_text": "CTA at end.", "timestamp_range": "0:45-0:50", "evidence": "Like and save this video", "is_falsifiable": True, "severity": "medium"},
        {"claim_id": "C3", "critique_class": "pacing_issue", "claim_text": "Pacing issue.", "timestamp_range": "N/A", "evidence": "save twenty percent", "is_falsifiable": True, "severity": "low"},
    ],
    "overall_severity": "high",
})

MOCK_INVALID_JSON = "Here is my feedback: The hook is weak and the CTA is missing."


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
@patch("viral_script_engine.agents.critic.anthropic.Anthropic")
def test_critic_agent_returns_critique_output(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=MOCK_VALID_JSON)]
    mock_client.messages.create.return_value = mock_msg

    agent = CriticAgent()
    result = agent.critique("Some script text here", "Mumbai", "Reels", "finance")

    assert len(result.claims) == 3
    assert result.claims[0].claim_id == "C1"
    assert result.overall_severity == "high"
    assert mock_client.messages.create.call_count == 1


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
@patch("viral_script_engine.agents.critic.anthropic.Anthropic")
def test_critic_agent_retries_on_bad_json(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    bad_msg = MagicMock()
    bad_msg.content = [MagicMock(text=MOCK_INVALID_JSON)]
    good_msg = MagicMock()
    good_msg.content = [MagicMock(text=MOCK_VALID_JSON)]
    mock_client.messages.create.side_effect = [bad_msg, good_msg]

    agent = CriticAgent()
    result = agent.critique("Some script text here", "Mumbai", "Reels", "finance")
    assert len(result.claims) == 3
    assert mock_client.messages.create.call_count == 2


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
@patch("viral_script_engine.agents.critic.anthropic.Anthropic")
def test_critic_agent_raises_parse_error_after_two_failures(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    bad_msg = MagicMock()
    bad_msg.content = [MagicMock(text=MOCK_INVALID_JSON)]
    mock_client.messages.create.return_value = bad_msg

    agent = CriticAgent()
    with pytest.raises(CriticParseError):
        agent.critique("Some script text here", "Mumbai", "Reels", "finance")
    assert mock_client.messages.create.call_count == 2
