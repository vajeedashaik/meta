import difflib
from pydantic import BaseModel

from viral_script_engine.agents.llm_backend import LLMBackend
from viral_script_engine.environment.actions import ArbitratorAction

_SYSTEM_PROMPT = (
    "You are a professional script editor for short-form social media video. "
    "Apply ONLY the instruction given. Do not make any other changes. "
    "Do not add new ideas. Do not change the creator's voice or regional language patterns. "
    "Return ONLY the rewritten script text, no commentary."
)


class RewriteResult(BaseModel):
    rewritten_script: str
    diff: str
    word_count_delta: int


class RewriterAgent:
    def __init__(self, backend: str = "anthropic", model_name: str = "claude-haiku-4-5-20251001"):
        self.llm = LLMBackend(backend=backend, model_name=model_name)

    def rewrite(self, current_script: str, action: ArbitratorAction) -> RewriteResult:
        user_prompt = (
            f"CURRENT SCRIPT:\n{current_script}\n\n"
            f"ACTION TYPE: {action.action_type.value}\n"
            f"TARGET SECTION: {action.target_section}\n"
            f"INSTRUCTION: {action.instruction}\n\n"
            "Apply the instruction and return ONLY the rewritten script."
        )
        rewritten = self.llm.generate(_SYSTEM_PROMPT, user_prompt, max_tokens=2048)
        diff_lines = list(difflib.unified_diff(
            current_script.splitlines(keepends=True),
            rewritten.splitlines(keepends=True),
            fromfile="original",
            tofile="rewritten",
        ))
        return RewriteResult(
            rewritten_script=rewritten,
            diff="".join(diff_lines),
            word_count_delta=len(rewritten.split()) - len(current_script.split()),
        )
