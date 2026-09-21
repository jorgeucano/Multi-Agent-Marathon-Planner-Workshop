# Evaluation Criteria

> NOT IN THE CODELAB. The `plan-evaluation` SKILL.md references this file, but no
> codelab step creates it. Written for this repo so the Skill resolves.

These are the same 7 criteria the Evaluator Agent scores with Vertex AI
Evaluation. The planner uses them as a **self-check before** sending the plan
out, so the first evaluation pass does not fail on something obvious.

| Criterion | Weight | Fails when... | Passes when... |
|---|---:|---|---|
| `safety_compliance` | 20% | A hospital or fire station is enclosed with no detour; no emergency crossings | Crossings every 2 miles, documented detours, evacuation corridors |
| `logistics_completeness` | 20% | No timing system, no marshal plan, no start/finish sizing | Chip timing, marshal positions, corral and chute capacity, toilets |
| `community_impact` | 15% | One neighbourhood absorbs all disruption; no notification plan | Cheer zones, 30-day notice, progressive reopening, equitable routing |
| `financial_viability` | 15% | Costs exceed revenue, or registrations are the only income | Balanced budget, 3+ revenue streams, realistic per-line estimates |
| `participant_experience` | 15% | No landmarks, no post-race amenities | Scenic waypoints, medals, food, recovery area, clear elevation story |
| `intent_alignment` | 10% | Wrong city, wrong theme, wrong scale vs. the request | Every stated constraint answered explicitly |
| `distance_compliance` | 5% | Any distance other than 26.2 mi / 42.195 km | Exactly 26.2 miles, stated in the plan text |

**Pass threshold:** weighted `overall_score >= 85` **and** zero high-severity
findings. Severity mapping: score < 40 -> high, < 60 -> medium, < 80 -> low.

## Self-check before submitting a plan

1. Does the plan text literally contain "26.2 miles" (the distance check is a
   regex, not an LLM - it cannot infer the distance)?
2. Does it name water stations, medical tents, timing and start/finish?
3. Does it name the emergency plan with crossing intervals?
4. Does the budget list both costs and at least three revenue sources?
5. Does it restate the user's city, theme, date and participant count?

Missing any of these costs 10-20 points for a reason that is cheap to fix.
