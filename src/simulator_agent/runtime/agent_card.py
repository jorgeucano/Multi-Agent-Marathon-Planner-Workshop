"""A2A Agent Card for Simulation Controller Agent."""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

try:
    from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card
except ImportError:  # pragma: no cover
    # See docs/GOTCHAS.md #5 - same preview-path fallback as the planner card.
    def create_agent_card(agent_name, description, skills, **kwargs):
        return AgentCard(
            name=agent_name,
            description=description,
            url="http://127.0.0.1:8089",
            version="0.1.0",
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            capabilities=AgentCapabilities(streaming=False),
            skills=skills,
        )


def create_simulation_controller_card() -> AgentCard:
    skill = AgentSkill(
        id="review_marathon_plan",
        name="Review Marathon Plan",
        description="Review a marathon plan and simulate representative runner cohorts.",
        tags=["simulation", "review", "approval", "marathon", "runners"],
    )
    return create_agent_card(
        agent_name="simulator_agent",
        description=(
            "Simulation Controller Agent - Reviews plans for readiness and delegates "
            "runner experience analysis to a local Runner Cohort Agent."
        ),
        skills=[skill],
    )
