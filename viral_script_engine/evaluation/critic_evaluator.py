from typing import List, Tuple

from pydantic import BaseModel

from viral_script_engine.agents.critic import CritiqueOutput


class EvaluationResult(BaseModel):
    script_id: str = ""
    claim_count: int
    specificity_score: float
    falsifiability_score: float
    timestamp_coverage: float
    critique_class_diversity: float
    passes_gate: bool


class BatchEvaluationResult(BaseModel):
    pass_count: int
    pass_rate: float
    passes_overall_gate: bool
    per_script_results: List[EvaluationResult]
    failing_scripts: List[str]


class CriticEvaluator:
    def evaluate(self, output: CritiqueOutput, script_text: str, script_id: str = "") -> EvaluationResult:
        claims = output.claims
        claim_count = len(claims)

        if claim_count == 0:
            return EvaluationResult(
                script_id=script_id,
                claim_count=0,
                specificity_score=0.0,
                falsifiability_score=0.0,
                timestamp_coverage=0.0,
                critique_class_diversity=0.0,
                passes_gate=False,
            )

        specificity_score = sum(
            1 for c in claims if c.evidence and c.evidence.strip() in script_text
        ) / claim_count

        falsifiability_score = sum(1 for c in claims if c.is_falsifiable) / claim_count

        timestamp_coverage = sum(
            1 for c in claims if c.timestamp_range and c.timestamp_range.strip() != "N/A"
        ) / claim_count

        unique_classes = {c.critique_class for c in claims}
        critique_class_diversity = len(unique_classes) / 6

        passes_gate = (
            claim_count >= 3
            and specificity_score >= 0.6
            and falsifiability_score >= 0.7
        )

        return EvaluationResult(
            script_id=script_id,
            claim_count=claim_count,
            specificity_score=round(specificity_score, 3),
            falsifiability_score=round(falsifiability_score, 3),
            timestamp_coverage=round(timestamp_coverage, 3),
            critique_class_diversity=round(critique_class_diversity, 3),
            passes_gate=passes_gate,
        )

    def batch_evaluate(
        self,
        results: List[Tuple[CritiqueOutput, str]],
        script_ids: List[str] = None,
    ) -> BatchEvaluationResult:
        if script_ids is None:
            script_ids = ["" for _ in results]

        per_script = [
            self.evaluate(output, script_text, sid)
            for (output, script_text), sid in zip(results, script_ids)
        ]

        pass_count = sum(1 for r in per_script if r.passes_gate)
        pass_rate = pass_count / len(per_script) if per_script else 0.0
        failing_scripts = [r.script_id for r in per_script if not r.passes_gate]

        return BatchEvaluationResult(
            pass_count=pass_count,
            pass_rate=round(pass_rate, 3),
            passes_overall_gate=pass_rate >= 0.8,
            per_script_results=per_script,
            failing_scripts=failing_scripts,
        )
