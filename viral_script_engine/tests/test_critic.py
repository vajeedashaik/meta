import json
import os
import subprocess
import sys

import pytest
from unittest.mock import patch

from viral_script_engine.agents.critic import CritiqueClaim, CritiqueOutput, CriticAgent, CriticParseError
from viral_script_engine.evaluation.critic_evaluator import CriticEvaluator, EvaluationResult
from tests.conftest import MOCK_VALID_RESPONSE

MOCK_INVALID_RESPONSE = "Here is my feedback: The hook is weak and the CTA is missing."


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

def test_cli_dry_run_exits_zero_or_one():
    """CLI must exit 0 (pass) or 1 (fail) — never crash with unhandled exception."""
    result = subprocess.run(
        [sys.executable, "scripts/run_critic_gate.py", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(__import__("pathlib").Path(__file__).parent.parent),
        env={**os.environ},
    )
    assert result.returncode in (0, 1), (
        f"Unexpected exit code: {result.returncode}\nSTDERR: {result.stderr}"
    )


# ── Task 6: Mocked CriticAgent tests ─────────────────────────────────────────

def test_critic_agent_returns_critique_output(mock_llm):
    agent = CriticAgent(backend="qwen")
    result = agent.critique("Some script text here", "Mumbai", "Reels", "finance")
    assert len(result.claims) == 3
    assert result.claims[0].claim_id == "C1"
    assert result.overall_severity == "high"


def test_critic_agent_retries_on_bad_json(monkeypatch):
    calls = []

    def fake_generate(self, sys_prompt, usr_prompt, **kw):
        calls.append(usr_prompt)
        if len(calls) == 1:
            return MOCK_INVALID_RESPONSE
        return MOCK_VALID_RESPONSE

    monkeypatch.setattr(
        "viral_script_engine.agents.llm_backend.LLMBackend.generate", fake_generate
    )
    agent = CriticAgent(backend="qwen")
    result = agent.critique("Some script text here", "Mumbai", "Reels", "finance")
    assert len(result.claims) == 3
    assert len(calls) == 2


def test_critic_agent_raises_parse_error_after_two_failures(monkeypatch):
    monkeypatch.setattr(
        "viral_script_engine.agents.llm_backend.LLMBackend.generate",
        lambda self, sys_prompt, usr_prompt, **kw: MOCK_INVALID_RESPONSE,
    )
    agent = CriticAgent(backend="qwen")
    with pytest.raises(CriticParseError):
        agent.critique("Some script text here", "Mumbai", "Reels", "finance")
