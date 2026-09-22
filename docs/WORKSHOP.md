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

## 60-minute runsheet

Attendees do **not** type code. Sixty minutes is enough to understand the
system and see it run; it is not enough to build it. They follow along in the
repo (or the Colab), you drive. Everything that costs minutes of silence has a
pre-warmed fallback.

| Min | Block | What happens on screen | Fallback |
|---:|---|---|---|
| 0-4 | Framing | Three agents, one request. Why not one prompt. | — |
| 4-8 | The bug that teaches | `git tag -l`, then GOTCHAS #2: the tool the codelab calls but never writes. "A missing tool looks like a hallucination, not an error." | — |
| 8-18 | The Evaluator | `evaluator/tools.py`: one `MetricPromptBuilder` on screen. Then `tests/test_evaluator_scoring.py::test_high_severity_finding_blocks_a_pass` — 95 average, still fails. | Offline, always works |
| 18-26 | The route | `plan_marathon_route("Buenos Aires")` in a REPL: waypoints, closure severity, 42.195 km with the adjustment stated. | Offline |
| 26-34 | Wiring | `agent/tools.py::get_tools()`: SkillToolset / AgentTool / RemoteA2aAgent side by side. Start the simulator, `curl` its agent card. | — |
| 34-40 | One env var | Start the planner **without** the var (banner: `SOLO`), Ctrl+C, start **with** it (banner: `FULL TEAM`, 7 tools). | — |
| 40-52 | The run | Send the request, then the event-by-event choreography: `plan_marathon_route` at ~10 s, `evaluator_agent` at ~17 s (AgentTool, same process), `simulator_agent` at ~30 s (A2A, HTTP). ~45 s total with flash-lite. | `EVAL_MODE=heuristic` pre-started in another tab |
| 52-57 | Break it | Kill the simulator, resend. What the planner does is in its *instruction*, not its code. | Skip if late |
| 57-60 | Close | ThinkingConfig per task. Memory Bank is **not** demonstrated — say so. Repo + Colab link. | — |

**Cut order if you run late:** 52-57 first, then compress 18-26 to a single
slide of output.

**On the projector, `adk web` is the instructor's tool, not the attendees'.**
It works on a laptop (`make web`, http://127.0.0.1:8000). Inside Colab the port
proxy returns 403 on the UI's JavaScript chunks, so attendees get the same
choreography from the notebook's 4.3 cell instead — which talks to the API from
the kernel and never touches the proxy.

**Pre-warm before the room opens:** `uv sync` done, ADC valid, simulator
running, one full request already completed once today (model cold starts and
quota surprises happen on the *first* call, not the tenth).

## Extended version (90 min - 3 h)

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
   (`--city Rosario --participants 30000` with the instruction trimmed) and show
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
