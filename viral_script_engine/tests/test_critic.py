import json
import pytest
from unittest.mock import MagicMock, patch

from viral_script_engine.agents.critic import CritiqueClaim, CritiqueOutput


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
