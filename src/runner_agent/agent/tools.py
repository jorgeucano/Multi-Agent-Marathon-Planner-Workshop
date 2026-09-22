"""Deterministic tools for the Runner Cohort Agent."""

from __future__ import annotations

import re
from typing import Any


COHORTS = (
    ("elite", 0.01, 3.15, 0.004),
    ("competitive", 0.14, 4.35, 0.009),
    ("main_pack", 0.60, 5.75, 0.021),
    ("back_of_pack", 0.25, 7.25, 0.047),
)


def _participants_from_plan(plan_text: str, fallback: int) -> int:
    patterns = (
        r"([\d,.]+)\s*(?:runners?|participants?|corredores?|participantes?)",
        r"(?:field|cupo)\s+(?:of|de)\s+([\d,.]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, plan_text, re.IGNORECASE)
        if match:
            value = re.sub(r"[^0-9]", "", match.group(1))
            if value:
                return max(1, int(value))
    return max(1, int(fallback))


def simulate_runner_cohorts(
    plan_text: str,
    participants: int = 30_000,
    temperature_c: float = 18.0,
) -> dict[str, Any]:
    """Simulate representative runner cohorts from a marathon plan.

    The output is deterministic and intentionally lightweight. It gives a real
    Runner Agent stable facts to interpret without launching thousands of LLM
    calls during a workshop.
    """
    if not plan_text or not plan_text.strip():
        raise ValueError("plan_text must not be empty")

    participants = _participants_from_plan(plan_text, participants)
    lower = plan_text.lower()
    has_water = any(term in lower for term in ("water station", "hydration", "puesto de agua"))
    has_medical = any(term in lower for term in ("medical tent", "medical station", "first aid", "ambulance", "médic"))
    has_waves = any(term in lower for term in ("wave start", "starting waves", "corrales", "largadas por ola"))
    has_timing = any(term in lower for term in ("chip timing", "timing", "tracking", "cronometraje"))

    heat_penalty = max(0.0, float(temperature_c) - 20.0) * 0.0025
    infrastructure_penalty = (0 if has_water else 0.035) + (0 if has_medical else 0.018)
    congestion_penalty = 0 if has_waves else 0.006

    cohorts = []
    assigned = 0
    for index, (name, share, pace, base_dropout) in enumerate(COHORTS):
        count = participants - assigned if index == len(COHORTS) - 1 else round(participants * share)
        assigned += count
        finish_minutes = round(pace * 42.195)
        dropout_rate = min(0.35, base_dropout + heat_penalty + infrastructure_penalty + congestion_penalty)
        finishers = round(count * (1 - dropout_rate))
        risk = "high" if dropout_rate >= 0.07 else "medium" if dropout_rate >= 0.03 else "low"
        hydration_interval_km = 2.5 if pace >= 5 else 5.0
        cohorts.append({
            "cohort": name,
            "share": share,
            "runners": count,
            "pace_min_per_km": pace,
            "projected_finish_minutes": finish_minutes,
            "projected_finishers": finishers,
            "dropout_rate": round(dropout_rate, 3),
            "risk": risk,
            "hydration_interval_km": hydration_interval_km,
        })

    findings = []
    if not has_water:
        findings.append("No hydration plan detected; every cohort receives a major dropout penalty.")
    if not has_medical:
        findings.append("No medical coverage detected; late-race runner risk is elevated.")
    if not has_waves:
        findings.append("No wave start detected; the main pack receives a congestion penalty.")
    if not has_timing:
        findings.append("No timing or tracking system detected for runner accountability.")
    if temperature_c > 24:
        findings.append(f"Heat risk at {temperature_c:.1f} C increases projected dropouts.")
    if not findings:
        findings.append("Core runner services are present; no deterministic blocker detected.")

    projected_finishers = sum(c["projected_finishers"] for c in cohorts)
    readiness = "ready" if has_water and has_medical and has_timing else "conditional"
    if not has_water and not has_medical:
        readiness = "not_ready"

    return {
        "participants": participants,
        "temperature_c": float(temperature_c),
        "cohorts": cohorts,
        "projected_finishers": projected_finishers,
        "projected_dropouts": participants - projected_finishers,
        "runner_readiness": readiness,
        "findings": findings,
        "method": "deterministic_cohort_simulation",
    }
