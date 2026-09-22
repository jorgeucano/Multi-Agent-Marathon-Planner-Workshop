"""Schemas for the Simulation Controller Agent."""

from pydantic import BaseModel, Field


class SimulationApproval(BaseModel):
    """Structured output from the Simulation Controller Agent."""

    approved: bool = Field(description="Whether the plan is approved for simulation")
    overall_readiness: float = Field(ge=0.0, le=1.0, description="Readiness score (0-1)")
    route_feasibility: str = Field(description="'feasible', 'marginal', or 'infeasible'")
    logistics_readiness: str = Field(description="'ready', 'partial', or 'not_ready'")
    safety_clearance: str = Field(description="'cleared', 'conditional', or 'blocked'")
    runner_readiness: str = Field(
        default="unknown", description="Runner cohort verdict: ready, conditional, or not_ready"
    )
    runner_findings: list[str] = Field(
        default_factory=list, description="Runner-centered pace, hydration, fatigue, or congestion findings"
    )
    blockers: list[str] = Field(default_factory=list, description="Blocking issues")
    recommendations: list[str] = Field(default_factory=list, description="Non-blocking suggestions")
    summary: str = Field(default="", description="Summary of the decision")
