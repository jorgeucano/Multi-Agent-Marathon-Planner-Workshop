"""Configuration for the Evaluator Agent.

DEVIATION FROM THE CODELAB (intentional, see docs/GOTCHAS.md #1):
In the codelab, MODEL / CRITERION_WEIGHTS / SEVERITY_THRESHOLDS live in
agent.py, and tools.py does `from .agent import ...` while agent.py does
`from .tools import evaluate_plan`. That is a circular import: it only works
if `.agent` is imported first, and blows up on `import ...evaluator.tools`.
The codelab hides the failure behind a bare `except Exception` in
__init__.py, so the agent silently stops existing.

Pulling the constants into this module breaks the cycle. Nothing else changes.
"""

import os

AGENT_NAME = "evaluator_agent"
AGENT_DESCRIPTION = (
    "Evaluates marathon plans across multiple quality criteria using Vertex AI "
    "Evaluation with custom metrics. Acts as LLM-as-Judge to score plans and "
    "provide actionable feedback for iterative improvement."
)

# Model - use gemini-3.1-pro-preview for evaluation accuracy
# Rehearsed default. The codelab's gemini-3.1-pro-preview also works, but only in location=global.
MODEL = os.getenv("EVALUATOR_MODEL", "gemini-3.1-flash-lite")

# Criterion weights must sum to 1.0
CRITERION_WEIGHTS = {
    "safety_compliance": 0.20,
    "community_impact": 0.15,
    "logistics_completeness": 0.20,
    "financial_viability": 0.15,
    "participant_experience": 0.15,
    "intent_alignment": 0.10,
    "distance_compliance": 0.05,
}

SEVERITY_THRESHOLDS = {"high": 40.0, "medium": 60.0, "low": 80.0}
