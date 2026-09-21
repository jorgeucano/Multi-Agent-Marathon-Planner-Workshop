"""Tools for the Evaluator Agent.

Provides tools for evaluating marathon plans using Vertex AI Evaluation
with custom metrics. Uses a hybrid approach: LLM-based evaluation with
custom rubrics, plus deterministic checks, with heuristic fallback.
"""

import json
import logging
import os
import re
from typing import Any

import pandas as pd
import vertexai
from google.genai import types as genai_types
from vertexai import types

from .config import CRITERION_WEIGHTS, MODEL, SEVERITY_THRESHOLDS

logger = logging.getLogger(__name__)


def _get_model_resource() -> str:
    """Get the full resource path for the Vertex AI evaluation model."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    return (
        f"projects/{project_id}/locations/{location}/publishers/google/models/{MODEL}"
        if project_id else MODEL
    )


# DEVIATION FROM THE CODELAB (docs/GOTCHAS.md #18). The prompt that
# MetricPromptBuilder generates asks the judge for prose ("Step 1: assess...,
# Step 2: score..."), but the Vertex AI Evaluation service parses the judge's
# reply as JSON. Without this system instruction EVERY LLM metric fails with
# `400 Error parsing JSON` - with every judge model, including the codelab's
# gemini-3.1-pro-preview - and the codelab then silently scores it 50.
JUDGE_SYSTEM_INSTRUCTION = (
    "You are a strict evaluator. Follow the evaluation steps in the prompt, then "
    "output ONLY a single JSON object and nothing else - no markdown, no headings, "
    'no prose outside the JSON: {"score": <integer from the rating scale>, '
    '"explanation": "<your assessment of each criterion and the rationale for the score>"}'
)

# ============================================================================
# CUSTOM METRICS - each uses MetricPromptBuilder for structured rubrics
# ============================================================================

def _create_safety_compliance_metric() -> types.LLMMetric:
    """Evaluate emergency corridor access and crowd safety."""
    builder = types.MetricPromptBuilder(
        metric_definition=(
            "Evaluate whether the proposed marathon route maintains emergency "
            "vehicle access and crowd safety. Check for blocked hospitals, fire stations, "
            "and major emergency corridors."
        ),
        criteria={
            "Emergency corridor access": (
                "The route does not permanently block access to hospitals, "
                "fire stations, or police stations without providing clear detour routes."
            ),
            "Evacuation routes": (
                "Major evacuation routes remain accessible or have documented alternatives."
            ),
            "Emergency vehicle passage": (
                "The plan includes provisions for emergency vehicle crossing "
                "at regular intervals along the route."
            ),
        },
        rating_scores={
            "1": "Dangerous - Major emergency corridors blocked with no detours",
            "25": "Unsafe - Several emergency access points compromised",
            "50": "Concerning - Some emergency access issues that need resolution",
            "75": "Mostly safe - Minor emergency access concerns, easy to fix",
            "100": "Fully safe - Emergency access maintained throughout",
        },
    )
    return types.LLMMetric(
        name="safety_compliance",
        prompt_template=str(builder),
        judge_model=_get_model_resource(),
        judge_model_system_instruction=JUDGE_SYSTEM_INSTRUCTION,
    )


def _create_community_impact_metric() -> types.LLMMetric:
    """Evaluate community disruption, inclusivity, and neighborhood equity."""
    builder = types.MetricPromptBuilder(
        metric_definition=(
            "Evaluate the marathon plan's impact on the local community. "
            "Check for noise disruption, residential access, business impact, "
            "inclusivity, and equitable neighborhood treatment."
        ),
        criteria={
            "Residential disruption": (
                "The plan minimizes disruption to residential areas, with "
                "reasonable timing and notification plans."
            ),
            "Business access": (
                "Local businesses along the route can still operate or have "
                "been accommodated with alternative access."
            ),
            "Neighborhood equity": (
                "The route and plan are accessible to diverse communities "
                "and do not disproportionately burden any demographic group."
            ),
            "Community engagement": (
                "The plan includes cheer zones, community events, or other "
                "ways to involve and benefit local residents."
            ),
        },
        rating_scores={
            "1": "Harmful - Major negative impact on community with no mitigation",
            "25": "Disruptive - Significant community issues that need resolution",
            "50": "Mixed - Some community concerns that need attention",
            "75": "Considerate - Minor community impacts with good mitigation",
            "100": "Excellent - Community benefits from the event",
        },
    )
    return types.LLMMetric(
        name="community_impact",
        prompt_template=str(builder),
        judge_model=_get_model_resource(),
        judge_model_system_instruction=JUDGE_SYSTEM_INSTRUCTION,
    )


def _create_logistics_completeness_metric() -> types.LLMMetric:
    """Evaluate logistics coverage: water stations, timing, marshals."""
    builder = types.MetricPromptBuilder(
        metric_definition=(
            "Evaluate whether the marathon plan's logistics are complete and "
            "adequate for the expected scale."
        ),
        criteria={
            "Water and nutrition": "Hydration and nutrition are considered for the expected participant count.",
            "Timing and tracking": "Timing systems (chip timing, mats) are specified.",
            "Course management": "Sufficient course marshals, signage, barriers, and traffic control are planned.",
            "Start/finish infrastructure": "Start/finish areas have adequate capacity for the participant count.",
        },
        rating_scores={
            "1": "Incomplete - Critical logistics missing",
            "25": "Sparse - Major logistics gaps",
            "50": "Partial - Some logistics covered but significant gaps remain",
            "75": "Mostly complete - Minor logistics details to finalize",
            "100": "Comprehensive - All logistics thoroughly planned",
        },
    )
    return types.LLMMetric(
        name="logistics_completeness",
        prompt_template=str(builder),
        judge_model=_get_model_resource(),
        judge_model_system_instruction=JUDGE_SYSTEM_INSTRUCTION,
    )


def _create_financial_viability_metric() -> types.LLMMetric:
    """Evaluate budget balance, revenue sources, and cost control."""
    builder = types.MetricPromptBuilder(
        metric_definition=(
            "Evaluate the financial viability of the marathon plan. "
            "Check budget balance, revenue sources, cost estimates, and sustainability."
        ),
        criteria={
            "Budget balance": "Revenue projections meet or exceed estimated costs.",
            "Cost estimates": "Cost estimates are realistic and cover major expense categories.",
            "Revenue diversity": "Revenue comes from multiple sources, not just registration fees.",
        },
        rating_scores={
            "1": "Unviable - Major financial gaps",
            "25": "Risky - Budget concerns that could threaten viability",
            "50": "Uncertain - Financial plan needs more detail",
            "75": "Viable - Sound financial plan with minor gaps",
            "100": "Strong - Well-balanced budget with diverse revenue streams",
        },
    )
    return types.LLMMetric(
        name="financial_viability",
        prompt_template=str(builder),
        judge_model=_get_model_resource(),
        judge_model_system_instruction=JUDGE_SYSTEM_INSTRUCTION,
    )


def _create_participant_experience_metric() -> types.LLMMetric:
    """Evaluate route quality, scenic value, and runner amenities."""
    builder = types.MetricPromptBuilder(
        metric_definition=(
            "Evaluate the participant experience of a proposed marathon plan."
        ),
        criteria={
            "Route Quality": "The route surface is suitable and elevation profile appropriate.",
            "Scenic Value": "The route passes through interesting or landmark areas.",
            "Runner Amenities": "Post-race amenities (food, medals, recovery area) are planned.",
        },
        rating_scores={
            "1": "Poor experience - Boring route, no amenities",
            "50": "Average - Adequate but unremarkable",
            "100": "Excellent - Outstanding experience that runners will remember",
        },
    )
    return types.LLMMetric(
        name="participant_experience",
        prompt_template=str(builder),
        judge_model=_get_model_resource(),
        judge_model_system_instruction=JUDGE_SYSTEM_INSTRUCTION,
    )


def _create_intent_alignment_metric() -> types.LLMMetric:
    """Evaluate whether the plan matches the user's original request."""
    builder = types.MetricPromptBuilder(
        metric_definition=(
            "Evaluate whether a proposed marathon plan matches the user's original intent."
        ),
        criteria={
            "City Match": "The plan takes place in the requested city.",
            "Theme Match": "The plan matches the desired theme (scenic, fast, charity, etc.).",
            "Scale Match": "The plan's scale matches the user's vision.",
        },
        rating_scores={
            "1": "Completely misaligned",
            "50": "Partially aligned - Key requirements missed",
            "100": "Perfectly aligned - All requirements addressed",
        },
    )
    return types.LLMMetric(
        name="intent_alignment",
        prompt_template=str(builder),
        judge_model=_get_model_resource(),
        judge_model_system_instruction=JUDGE_SYSTEM_INSTRUCTION,
    )


