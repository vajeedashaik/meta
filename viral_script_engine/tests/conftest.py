import json
import pytest

MOCK_VALID_RESPONSE = json.dumps({
    "claims": [
        {
            "claim_id": "C1",
            "critique_class": "hook_weakness",
            "claim_text": "Weak hook.",
            "timestamp_range": "0:00-0:03",
            "evidence": "Let me tell you a secret",
            "is_falsifiable": True,
            "severity": "high",
        },
        {
            "claim_id": "C2",
            "critique_class": "cta_buried",
            "claim_text": "CTA at end.",
            "timestamp_range": "0:45-0:50",
            "evidence": "Like and save this video",
            "is_falsifiable": True,
            "severity": "medium",
        },
        {
            "claim_id": "C3",
            "critique_class": "pacing_issue",
            "claim_text": "Pacing issue.",
            "timestamp_range": "N/A",
            "evidence": "save twenty percent",
            "is_falsifiable": True,
            "severity": "low",
        },
    ],
    "overall_severity": "high",
})


@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setattr(
        "viral_script_engine.agents.llm_backend.LLMBackend.generate",
        lambda self, sys_prompt, usr_prompt, **kw: MOCK_VALID_RESPONSE,
    )
    return MOCK_VALID_RESPONSE
