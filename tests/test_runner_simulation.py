"""Offline tests for the Runner Cohort Agent's deterministic tool."""

import importlib.util
import pathlib


TOOLS = (
    pathlib.Path(__file__).resolve().parent.parent
    / "src/runner_agent/agent/tools.py"
)
spec = importlib.util.spec_from_file_location("runner_tools", TOOLS)
runner_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner_tools)
simulate_runner_cohorts = runner_tools.simulate_runner_cohorts


COMPLETE_PLAN = """
Buenos Aires marathon for 30,000 runners over 26.2 miles (42.195 km).
Wave starts, chip timing and tracking, hydration every 2.5 km, medical tents,
ambulances and emergency access throughout the course.
"""


def test_complete_plan_produces_four_cohorts_and_all_runners():
    result = simulate_runner_cohorts(COMPLETE_PLAN)
    assert len(result["cohorts"]) == 4
    assert sum(c["runners"] for c in result["cohorts"]) == 30_000
    assert result["runner_readiness"] == "ready"
    assert result["method"] == "deterministic_cohort_simulation"


def test_missing_runner_services_raise_risk_and_lower_readiness():
    complete = simulate_runner_cohorts(COMPLETE_PLAN)
    thin = simulate_runner_cohorts("A marathon for 30,000 runners.")
    assert thin["runner_readiness"] == "not_ready"
    assert thin["projected_dropouts"] > complete["projected_dropouts"]
    assert any("hydration" in finding.lower() for finding in thin["findings"])


def test_participant_count_is_read_from_plan():
    result = simulate_runner_cohorts("Race with 12,500 participants, hydration and medical tents.")
    assert result["participants"] == 12_500
    assert sum(c["runners"] for c in result["cohorts"]) == 12_500
