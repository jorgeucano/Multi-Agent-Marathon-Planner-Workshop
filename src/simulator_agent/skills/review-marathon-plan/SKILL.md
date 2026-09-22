---
name: review-marathon-plan
description: Step-by-step methodology for reviewing marathon plans for simulation readiness, covering route feasibility, logistics completeness, safety clearance, and runner-cohort experience.
---

# Review Marathon Plan

## Purpose

Systematically confirm that a marathon plan is ready for simulation execution by verifying the presence of all required prerequisite data.

## Procedure

### Step 1: Prerequisite Data Verification

Use the `check_plan_readiness` tool to confirm the presence of:

1. **Route Data**: Waypoints, landmarks, distance (26.2 mi / 42.195 km), start/finish locations.
2. **Logistics Data**: Water stations, medical tents, timing systems, participant scale.
3. **Safety Data**: Emergency access routes, evacuation plans, crowd management.

### Step 2: Approval Decision

1. Set `approved=true` ONLY if all three data categories are present.
2. If any critical data is missing, set `approved=false` and list missing elements in `blockers`.
3. Provide `recommendations` for minor data gaps.

### Step 3: Runner-Cohort Experience

1. Delegate the complete plan to `runner_agent` exactly once.
2. Preserve the deterministic cohort sizes, pace, finish-time, dropout, and risk values returned by the Runner Agent.
3. Include `runner_readiness` and the most important `runner_findings` in the final simulation approval.
4. Treat the Runner Agent as a runner-experience specialist, not as a second approval gate: the Simulator remains responsible for the final `approved` decision.
