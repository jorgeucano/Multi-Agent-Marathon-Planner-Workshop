"""Tests for the Simulation Controller's deterministic checklist."""

import asyncio
import importlib.util
import pathlib

# Loaded by path so the offline suite needs no ADK install and no credentials.
_TOOLS = (
    pathlib.Path(__file__).resolve().parent.parent
    / "src/simulator_agent/agent/tools.py"
)
_spec = importlib.util.spec_from_file_location("sim_tools", _TOOLS)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
check_plan_readiness = _mod.check_plan_readiness

COMPLETE_PLAN = """
Las Vegas Marathon, 26.2 miles starting at the Festival Grounds.
Water station every 2.5 km, medical tent every 5 km, chip timing at the
start line and finish line, emergency vehicle crossings every 2 miles,
budget of USD 2.7M, race day schedule from 04:00 setup to 16:00 teardown.
"""

EMPTY_PLAN = "We will run somewhere in the city. It will be fun."


def test_complete_plan_passes_every_check():
    result = asyncio.run(check_plan_readiness(COMPLETE_PLAN))
    assert result["readiness_score"] == 1.0
    assert result["missing_elements"] == []


def test_empty_plan_reports_what_is_missing():
    result = asyncio.run(check_plan_readiness(EMPTY_PLAN))
    assert result["readiness_score"] < 0.3
    assert "water_stations" in result["missing_elements"]
    assert "timing_system" in result["missing_elements"]


def test_distance_is_detected_in_both_units():
    for text in ("the course is 26.2 miles", "el recorrido son 42.195 km"):
        result = asyncio.run(check_plan_readiness(text))
        assert result["checklist"]["distance_specified"], text
