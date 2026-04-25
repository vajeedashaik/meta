import json
from typing import List

from pydantic import BaseModel

from viral_script_engine.agents.llm_backend import LLMBackend

SYSTEM_PROMPT = """You are an expert social media content critic specialising in short-form video scripts for Reels and YouTube Shorts. Your job is to find specific, real problems in creator scripts — not vague feedback.

RULES:
1. Every claim must cite a specific part of the script (quote it or reference the timestamp range)
2. Every claim must be falsifiable — a human editor must be able to verify it by re-reading the script
3. Never say "the hook is weak" — say "the hook at 0:00-0:03 promises [X] but the script delivers [Y] at 0:22, by which time most viewers have already dropped off"
4. Focus on the 6 critique classes: hook_weakness, pacing_issue, cultural_mismatch, cta_buried, coherence_break, retention_risk
5. Produce between 3 and 6 claims per script. No more, no less.
6. For each claim, assign a timestamp range if the issue is locatable in the script. Use "N/A" only if it's a structural issue spanning the whole script.

OUTPUT FORMAT (respond ONLY with valid JSON, no markdown, no preamble):
{
  "claims": [
    {
      "claim_id": "C1",
      "critique_class": "hook_weakness",
      "claim_text": "...",
      "timestamp_range": "0:00-0:03",
      "evidence": "exact quote from script",
      "is_falsifiable": true,
      "severity": "high"
    }
  ],
  "overall_severity": "high"
}"""

USER_PROMPT_TEMPLATE = """SCRIPT TO CRITIQUE:
{script}

TARGET REGION: {region}
PLATFORM: {platform}
NICHE: {niche}

Produce your critique now."""

STRICT_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was not valid JSON. "
    "Respond ONLY with the raw JSON object. No markdown fences, no explanation, no preamble."
)


class CriticParseError(Exception):
    pass


class CritiqueClaim(BaseModel):
    claim_id: str
    critique_class: str
    claim_text: str
    timestamp_range: str
    evidence: str
    is_falsifiable: bool
    severity: str


class CritiqueOutput(BaseModel):
    claims: List[CritiqueClaim]
    overall_severity: str
    raw_response: str


class CriticAgent:
    def __init__(self, backend: str = "anthropic", model_name: str = "claude-haiku-4-5-20251001"):
        self.llm = LLMBackend(backend=backend, model_name=model_name)

    @staticmethod
    def _extract_json(text: str) -> dict:
        import re
        text = text.strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
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
                                return json.loads(text[start : i + 1])
                            except json.JSONDecodeError:
                                break
        raise ValueError(f"No valid JSON found in response: {text[:200]}")

    def _parse_response(self, raw: str, user_prompt: str) -> CritiqueOutput:
        try:
            data = self._extract_json(raw)
            data["raw_response"] = raw
            return CritiqueOutput(**data)
        except Exception:
            strict_prompt = user_prompt + STRICT_RETRY_SUFFIX
            raw2 = self.llm.generate(SYSTEM_PROMPT, strict_prompt, max_tokens=2048)
            try:
                data = self._extract_json(raw2)
                data["raw_response"] = raw2
                return CritiqueOutput(**data)
            except Exception as e:
                raise CriticParseError(f"Failed to parse critique after 2 attempts: {e}")

    def critique(self, script: str, region: str, platform: str, niche: str) -> CritiqueOutput:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            script=script, region=region, platform=platform, niche=niche
        )
        raw = self.llm.generate(SYSTEM_PROMPT, user_prompt, max_tokens=2048)
        return self._parse_response(raw, user_prompt)
