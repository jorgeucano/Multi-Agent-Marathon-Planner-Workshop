# Gotchas — what this repo changes, and what breaks live

Every deviation from the codelab, why it is here, and the traps that bite during
a live session. Read this before you teach.

Source: <https://codelabs.developers.google.com/next26/dev-keynote/build-multi-agent-marathon-planner>
(9 steps, 90 min stated, ~$5 stated).

---

## A. Things the codelab ships that do not work as written

### 1. Circular import in the Evaluator, hidden by a bare `except`

The codelab has `evaluator/tools.py` do `from .agent import CRITERION_WEIGHTS,
SEVERITY_THRESHOLDS, MODEL`, while `evaluator/agent.py` does `from .tools import
evaluate_plan`. That only resolves if `.agent` is imported first. Import
`evaluator.tools` first and you get `ImportError: cannot import name
'evaluate_plan' from partially initialized module`.

Worse, the codelab's `__init__.py` is:

```python
try:
    from .agent import root_agent, AGENT_NAME, MODEL
    __all__ = [...]
except Exception:
    __all__ = ["root_agent"]      # root_agent does not exist
```

So the failure is silent: the package imports fine and the agent is simply gone.

**Here:** constants moved to `evaluator/config.py`, both modules import from
there, and the `__init__` files let errors raise. Package `__init__`s are also
lazy (PEP 562) so importing a package no longer builds an LlmAgent as a side
effect — that is what lets the test suite run with no credentials.

### 2. `plan_marathon_route` — the tool that does not exist

The planner instruction says "Call `plan_marathon_route`". `route-planning/SKILL.md`
says `tools.py` contains it. `get_tools()` loads it with
`load_tool_from_skill("route-planning", "plan_marathon_route")`.

**No step in the codelab ever creates `skills/route-planning/tools.py`.**
`load_tool_from_skill` returns `None` on a missing file and the tool is dropped
without a word, so the model hallucinates a route instead of computing one.

**Here:** the file is written — a real road graph for Las Vegas, Austin and
Buenos Aires, Dijkstra, loop closure onto 42.195 km, GeoJSON out, plus
`add_water_stations` and `add_medical_tents` (also named in SKILL.md, also
missing). Unknown cities fall back to a deterministic synthetic ring flagged
`network_source: "synthetic"`, so the demo survives a city shouted from the
audience. `load_tool_from_skill` now logs an error instead of failing quietly.

Also missing and written here: `route-planning/references/marathon_planning_guide.md`
and `plan-evaluation/references/evaluation_criteria.md`, both referenced by their
SKILL.md.

### 3. `MarathonPlannerExecutor` is written and never used

Step 6 has you write a ~120-line executor with session manager, memory service,
`ContextCacheConfig`, `max_llm_calls=15` — then `local_server.py` builds ADK's
generic `A2aAgentExecutor` with a legacy `Runner(app_name=..., agent=...)`
signature instead. The custom executor is dead code; the simulator's equivalent
*is* wired, so the two agents are asymmetric for no stated reason.

**Here:** the custom executor is the default. `USE_ADK_EXECUTOR=1` switches to
the codelab's path — useful to show both on stage.

### 4. `uv sync` can fail before anything is built

`pyproject.toml` declares `readme = "README.md"` and hatchling builds the
project itself. The codelab never creates `README.md`, so hatchling can refuse
the build. **Here:** README.md exists.

### 5. `vertexai.preview.reasoning_engines.templates.a2a.create_agent_card`

A `preview` import path, used by both agent cards. It moves between SDK
releases. **Here:** wrapped in `try/except ImportError` with a hand-built
`AgentCard` fallback.

### 6. The simulator prints the wrong agent-card path

`local_server.py` prints `/.well-known/agent.json`; `A2AStarletteApplication`
serves `/.well-known/agent-card.json`, which is also what the planner fetches.
Copy the printed URL and you get a 404 and conclude A2A is broken.
**Here:** corrected, and the simulator card's `url` is set explicitly so the
planner talks to the address it actually resolved.

### 7. Memory Bank is never actually demonstrated

`VertexAiMemoryBankService` needs an Agent Engine. No step creates one, and
`create_memory_service` returns `None` when `AGENT_ENGINE_ID` is unset, while
`auto_save_memories` returns early. Everything runs on `InMemorySessionService`
and nothing persists.

**Do not tell the room memory is working.** Either create an Agent Engine
beforehand and set `AGENT_ENGINE_ID`, or present it as "this is the one line you
change for production". Same for `BUCKET_URI` — declared in `config.py`, never
created, never used.

### 8. "Test the multi-agent system" never tests the multi-agent system

The final step's only check is `curl .../.well-known/agent-card.json`. Nothing
sends a message, so the Planner → Evaluator → Simulator path is never exercised
and no one sees the system work. **Here:** `scripts/send_request.py` sends a real
A2A `message/send`, polls the task and prints the artifact.

### 9. Default port mismatch

`_get_agent_a2a_endpoint(resource_name, default_port=8080)` defaults to 8080
while the simulator listens on 8089. It only works because the caller passes
8089 explicitly. **Here:** one `SIMULATOR_DEFAULT_PORT = 8089` constant.

---

## B. Things that are correct but will bite you live

### 10. Unpinned dependencies: the codelab does not install today

**Verified on 2026-09-21, from a clean environment.** The codelab declares only
floors:

