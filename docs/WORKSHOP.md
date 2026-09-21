# Runsheet — Multi-Agent Marathon Planner

For the instructor. The codelab says 90 minutes; dictated with questions it is
2.5–3 h. Below is the **90-minute cut** that keeps the conceptual payload and
drops the typing, plus the long version if you have half a day.

---

## Before the room opens

| # | Task | Why |
|---|---|---|
| 1 | Run the whole thing in a **fresh** GCP project | The only way to see the errors attendees will see |
| 2 | `uv lock` and commit `uv.lock` | Everyone resolves the same ADK; see GOTCHAS #10 |
| 3 | `uv run python scripts/preflight.py` | Confirms models, ADC, ports, skill files |
| 4 | Confirm preview models answer in your region | GOTCHAS #11 |
| 5 | Time one full `send_request.py` run | That number is your stage patience |
| 6 | Send attendees: repo URL, `uv sync`, billing enabled, `gcloud auth application-default login` | GOTCHAS #13, #16 |

Attendee prerequisites, in one message:

> Before the session: GCP project with billing on, `gcloud services enable
> aiplatform.googleapis.com`, `gcloud auth application-default login`, clone
> `<repo>`, run `uv sync`, then `uv run python scripts/preflight.py`. If
> preflight is green you are ready. Bring that terminal.

---

## 90-minute cut

Attendees start from `git checkout step-4-simulator` — the Evaluator and the
Simulator are given. They **write the Planner and the A2A wiring**, which is
where the actual lesson lives.

| Min | Block | You do | They do |
|---:|---|---|---|
| 0–5 | Framing | The three agents, why not one prompt | — |
| 5–10 | Preflight | Run preflight on the projector | Run preflight; you triage |
| 10–20 | The Evaluator, read-only | Walk `MetricPromptBuilder`, the 7 metrics, the rubric scores | Read `evaluator/tools.py` |
| 20–30 | Judges are expensive | Run with `EVAL_MODE=heuristic`, then real. Show the hybrid fallback | Watch |
| 30–45 | Write the Planner | Live-code `agent/tools.py` `get_tools()` | Type along |
| 45–55 | Solo mode | Start planner, `send_request.py` | Same |
| 55–70 | A2A | Start the simulator, restart planner **with the env var**, show both log lines | Same |
| 70–80 | Full run | One end-to-end plan on the projector | Their own city |
| 80–90 | Close | ThinkingConfig per task, Memory Bank in production, cleanup | Questions |

**If you are short on time, cut in this order:** Memory Bank discussion → the
custom executor → the second Full Team run.

## Full version (three hours, with a break)

Steps 0–3 before the break (scaffold, services, Evaluator), 4–6 after
(Simulator, Planner, A2A). Same runsheet, each block roughly doubled, with a
checkpoint after each git tag: everyone runs the offline test suite, then
`git checkout step-N` if they are behind.

```bash
git tag -l
git checkout step-3-evaluator
uv run --extra dev pytest -q
```

---

## The three moments that carry the workshop

1. **The judge scoring a bad plan.** Feed a deliberately thin plan
   (`--city Austin --participants 30000` with the instruction trimmed) and show
   `safety_compliance` collapsing with a high-severity finding that blocks the
   pass even though the average is high. That is `_build_result` doing real work.
2. **Killing Vertex AI Eval mid-demo** (`EVAL_MODE=heuristic`). The system keeps
   answering. Hybrid evaluation stops being a slide and becomes a behaviour.
3. **`SIMULATOR_AGENT_RESOURCE_NAME`.** Same binary, same code, one env var, and
   a third agent joins over HTTP. Show the planner banner flipping from `SOLO`
   to `FULL TEAM`.

## Failure playbook

| Symptom | Cause | Fix on stage |
|---|---|---|
| `DefaultCredentialsError` | No ADC on a laptop | `gcloud auth application-default login` |
| Planner log has no `Added A2A Simulation Controller tool` | Env var missing on restart | Restart with the prefix |
| Agent card 404 | Wrong path (`agent.json`) | `/.well-known/agent-card.json` |
| Judge call hangs > 3 min | Eval API slow or quota | `EVAL_MODE=heuristic`, keep talking |
| `404 model not found` | Preview model moved/region | Set `*_MODEL` in `.env` |
| Agent calls the same tool forever | `output_schema` + `tools` | Drop `output_schema` on the Simulator (GOTCHAS #10) |
| Route looks invented | `route-planning/tools.py` missing | You are on the codelab, not this repo (GOTCHAS #2) |
| `uv sync` crawls | Conference wifi | Pair people onto one machine, keep going |

## Cleanup

```bash
# Ctrl+C in each server terminal
gcloud projects delete $PROJECT_ID   # only if the project was for this session
```

No Cloud Run services, no Agent Engine deployments — unless you created an Agent
Engine for the Memory Bank demo, in which case delete it explicitly.
