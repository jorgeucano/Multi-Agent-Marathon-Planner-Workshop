"""Configuration for the Runner Cohort Agent."""

import os

AGENT_NAME = "runner_agent"
AGENT_DESCRIPTION = (
    "Runner Cohort Agent. Simulates how representative groups of runners "
    "experience pace, hydration, fatigue, medical risk, and the finish rate."
)
MODEL = os.getenv("RUNNER_MODEL", os.getenv("SIMULATOR_MODEL", "gemini-3.1-flash-lite"))
