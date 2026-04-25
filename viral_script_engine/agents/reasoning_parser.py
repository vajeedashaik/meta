import json
import re
from typing import Tuple

from pydantic import BaseModel

from viral_script_engine.environment.actions import ArbitratorAction


class ArbitratorParseError(Exception):
    pass


class ReasoningChain(BaseModel):
    priority_assessment: str
    conflict_check_answer: str        # "yes" or "no" (empty string = missing)
    conflict_check_reason: str
    defender_consideration_answer: str   # "yes" or "no" (empty string = missing)
    defender_consideration_reason: str
    action: ArbitratorAction


class ReasoningParser:
    """
    Parses the extended Arbitrator JSON output into a ReasoningChain.
    Falls back gracefully if reasoning fields are missing (backward compatible
    with the untrained baseline model which does not produce reasoning fields).
    """

    _VALID_ACTIONS = {"hook_rewrite", "section_reorder", "cultural_ref_sub", "cta_placement"}

    @staticmethod
    def _extract_json(text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Walk to find balanced braces
        start = text.find("{")
        if start != -1:
            depth, in_str, esc = 0, False, False
            for i, c in enumerate(text[start:], start):
                if esc:
                    esc = False
                    continue
                if c == "\\" and in_str:
                    esc = True
                    continue
                if c == '"':
                    in_str = not in_str
                elif not in_str:
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start: i + 1])
                            except json.JSONDecodeError:
                                break
        raise ArbitratorParseError(f"No valid JSON found in: {text[:200]}")

    @staticmethod
    def _parse_yes_no_field(field_value: str) -> Tuple[str, str]:
        """Extract yes/no answer and optional reason from a field string."""
        if not field_value:
            return "", ""
        lower = field_value.lower().strip()
        if lower.startswith("yes"):
            answer = "yes"
            rest = field_value[3:].strip(" —-:,")
        elif lower.startswith("no"):
            answer = "no"
            rest = field_value[2:].strip(" —-:,")
        else:
            return "", field_value
        return answer, rest

    def parse(self, raw_output: str) -> ReasoningChain:
        data = self._extract_json(raw_output)

        # Action fields are required — raise if missing/invalid
        action_type = data.get("action_type")
        if not action_type or action_type not in self._VALID_ACTIONS:
            raise ArbitratorParseError(
                f"Missing or invalid action_type: {action_type!r}"
            )

        action = ArbitratorAction(
            action_type=data["action_type"],
            target_section=data.get("target_section", "hook"),
            instruction=data.get("instruction", ""),
            critique_claim_id=data.get("critique_claim_id", "C1"),
            reasoning=data.get("reasoning", ""),
        )

        # Reasoning fields are optional — fall back to empty strings if absent
        priority_assessment = data.get("priority_assessment", "")

        conflict_raw = data.get("conflict_check", "")
        conflict_answer, conflict_reason = self._parse_yes_no_field(conflict_raw)

        defender_raw = data.get("defender_consideration", "")
        defender_answer, defender_reason = self._parse_yes_no_field(defender_raw)

        return ReasoningChain(
            priority_assessment=priority_assessment,
            conflict_check_answer=conflict_answer,
            conflict_check_reason=conflict_reason,
            defender_consideration_answer=defender_answer,
            defender_consideration_reason=defender_reason,
            action=action,
        )
