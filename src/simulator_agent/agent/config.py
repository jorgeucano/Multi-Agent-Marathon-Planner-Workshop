"""Configuration for the Simulation Controller Agent."""

import os
from .schemas import SimulationApproval

AGENT_NAME = "simulator_agent"
AGENT_DESCRIPTION = (
    "Simulation Controller Agent. Reviews marathon plans for simulation readiness, "
    "assessing route feasibility, logistics completeness, safety clearance, and "
    "runner cohort experience through its local Runner Agent."
)
# Rehearsed default. The codelab's gemini-3-flash-preview also works, but only in location=global.
MODEL = os.getenv("SIMULATOR_MODEL", "gemini-3.1-flash-lite")
OUTPUT_SCHEMA = SimulationApproval
