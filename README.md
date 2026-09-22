# marathon-agents

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jorgeucano/Multi-Agent-Marathon-Planner-Workshop/blob/main/notebooks/marathon_agents_workshop.ipynb)

Four ADK agents that plan and simulate a city marathon together: a **Planner** that
orchestrates, an **Evaluator** that scores the plan with Vertex AI Evaluation
(LLM-as-Judge), a **Simulation Controller** reached over the **A2A protocol**,
and a **Runner Cohort Agent** inside the Simulator that models how four
representative groups experience the race.

Runnable reconstruction of the Google Codelab
[Build a Multi-Agent Marathon Planner with ADK and A2A](https://codelabs.developers.google.com/next26/dev-keynote/build-multi-agent-marathon-planner),
packaged for teaching it as a workshop: every step is a git tag, the files the
codelab forgets to create are included, and there is a client that actually
exercises the four agents end to end.

> Read [docs/GOTCHAS.md](docs/GOTCHAS.md) before you teach this. It lists every
> place this repo deviates from the codelab and why — including the tool the
> codelab tells the agent to call but never writes.

```
                        ┌──────────────────────┐
   your request ──────► │    planner_agent     │  gemini-3-flash-preview
                        │  (lead orchestrator) │  thinking_budget=2048
                        └───────┬──────────────┬───┘
                  AgentTool    │              │ A2A / JSON-RPC :8089
                  same process │              │ separate process
                           ┌────▼─────┐   ┌────▼────────────────┐
                           │evaluator │   │ simulator_agent     │
                           │  agent   │   │ readiness gate      │
                           │7 metrics │   └──────────┬──────────┘
                           └──────────┘              │ AgentTool
                                              ┌─────▼───────────┐
                                              │ runner_agent    │
                                              │ four cohorts    │
                                              └─────────────────┘
```

## Quickstart

```bash
git clone https://github.com/jorgeucano/Multi-Agent-Marathon-Planner-Workshop.git marathon-agents
cd marathon-agents
curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env

cp .env.example .env && $EDITOR .env        # set GOOGLE_CLOUD_PROJECT
gcloud services enable aiplatform.googleapis.com
gcloud auth application-default login       # not needed inside Cloud Shell

uv sync
uv run python scripts/preflight.py          # fails here, not on stage
```

### Solo mode — Planner + Evaluator

```bash
uv run python -m src.planner_agent.runtime.local_server
# second terminal:
uv run python scripts/send_request.py --city "Buenos Aires" --participants 30000 --watch
```

### The visual demo — `adk web`

```bash
uv run python -m src.simulator_agent.runtime.local_server        # terminal 1
make web                                                          # terminal 2 -> http://127.0.0.1:8000
```

ADK's dev UI: pick `planner_agent`, type the request, and watch the event
trace on the right — every `plan_marathon_route` call, the `evaluator_agent`
sub-agent, and the A2A hop to `simulator_agent`. This is the part the room
should see; the codelab never mentions it.

The Colab workshop then adds a separate animated Buenos Aires race view built
from the Planner's deterministic GeoJSON: route, landmarks, hydration, medical
posts, and a controllable visual sample of the 30,000-runner field. It is a
lightweight workshop visualization, not the keynote's full Angular/Three.js
simulation (which also requires the Go gateway, Redis, WebSockets, and Runner
agents from `GoogleCloudPlatform/race-condition`).

### Full Team mode — four agents, one A2A boundary

```bash
# terminal 1
uv run python -m src.simulator_agent.runtime.local_server

# terminal 2 — the env var is what turns Full Team mode on
SIMULATOR_AGENT_RESOURCE_NAME=local:8089 \
  uv run python -m src.planner_agent.runtime.local_server

# terminal 3
uv run python scripts/send_request.py --city Austin --theme charity --watch
```

The Planner log should show both lines:

```
Added local Evaluator tool
Added A2A Simulation Controller tool
```

If the second one is missing you forgot `SIMULATOR_AGENT_RESOURCE_NAME` — that
is the single most common mistake in this workshop. The Simulator startup has
its own `Tools:` line; `AgentTool` there is the local `runner_agent` delegation.

## Layout

```
src/
  config.py                         shared GCP config
  planner_agent/
    agent/        config, prompts, auth, tools (A2A wiring), agent
    evaluator/    schemas, instruction.md, 7 custom metrics, agent
    skills/       route-planning/ (SKILL.md + tools.py) , plan-evaluation/
    services/     memory_manager (Memory Bank topics), session_manager (TTL cache)
    runtime/      agent_card, agent_executor, local_server  (:8084)
  simulator_agent/
    agent/        schemas, deterministic checklist, agent
    skills/       review-marathon-plan/
    services/     memory_manager, session_manager
    runtime/      agent_card, agent_executor, local_server  (:8089)
  runner_agent/
    agent/        cohort instruction + deterministic pace/fatigue tool
scripts/
  preflight.py                      pre-workshop environment check
  send_request.py                   A2A client — the actual end-to-end demo
tests/                              offline suite: no GCP, no network
docs/
  GOTCHAS.md                        deviations from the codelab + live-demo traps
  WORKSHOP.md                       timed runsheet for teaching it
```

## Environment variables

| Variable | Required | Meaning |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | yes | GCP project with billing and the Vertex AI API on |
| `GOOGLE_CLOUD_LOCATION` | no | default `us-central1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | yes | `true` — use Vertex, not AI Studio |
| `SIMULATOR_AGENT_RESOURCE_NAME` | no | `local:8089` or an Agent Engine resource name. Unset = Solo mode |
| `PLANNER_MODEL` / `EVALUATOR_MODEL` / `SIMULATOR_MODEL` / `RUNNER_MODEL` | no | per-agent model override |
| `EVAL_MODE` | no | `heuristic` forces the fallback path (fast, no judge calls) |
| `AGENT_ENGINE_ID` | no | enables Memory Bank + persistent sessions |
| `USE_ADK_EXECUTOR` | no | `1` runs the planner on ADK's generic A2A executor |

## Tests

```bash
uv run --extra dev pytest -q          # full suite
uv run --no-project --with pytest python -m pytest tests/test_route_planning.py -q   # offline only
```

## Run it in Colab (no local setup)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jorgeucano/Multi-Agent-Marathon-Planner-Workshop/blob/main/notebooks/marathon_agents_workshop.ipynb)

`notebooks/marathon_agents_workshop.ipynb` runs the whole system on a Colab VM:
`auth.authenticate_user()` replaces the ADC dance, both A2A servers run as
processes on the same VM, the route is plotted on an animated map with runners,
and every step has a short explanation plus an intermediate check. Attendees
need a GCP project with billing enabled and nothing else — the notebook's first
cell lists the prerequisites.

The notebook is generated from `notebooks/build_notebook.py` so the cells are
reviewable source; edit the script, run it, commit both.

## Teaching it

Each codelab step is a git tag. Anyone who falls behind jumps forward:

```bash
git tag -l              # step-0-scaffold ... step-6-runtime, workshop-extras
git checkout step-3-evaluator
```

See [docs/WORKSHOP.md](docs/WORKSHOP.md) for the runsheet.

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Original codelab
material © Google LLC (code Apache 2.0, prose CC BY 4.0).