```toml
"google-cloud-aiplatform[agent_engines,adk,evaluation]>=1.121.0"
"google-adk>=1.25.0"
"a2a-sdk>=0.3.9"
```

Today those floors resolve to the **next major** of all three:

| Package | Codelab floor | Resolves to |
|---|---|---|
| `google-adk` | `>=1.25.0` | **2.9.2** |
| `a2a-sdk` | `>=0.3.9` | **1.1.5** |
| `google-cloud-aiplatform` | `>=1.121.0` | **2.1.3** |

On those versions, symbols the codelab code imports are gone:

```
x a2a.server.apps                 -> ModuleNotFoundError  (no A2A server at all)
x a2a.types.TransportProtocol     -> symbol missing
x a2a.utils.new_agent_text_message -> symbol missing
```

`a2a.server.apps` is where `A2AStarletteApplication` lives. Without it **neither
local server can be built** — the entire final step of the codelab fails at
import. Someone copy-pasting the codelab today gets a `ModuleNotFoundError`, not
a working system.

**Here:** upper bounds in `pyproject.toml` (`google-adk>=1.25,<2`,
`a2a-sdk>=0.3.9,<1`, `google-cloud-aiplatform>=1.121,<2`), which resolve to
adk 1.39.1 / a2a-sdk 0.3.26 / aiplatform 1.165.1 — all 31 symbols present, all
three agents construct, both servers start, the A2A round trip completes.
`uv.lock` is committed so every attendee gets exactly what was rehearsed.

> Note on a false alarm: `vertexai.types` fails under
> `importlib.import_module("vertexai.types")` but the codelab's actual form,
> `from vertexai import types`, resolves fine (lazy alias to
> `vertexai._genai.types`). Don't "fix" that one.

### 10b. `output_schema` together with `tools`

Both the Evaluator (`output_schema=EvaluationResult` + `PreloadMemoryTool` +
`evaluate_plan`) and the Simulator (`output_schema=SimulationApproval` +
`SkillToolset`) use this combination. On adk 1.39.1 **both agents construct
without error** — verified locally. The historical failure modes are runtime
ones: [#3413](https://github.com/google/adk-python/issues/3413) (infinite tool
loop on 1.18) and [#3969](https://github.com/google/adk-python/issues/3969)
(schema ignored). If it loops on stage, drop `output_schema` from the Simulator
and let the instruction carry the format.

### 10c. Experimental features in use

ADK prints `[EXPERIMENTAL]` warnings for three things this system depends on:
`SKILL_TOOLSET`, `RemoteA2aAgent` / `A2aAgentExecutor`, and `AGENT_CONFIG`.
They work, but expect breaking changes between ADK minors — one more reason the
lock file matters.

### 11. The codelab's models 404 in the codelab's own region

**Verified 2026-09-21** on a project with billing and Vertex AI enabled:

| Model | `us-central1` (codelab `.env`) | `global` |
|---|---|---|
| `gemini-3-flash-preview` | **404** | OK |
| `gemini-3.1-pro-preview` | **404** | OK |
| `gemini-3.1-flash-lite` | **404** | OK |
| `gemini-2.5-flash` / `-pro` / `-flash-lite` | OK | OK |

Every Gemini 3.x model is served from `location=global`. The codelab hard-codes
`GOOGLE_CLOUD_LOCATION=us-central1`, so a fresh follower gets three 404s at the
first model call — after 40 minutes of setup. `scripts/preflight.py` pings all
three models and fails here, before anything else.

**Here:** `.env.example` uses `global` and `gemini-3.1-flash-lite` for all
three agents. Full Team run completes in ~57 s with it. The preview pair from
the codelab also works in `global` if you want fidelity — the `pro` judge is
slower and pricier.

### 12. The Evaluator is the slow part

Seven judges, one of them a `pro` model with a 1024-token thinking budget.
One to three minutes of silence. Two options on stage: narrate it, or run
`EVAL_MODE=heuristic` and show the hybrid fallback as the design feature it is —
then switch back for the real run.

### 13. No ADC outside Cloud Shell

The codelab assumes Cloud Shell and only runs `gcloud auth list`. Anyone on a
laptop needs `gcloud auth application-default login` or everything fails with a
`DefaultCredentialsError` twenty minutes in. Say it in the first five minutes.

### 14. Only one API is enabled

`gcloud services enable aiplatform.googleapis.com`. On a brand-new project you
may also need billing linked and `serviceusage` / `cloudresourcemanager`
reachable before that command itself works.

### 15. Restarting the planner without the env var

Full Team mode is `SIMULATOR_AGENT_RESOURCE_NAME=local:8089` prefixed on the
restart. Forget it and the planner silently goes back to Solo mode. The startup
banner here prints `Mode: SOLO` / `FULL TEAM` so it is visible from the back row.

### 16. `uv sync` downloads a lot

`google-cloud-aiplatform[agent_engines,adk,evaluation]` plus ADK, a2a-sdk and
pandas. On conference wifi, 30 people doing this at once is a wall. Have them
run it before arriving.

---

## C. Known limitations of this repo

- The road networks in `route-planning/tools.py` are hand-built, not OSM. The
  reported course is the certified 42.195 km with the adjustment stated
  explicitly in `course_adjustment_km` — do not present it as a surveyed course.
- The full pipeline has **not** been run against live Vertex AI from here. The
  offline suite (`tests/`) passes; the GCP path needs one real run in your own
  project before you teach. That run is the whole of day-before prep.
