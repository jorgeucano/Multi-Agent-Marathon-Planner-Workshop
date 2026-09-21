"""Tests for the Evaluator's heuristic fallback and weighting.

Skipped automatically if the Google deps are not installed yet.
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

pytest.importorskip("vertexai")
pytest.importorskip("pandas")

from src.planner_agent.evaluator.config import CRITERION_WEIGHTS  # noqa: E402
from src.planner_agent.evaluator.tools import (  # noqa: E402
    _build_result,
    _check_distance_compliance_logic,
    _heuristic_eval,
)


def test_weights_sum_to_one():
    assert sum(CRITERION_WEIGHTS.values()) == pytest.approx(1.0)


def test_distance_check_accepts_the_real_marathon():
    assert _check_distance_compliance_logic("26.2 miles of scenic course")["score"] == 100.0


def test_distance_check_rejects_a_wrong_course():
    assert _check_distance_compliance_logic("a 24 mile course")["score"] == 1.0


def test_heuristic_rewards_a_detailed_plan():
    thin, _ = _heuristic_eval("intent", "a marathon")
    rich, _ = _heuristic_eval(
        "intent",
        "26.2 miles with hydration, chip timing, marshals, budget, revenue, "
        "sponsor, scenic landmarks, medals, post-race recovery, cheer zone, "
        "community engagement and emergency vehicle access.",
    )
    assert rich["logistics_completeness"] > thin["logistics_completeness"]
    assert rich["financial_viability"] > thin["financial_viability"]


def test_high_severity_finding_blocks_a_pass():
    scores = {c: 95.0 for c in CRITERION_WEIGHTS}
    scores["safety_compliance"] = 30.0  # below the high-severity threshold
    result = _build_result(scores, {}, "heuristic")
    assert any(f["severity"] == "high" for f in result["findings"])
    assert result["passed"] is False, "a high-severity finding must block the pass"
