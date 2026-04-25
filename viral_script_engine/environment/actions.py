from enum import Enum
from pydantic import BaseModel


class ActionType(str, Enum):
    HOOK_REWRITE = "hook_rewrite"
    SECTION_REORDER = "section_reorder"
    CULTURAL_REF_SUB = "cultural_ref_sub"
    CTA_PLACEMENT = "cta_placement"


class ArbitratorAction(BaseModel):
    action_type: ActionType
    target_section: str       # "hook" | "body" | "cta" | "full"
    instruction: str          # natural language instruction to the Rewriter
    critique_claim_id: str    # which CritiqueClaim this responds to, e.g. "C2"
    reasoning: str            # why this action was chosen
