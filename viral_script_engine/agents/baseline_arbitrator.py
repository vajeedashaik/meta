import json

from viral_script_engine.agents.llm_backend import LLMBackend

SYSTEM_PROMPT = """You are helping improve a short-form video script.
You have observed a debate between a Critic and a Defender about the script.
Choose ONE action to take to improve the script.

Available actions: hook_rewrite, section_reorder, cultural_ref_sub, cta_placement

Respond ONLY with valid JSON:
{
  "action_type": "hook_rewrite",
  "target_section": "hook",
  "instruction": "specific instruction for the rewriter",
  "critique_claim_id": "C1",
  "reasoning": "brief explanation"
}"""

STRICT_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was not valid JSON. "
    "Respond ONLY with the raw JSON object. No markdown fences, no explanation, no preamble."
)

_FALLBACK_ACTION = {
    "action_type": "hook_rewrite",
    "target_section": "hook",
    "instruction": "Rewrite the hook to be more engaging and direct.",
    "critique_claim_id": "C1",
    "reasoning": "Default fallback action.",
}


class BaselineArbitratorAgent:
    """
    Untrained Arbitrator for the pre-training baseline.
    Uses zero-shot instruction — no chain-of-thought, no few-shot examples.
    This ensures the comparison is fair: trained model learns through RL, not prompting.
    """

    def __init__(self, backend: str = "anthropic", model_name: str = "claude-haiku-4-5-20251001"):
        self.llm = LLMBackend(backend=backend, model_name=model_name)

    def _build_user_prompt(self, observation: dict) -> str:
        script = observation.get("current_script", "")
        debate = observation.get("debate_history", [])
        last_claims = []
        last_defense = None
        if debate:
            last_round = debate[-1]
            last_claims = last_round.get("critic_claims", [])
            last_defense = last_round.get("defender_response")

        claims_text = ""
        for c in last_claims:
            claims_text += f"- [{c.get('claim_id','?')}] {c.get('claim_text','')} (severity: {c.get('severity','')})\n"

        defense_text = ""
        if last_defense:
            defense_text = (
                f"Defender preserved: {last_defense.get('core_strength_quote','')}\n"
                f"Flagged claims: {last_defense.get('flagged_critic_claims', [])}\n"
            )

        return (
            f"SCRIPT:\n{script}\n\n"
            f"CRITIC CLAIMS:\n{claims_text or 'None'}\n"
            f"DEFENDER:\n{defense_text or 'None'}\n\n"
            "Choose one action to improve the script."
        )

    def act(self, observation: dict) -> dict:
        user_prompt = self._build_user_prompt(observation)
        raw = self.llm.generate(SYSTEM_PROMPT, user_prompt, max_tokens=512)
        try:
            return json.loads(raw)
        except Exception:
            strict_prompt = user_prompt + STRICT_RETRY_SUFFIX
            raw2 = self.llm.generate(SYSTEM_PROMPT, strict_prompt, max_tokens=512)
            try:
                return json.loads(raw2)
            except Exception:
                return _FALLBACK_ACTION.copy()
