import json
from pathlib import Path
from typing import Any, Dict, Optional


class PersonaKB:
    """Wrapper around persona_advice_kb.json. Provides tier-keyed rule lookups."""

    def __init__(self, kb_path: Optional[str] = None):
        if kb_path is None:
            kb_path = str(Path(__file__).parent.parent / "data" / "persona_advice_kb.json")
        with open(kb_path, encoding="utf-8") as f:
            self._kb: Dict[str, Any] = json.load(f)

    def get_rules(self, tier: str) -> Dict[str, Any]:
        return self._kb.get(tier, {})

    def priority_actions(self, tier: str) -> list:
        return self.get_rules(tier).get("priority_actions", [])

    def deprioritised_actions(self, tier: str) -> list:
        return self.get_rules(tier).get("deprioritised_actions", [])

    def forbidden_advice(self, tier: str) -> list:
        return self.get_rules(tier).get("forbidden_advice", [])

    def max_changes(self, tier: str) -> int:
        return self.get_rules(tier).get("max_changes_per_episode", 3)

    def rationale(self, tier: str) -> str:
        return self.get_rules(tier).get("rationale", "")