def _check_distance_compliance_logic(response_text: str) -> dict:
    """Deterministic check for 26.2 mile (42.195 km) marathon distance."""
    text_lower = response_text.lower()
    score = 100.0
    issues = []

    for distance_str in re.findall(r'(\d+(?:\.\d+)?)\s*(?:miles?|mi)\b', text_lower):
        distance = float(distance_str)
        if 20 <= distance <= 30:
            deviation = abs(distance - 26.2)
            if deviation > 0.5:
                score = 1.0
                issues.append(f"Route distance {distance} miles deviates from 26.2 mile standard")
            elif deviation > 0.1:
                score = 60.0
                issues.append(f"Route distance {distance} miles is close but not exactly 26.2 miles")

    for distance_str in re.findall(r'(\d+(?:\.\d+)?)\s*(?:kilometers?|km)\b', text_lower):
        distance = float(distance_str)
        if 35 <= distance <= 50 and abs(distance - 42.195) > 1.0:
            score = 1.0
            issues.append(f"Route distance {distance} km deviates from 42.195 km standard")

    return {"score": score, "explanation": "; ".join(issues) if issues else "No distance issues detected"}


def _create_distance_compliance_metric() -> types.Metric:
    """Deterministic check for marathon distance - no LLM needed."""
    def check_distance_compliance(instance: dict) -> dict:
        response_text = instance["response"]["parts"][0]["text"]
        return _check_distance_compliance_logic(response_text)
    return types.Metric(
        name="distance_compliance",
        custom_function=check_distance_compliance,
    )


