import json
from typing import List

from pydantic import BaseModel

from viral_script_engine.agents.llm_backend import LLMBackend
from viral_script_engine.agents.critic import CritiqueClaim

SYSTEM_PROMPT = """You are a script defender for short-form video content. Your job is NOT to say the script is perfect.
Your job is to identify what is genuinely working — and protect it from being edited away.

Specifically:
1. Find the single most powerful element of the script. Quote it exactly.
2. Explain why a viewer would respond positively to this element.
3. Review the Critic's claims. Flag any that would destroy the script's core strength or strip its regional authenticity if acted on.
4. List any phrases, idioms, or references that are intentionally regional — these must not be "corrected" away.

OUTPUT (JSON only, no preamble):
{
  "core_strength": "one sentence describing the strongest element",
  "core_strength_quote": "exact verbatim quote from the script",
  "defense_argument": "why this element should be preserved",
  "flagged_critic_claims": ["C2", "C3"],
  "regional_voice_elements": ["specific phrase 1", "specific phrase 2"]
}"""

STRICT_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was not valid JSON. "
    "Respond ONLY with the raw JSON object. No markdown fences, no explanation, no preamble."
)


class DefenderParseError(Exception):
    pass


class DefenderOutput(BaseModel):
    core_strength: str
    core_strength_quote: str
    defense_argument: str
    flagged_critic_claims: List[str]
    regional_voice_elements: List[str]


class DefenderAgent:
    def __init__(self, backend: str = "groq", model_name: str = "llama-3.3-70b-versatile"):
        self.llm = LLMBackend(backend=backend, model_name=model_name)

    def _build_user_prompt(
        self,
        script: str,
        critic_claims: List[CritiqueClaim],
        region: str,
        platform: str,
    ) -> str:
        claims_lines = []
        for i, claim in enumerate(critic_claims, start=1):
            claims_lines.append(
                f"{i}. [{claim.claim_id}] ({claim.critique_class}) {claim.claim_text} | Evidence: {claim.evidence}"
            )
        claims_block = "\n".join(claims_lines) if claims_lines else "No critic claims provided."

        return (
            f"SCRIPT:\n{script}\n\n"
            f"CRITIC CLAIMS:\n{claims_block}\n\n"
            f"REGION: {region}\n"
            f"PLATFORM: {platform}\n\n"
            "Defend the script now."
        )

    def _parse_response(self, raw: str, user_prompt: str) -> DefenderOutput:
        try:
            data = json.loads(raw)
            return DefenderOutput(**data)
        except Exception:
            strict_prompt = user_prompt + STRICT_RETRY_SUFFIX
            raw2 = self.llm.generate(SYSTEM_PROMPT, strict_prompt, max_tokens=1024)
            try:
                data = json.loads(raw2)
                return DefenderOutput(**data)
            except Exception as e:
                raise DefenderParseError(f"Failed to parse defender output after 2 attempts: {e}")

    def defend(
        self,
        script: str,
        critic_claims: List[CritiqueClaim],
        region: str,
        platform: str,
    ) -> DefenderOutput:
        user_prompt = self._build_user_prompt(script, critic_claims, region, platform)
        raw = self.llm.generate(SYSTEM_PROMPT, user_prompt, max_tokens=1024)
        return self._parse_response(raw, user_prompt)
