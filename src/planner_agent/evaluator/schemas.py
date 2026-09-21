"""Schemas for the Evaluator Agent.

Defines structured output formats for plan evaluation.
"""

from pydantic import BaseModel, Field

EVALUATION_CRITERIA = [
    "safety_compliance",
    "community_impact",
    "logistics_completeness",
    "financial_viability",
    "participant_experience",
    "intent_alignment",
    "distance_compliance",
]


class EvaluationFinding(BaseModel):
    """A specific finding from plan evaluation."""

    criterion: str = Field(
        description=(
            f"Which evaluation criterion triggered this finding. "
            f"Must be one of: {', '.join(EVALUATION_CRITERIA)}"
        ),
    )
    severity: str = Field(
        description="Severity of the finding: 'high', 'medium', or 'low'",
    )
    description: str = Field(
        description="Description of the finding and why it matters",
    )


class EvaluationResult(BaseModel):
    """Structured output from the Evaluator Agent."""

    passed: bool = Field(
        description="Whether the plan passes evaluation (overall_score >= 85)",
    )
    overall_score: float = Field(
        ge=0.0, le=100.0,
        description="Weighted average score across all criteria (0.0 to 100.0)",
    )
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-criterion scores: {criterion_name: score}",
    )
    findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="List of specific evaluation findings",
    )
    improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions to improve the plan score",
    )
    iteration_number: int = Field(
        default=1, ge=1,
        description="Which evaluation iteration this is",
    )
    summary: str = Field(
        default="",
        description="Brief natural-language summary of the evaluation",
    )