# ============================================================================
# MAIN EVALUATION TOOL
# ============================================================================

async def evaluate_plan(evaluation_request: str) -> dict[str, Any]:
    """Evaluate a proposed marathon plan across quality criteria.

    Uses Vertex AI Evaluation with 7 custom metrics.
    Falls back to heuristic evaluation if API fails.

    Args:
        evaluation_request: JSON string with user_intent and proposed_plan

    Returns:
        dict with evaluation results
    """
    try:
        request_data = json.loads(evaluation_request)
    except json.JSONDecodeError as e:
        return {
            "passed": False, "scores": {}, "overall_score": 0.0,
            "findings": [{"criterion": "intent_alignment",
                          "description": f"Invalid JSON input: {e}", "severity": "high"}],
            "improvement_suggestions": ["Provide valid JSON with 'user_intent' and 'proposed_plan' fields."],
            "eval_method": "error",
        }

    user_intent_raw = request_data.get("user_intent", "Unknown intent")
    proposed_plan_raw = request_data.get("proposed_plan", "No plan provided")
    user_intent = json.dumps(user_intent_raw) if not isinstance(user_intent_raw, str) else user_intent_raw
    proposed_plan = json.dumps(proposed_plan_raw) if not isinstance(proposed_plan_raw, str) else proposed_plan_raw

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    # DEVIATION FROM THE CODELAB (docs/GOTCHAS.md #4): EVAL_MODE lets you force
    # the heuristic path on stage instead of waiting ~1-3 min for 7 LLM judges.
    eval_mode = os.environ.get("EVAL_MODE", "auto").lower()

    if project_id and eval_mode != "heuristic":
        try:
            scores, details = await _run_custom_eval(
                project_id=project_id, location=location,
                user_intent=user_intent, proposed_plan=proposed_plan,
            )
            return _build_result(scores, details, eval_method="vertex_ai_eval")
        except Exception as e:
            logger.warning(f"Vertex AI Eval failed, using heuristics: {e}")

    scores, details = _heuristic_eval(user_intent, proposed_plan)
    return _build_result(scores, details, eval_method="heuristic")


async def _run_custom_eval(
    project_id: str, location: str,
    user_intent: str, proposed_plan: str,
) -> tuple[dict[str, float], dict[str, str]]:
    """Run Vertex AI Evaluation with custom metrics."""
    vertexai.init(project=project_id, location=location)
    client = vertexai.Client(
        project=project_id, location=location,
        http_options=genai_types.HttpOptions(api_version="v1beta1"),
    )
    df = pd.DataFrame({"prompt": [user_intent], "response": [proposed_plan]})
    metrics = [
        _create_safety_compliance_metric(),
        _create_community_impact_metric(),
        _create_logistics_completeness_metric(),
        _create_financial_viability_metric(),
        _create_participant_experience_metric(),
        _create_intent_alignment_metric(),
        _create_distance_compliance_metric(),
    ]
    result = client.evals.evaluate(dataset=df, metrics=metrics)

    scores, details, failed = {}, {}, []
    for case in result.eval_case_results:
        for cand in case.response_candidate_results:
            for metric_name, metric_result in cand.metric_results.items():
                score = getattr(metric_result, "score", None)
                if score is None:
                    # DEVIATION FROM THE CODELAB (docs/GOTCHAS.md #17): the codelab
                    # substitutes 50.0 for a failed judge, so six failed judges
                    # produce a plausible-looking 52.5 labelled "vertex_ai_eval".
                    # A failed metric is a failed metric: record it and let the
                    # caller decide whether the run still counts.
                    failed.append(metric_name)
                    err = getattr(metric_result, "error_message", None)
                    logger.warning(f"Judge metric {metric_name} failed: {str(err)[:200]}")
                    continue
                scores[metric_name] = round(float(score), 2)
                if getattr(metric_result, "explanation", None):
                    details[metric_name] = metric_result.explanation
    if failed:
        raise RuntimeError(
            f"{len(failed)}/{len(scores) + len(failed)} judge metrics failed: {', '.join(failed)}"
        )
    return scores, details


