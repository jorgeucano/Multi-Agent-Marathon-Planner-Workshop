"""Tools for the Simulation Controller Agent."""

import re
from typing import Any


async def check_plan_readiness(plan_text: str) -> dict[str, Any]:
    """Check a marathon plan for simulation readiness.

    Performs deterministic checks on the plan text to identify
    missing elements and assess completeness.
    """
    plan_lower = plan_text.lower()

    checklist = {
        "distance_specified": bool(
            re.search(r'(\d+(?:\.\d+)?)\s*(?:miles?|mi|kilometers?|km)\b', plan_lower)
        ),
        "water_stations": "water station" in plan_lower,
        "medical_tents": any(kw in plan_lower for kw in ["medical tent", "first aid", "medical station"]),
        "timing_system": any(kw in plan_lower for kw in ["timing", "chip", "tracking"]),
        "start_finish": any(kw in plan_lower for kw in ["start line", "finish line", "start/finish", "starting area"]),
        "emergency_access": any(kw in plan_lower for kw in ["emergency", "ambulance", "evacuation"]),
        "budget_included": any(kw in plan_lower for kw in ["budget", "cost", "revenue", "expense"]),
        "timeline_included": any(kw in plan_lower for kw in ["schedule", "timeline", "race day", "setup"]),
    }

    passed = sum(checklist.values())
    total = len(checklist)

    return {
        "checklist": checklist,
        "missing_elements": [k for k, v in checklist.items() if not v],
        "readiness_score": round(passed / total, 2),
        "passed_checks": passed,
        "total_checks": total,
    }


def get_tools() -> list:
    return [check_plan_readiness]
