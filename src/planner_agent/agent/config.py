"""Configuration for the Marathon Planner Agent."""

import os

AGENT_NAME = "planner_agent"
AGENT_DESCRIPTION = (
    "Marathon Planner Agent - Lead Architect. "
    "Designs comprehensive city marathon plans with built-in expertise in route design, "
    "traffic management, community impact, and economics. Evaluates plans via the "
    "Evaluator Agent (A2A) and submits for approval to the Simulation Controller (A2A)."
)
MODEL = os.getenv("PLANNER_MODEL", "gemini-3-flash-preview")
# Phase 1: No structured output - agent returns free-form text
OUTPUT_SCHEMA = None