def _heuristic_eval(user_intent: str, proposed_plan: str) -> tuple[dict[str, float], dict[str, str]]:
    """Heuristic evaluation fallback when Vertex AI Eval is unavailable."""
    plan_lower = proposed_plan.lower()
    scores, details = {}, {}

    # Safety
    safety_score = 80.0
    if "emergency" in plan_lower and "no detour" in plan_lower:
        safety_score = 20.0
    if "emergency vehicle" in plan_lower:
        safety_score = min(safety_score + 10.0, 100.0)
    scores["safety_compliance"] = safety_score
    details["safety_compliance"] = "Heuristic safety check"

    # Community
    community_score = 75.0
    if any(kw in plan_lower for kw in ["cheer zone", "community"]):
        community_score = min(community_score + 10.0, 100.0)
    scores["community_impact"] = community_score
    details["community_impact"] = "Heuristic community check"

    # Logistics
    logistics_score = 60.0
    for kw in ["hydration", "timing", "chip", "marshal"]:
        if kw in plan_lower:
            logistics_score += 10.0
    scores["logistics_completeness"] = min(logistics_score, 100.0)
    details["logistics_completeness"] = "Heuristic logistics check"

    # Financial
    financial_score = 65.0
    for kw in ["budget", "cost", "revenue", "sponsor"]:
        if kw in plan_lower:
            financial_score += 8.0
    scores["financial_viability"] = min(financial_score, 100.0)
    details["financial_viability"] = "Heuristic financial check"

    # Experience
    experience_score = 70.0
    for kw in ["scenic", "landmark", "medal", "post-race"]:
        if kw in plan_lower:
            experience_score += 8.0
    scores["participant_experience"] = min(experience_score, 100.0)
    details["participant_experience"] = "Heuristic experience check"

    # Intent
    scores["intent_alignment"] = 70.0
    details["intent_alignment"] = "Heuristic intent check"

    # Distance
    distance_result = _check_distance_compliance_logic(proposed_plan)
    scores["distance_compliance"] = float(distance_result["score"])
    details["distance_compliance"] = distance_result["explanation"]

    return scores, details


# El agente tiene que copiar estas descripciones dentro de su salida
# estructurada. Sin tope, seis explicaciones de juez desbordan
# max_output_tokens y el JSON llega cortado (docs/GOTCHAS.md #19).
MAX_FINDING_CHARS = 400


def _build_result(scores, details, eval_method):
    """Build the final evaluation result from scores and details."""
    findings, improvement_suggestions = [], []
    for criterion, score in scores.items():
        if score < 80.0:
            severity = "high" if score < SEVERITY_THRESHOLDS["high"] else "medium" if score < SEVERITY_THRESHOLDS["medium"] else "low"
            descripcion = details.get(criterion, f"Score: {score}")
            if len(descripcion) > MAX_FINDING_CHARS:
                descripcion = descripcion[:MAX_FINDING_CHARS].rstrip() + "..."
            findings.append({"criterion": criterion, "description": descripcion, "severity": severity})
            improvement_suggestions.append(_suggest_improvement(criterion, score, details.get(criterion, "")))

    overall_score = round(sum(scores.get(c, 50.0) * w for c, w in CRITERION_WEIGHTS.items()), 2)
    passed = overall_score >= 85.0 and not any(f["severity"] == "high" for f in findings)
    return {"passed": passed, "scores": scores, "findings": findings,
            "improvement_suggestions": improvement_suggestions,
            "overall_score": overall_score, "eval_method": eval_method}


def _suggest_improvement(criterion, score, detail):
    suggestions = {
        "safety_compliance": "Add emergency vehicle crossing points every 2 miles and plan detour routes around hospitals.",
        "community_impact": "Include cheer zones, notify affected residents, and ensure equitable route distribution.",
        "logistics_completeness": "Add timing chip details, plan course marshal positions, and detail start/finish infrastructure.",
        "financial_viability": "Add budget breakdown with cost estimates and identify 3+ revenue sources.",
        "participant_experience": "Highlight scenic landmarks and detail post-race amenities (medals, food, recovery).",
        "intent_alignment": "Review the user's original request and ensure the plan matches their stated requirements.",
        "distance_compliance": "Verify the route is exactly 26.2 miles (42.195 km) for marathon certification.",
    }
    return suggestions.get(criterion, f"Improve {criterion} (current score: {score:.2f})")
