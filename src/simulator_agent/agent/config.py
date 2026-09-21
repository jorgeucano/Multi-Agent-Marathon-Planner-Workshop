"""Configuration for the Simulation Controller Agent."""

import os
from .schemas import SimulationApproval

AGENT_NAME = "simulator_agent"
AGENT_DESCRIPTION = (
    "Simulation Controller Agent. Reviews marathon plans for simulation readiness, "
    "assessing route feasibility, logistics completeness, and safety clearance."
)
MODEL = os.getenv("SIMULATOR_MODEL", "gemini-3-flash-preview")
OUTPUT_SCHEMA = SimulationApproval
