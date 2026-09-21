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

### 17. A failed judge is scored 50, and the run is still called "vertex_ai_eval"

In `_run_custom_eval` the codelab does:

```python
raw_score = metric_result.score if ... metric_result.score is not None else 50.0
```

So when a judge metric fails, it becomes a 50. When **six** fail (see #18), the
result is `overall_score: 52.5` (six 50s plus the deterministic distance check
at 100), labelled `eval_method: "vertex_ai_eval"`. It looks like a mediocre
plan. It is actually a broken evaluator. We shipped that number in a rehearsal
before noticing.

**Here:** a metric with no score is recorded as failed and `_run_custom_eval`
raises, so `evaluate_plan` falls back to the heuristic path **and says so** in
`eval_method`. Fifty is never invented.

### 18. `MetricPromptBuilder` output does not parse — with any judge model

**Verified 2026-09-21**, aiplatform 1.165.1, judges tried: `gemini-3.1-flash-lite`,
`gemini-2.5-flash`, `gemini-3-flash-preview`, `gemini-3.1-pro-preview` (the
codelab's own). Every LLM metric fails identically:

```
400 INVALID_ARGUMENT: Error parsing JSON. Expecting property name enclosed in
double quotes ... Input: {### Evaluation  **Step 1: Assessment ...
```

The template `str(MetricPromptBuilder(...))` ends with *"Step 1: Assess the
response ... Step 2: Score based on the Rating Scores. Give a brief rationale"*
— it asks for prose. The Evaluation service then tries to parse the judge's
prose as JSON. Setting `response_mime_type="application/json"` on the judge does
**not** help. `return_raw_output=True` is rejected by the API
(`Unknown name "custom_output_format_config"`), and `result_parsing_function`
takes a string, not a callable.

**What works:** `judge_model_system_instruction` telling the judge to answer
with exactly `{"score": <int>, "explanation": "<text>"}`. Scores and
explanations come back for all six metrics. Applied to every metric in
`evaluator/tools.py` as `JUDGE_SYSTEM_INSTRUCTION`.

For the room: this is the best five minutes of the workshop. "LLM-as-Judge" is
not a prompt, it is a contract between three parties — the rubric, the model,
and the parser — and the codelab only wrote two of them.

### 19. The Evaluator truncates its own structured output

Once the judges actually return (see #18), each one ships a paragraph of
`explanation`. The agent has to copy all seven into `EvaluationResult`, which
overruns the codelab's `max_output_tokens=4096`. The JSON arrives cut off and
Pydantic rejects it:

```
1 validation error for EvaluationResult
  Invalid JSON: EOF while parsing an object at line 5 column 16244
```

The A2A task then fails with a generic `Planning failed`, which looks like an
A2A problem and is not.

**Here:** findings are capped at `MAX_FINDING_CHARS = 400` in `_build_result`
and `max_output_tokens` is 8192. Note the ordering: this bug is *invisible*
until #18 is fixed, because a broken judge returns no explanation to copy.

### 20. OpenStreetMap tiles are blocked from Colab

`folium.Map(tiles="OpenStreetMap")` renders a wall of `403 Access blocked - App
is not following the tile usage policy` from a Colab VM. CartoDB now requires an
API key. **Here:** Esri World Street Map, no key, no block.

### 21. The Colab port-proxy URL cannot be written down

`adk web` inside Colab is reachable only through a per-session, per-user signed
subdomain (`https://8000-m-s-<hash>.<region>.prod.colab.dev`). Copying one from
a tutorial gives `DNS_PROBE_FINISHED_NXDOMAIN`. Ask for it at runtime with
`google.colab.kernel.proxyPort(8000)` — and mind the trailing slash, or you get
`colab.devdev-ui`.

**And opening it in a new tab does not work either.** The HTML loads, then every
JavaScript chunk comes back `403`: the proxy does not authenticate sub-resource
requests made outside the notebook's context, so you get a blank page and four
403s in the console. That is why `serve_kernel_port_as_window` is deprecated
("Try `serve_kernel_port_as_iframe` instead" — Colab says so itself).

**Here:** cell 3.4 starts the server with `--host 0.0.0.0`, health-checks
`/list-apps` from inside the VM first (so a server problem is never mistaken for
a proxy problem), prints how the signed URL is built for teaching purposes, and
renders the UI with `output.serve_kernel_port_as_iframe` — the iframe runs in
the notebook's authenticated context and loads.

### 22. "Already cloned, skipping" is a silent trap

The obvious way to write the clone step is `if not isdir(repo): clone`. On the
second run of a Colab session — or after any push — that keeps the code from the
**first** clone, with no output saying so beyond a cheerful "already exists".
You then debug bugs that were fixed hours ago. It cost us a full round trip.

**Here:** cell 0.3 does `git fetch --tags --force && git reset --hard origin/main`
when the directory exists (fetch+reset, not `pull`: the history may have been
rewritten), prints the commit it ended up on, and warns if `src.*` modules were
already imported in this session — because updating files on disk does nothing
for a module Python has already cached. Restart the runtime in that case.

## C. Known limitations of this repo

- The road networks in `route-planning/tools.py` are hand-built, not OSM. The
  reported course is the certified 42.195 km with the adjustment stated
  explicitly in `course_adjustment_km` — do not present it as a surveyed course.
- The full pipeline has **not** been run against live Vertex AI from here. The
  offline suite (`tests/`) passes; the GCP path needs one real run in your own
  project before you teach. That run is the whole of day-before prep.
