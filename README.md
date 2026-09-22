# Multi-Agent Marathon Planner Workshop

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jorgeucano/Multi-Agent-Marathon-Planner-Workshop/blob/main/notebooks/marathon_agents_workshop.ipynb)

Workshop ejecutable sobre Google ADK, Vertex AI y el protocolo A2A. Cuatro
agentes colaboran para diseñar, evaluar y simular una maratón urbana: un
**Planner** que orquesta, un **Evaluator** que puntúa, un **Simulation
Controller** remoto que verifica si el evento está listo y un **Runner Agent**
que representa la experiencia de los corredores.

Es una reconstrucción ejecutable del Google Codelab
[Build a Multi-Agent Marathon Planner with ADK and A2A](https://codelabs.developers.google.com/next26/dev-keynote/build-multi-agent-marathon-planner),
preparada para enseñarlo como workshop: cada paso tiene un tag de Git, están
incluidos los archivos que el codelab omite y hay un cliente que realmente
ejercita los cuatro agentes de punta a punta.

> Antes de presentarlo, leé [docs/GOTCHAS.md](docs/GOTCHAS.md). Documenta cada
> diferencia respecto del codelab y su motivo, incluida la herramienta que el
> tutorial pide invocar pero nunca implementa.

```
                        ┌──────────────────────┐
   tu pedido ─────────► │    planner_agent     │  gemini-3.1-flash-lite
                        │ (orquestador líder)  │  thinking_budget=2048
                        └───────┬──────────────┬───┘
                  AgentTool    │              │ A2A / JSON-RPC :8089
                  mismo proceso│              │ proceso separado
                           ┌────▼─────┐   ┌────▼────────────────┐
                           │evaluator │   │ simulator_agent     │
                           │  agent   │   │ readiness gate      │
                           │7 métricas│   └──────────┬──────────┘
                           └──────────┘              │ AgentTool
                                              ┌─────▼───────────┐
                                              │ runner_agent    │
                                              │ cuatro cohortes │
                                              └─────────────────┘
```

## Qué hace cada agente

| Agente | Responsabilidad | Cómo se conecta | Qué no debe hacer |
|---|---|---|---|
| `planner_agent` | Diseña la ruta y el plan operativo completo | Es el punto de entrada | No debe inventar geometría ni calificarse a sí mismo |
| `evaluator_agent` | Puntúa siete criterios con Vertex AI Evaluation y reglas determinísticas | `AgentTool`, dentro del Planner | No rediseña la carrera |
| `simulator_agent` | Verifica ruta, logística, seguridad y datos necesarios para simular | A2A/JSON-RPC, en el puerto 8089 | No reemplaza al Evaluator |
| `runner_agent` | Interpreta ritmo, congestión, hidratación, fatiga, abandono y llegada | `AgentTool`, dentro del Simulator | No aprueba el evento ni cambia los cálculos |

La topología es deliberada. El Evaluator está cerca del Planner porque es una
capacidad local. El Simulator cruza una frontera A2A para demostrar que podría
desplegarse de manera independiente. El Runner vuelve a ser local, pero vive
del otro lado de esa frontera, dentro del proceso del Simulator.

### Qué ocurre cuando enviás un pedido

1. El Planner identifica ciudad, cantidad de participantes y restricciones.
2. `plan_marathon_route` calcula una ruta real sobre el grafo vial y devuelve GeoJSON.
3. Las herramientas determinísticas agregan hidratación y puestos médicos.
4. El Planner completa tráfico, comunidad, logística, finanzas, cronograma y riesgos.
5. El Evaluator aplica siete rúbricas y devuelve scores comparables.
6. El Planner envía el plan completo al Simulator mediante A2A.
7. El Simulator ejecuta su checklist y delega la experiencia al Runner Agent.
8. La respuesta final combina plan, evaluación, readiness y hallazgos de corredores.

### Por qué el Runner usa cohortes

El workshop representa 30.000 participantes con cuatro cohortes: **elite (1%)**,
**competitive (14%)**, **main pack (60%)** y **back of pack (25%)**. Una función
determinística calcula tamaños, ritmos, tiempos de llegada, abandonos y riesgos;
el agente interpreta esos números sin modificarlos.

Esto conserva una delegación multiagente real sin lanzar 30.000 llamadas LLM.
Los puntos del mapa son una muestra visual de las cohortes, no agentes
individuales. Color, velocidad, tabla y reloj consumen los mismos resultados.

## Recorrido recomendado en Colab

1. Abrí el notebook con el botón **Open in Colab**.
2. Ejecutá las celdas 0.1–0.3 para instalar, autenticar y descargar el repositorio.
3. Revisá que el preflight termine con `0 failure(s)`.
4. Ejecutá el Paso 3 para levantar Simulator, Planner y la ADK Dev UI.
5. Abrí la URL de Cloudflare generada por la celda 3.5.
6. Pegá el pedido completo de la celda 3.6 en `planner_agent`.
7. Usá 4.3 para explicar la coreografía y 4.4 para mostrar cohortes y mapa.

> La URL `*.colab.dev` puede abrir la página pero devolver `403` para los bundles
> JavaScript de ADK. No es un error de los agentes. La celda 3.5 crea el túnel
> Cloudflare que evita ese proxy; el mapa de 4.4 se renderiza directamente en el
> notebook y no depende de la Dev UI.

### Pedido completo para la demostración

```text
Plan a scenic marathon in Buenos Aires for 30,000 runners.

Create a certified-distance route of 26.2 miles (42.195 km), starting and
finishing at the Obelisco. Use the route-planning tool and include the
calculated waypoints, hydration stations, medical tents, traffic closures,
community impact, logistics, finances, timeline, and risks.

Then send the complete plan to evaluator_agent for scoring and afterward to
simulator_agent for the final readiness verdict. Ask simulator_agent to
delegate runner experience to runner_agent for elite, competitive, main-pack,
and back-of-pack cohorts. Include the evaluation scores, overall score,
simulation verdict, runner readiness, and runner findings in the final response.
```

Qué deberías ver: llamadas a las herramientas de ruta, una delegación local al
Evaluator, un salto A2A al Simulator y, dentro de su log, la delegación al
Runner. La respuesta tiene que incluir scores, veredicto y hallazgos de las
cuatro cohortes.

## Ejecución local

```bash
git clone https://github.com/jorgeucano/Multi-Agent-Marathon-Planner-Workshop.git marathon-agents
cd marathon-agents
curl -LsSf https://astral.sh/uv/install.sh | sh && source $HOME/.local/bin/env

cp .env.example .env && $EDITOR .env        # configurar GOOGLE_CLOUD_PROJECT
gcloud services enable aiplatform.googleapis.com
gcloud auth application-default login       # no hace falta en Cloud Shell

uv sync
uv run python scripts/preflight.py          # detectar problemas antes de la demo
```

### Modo Solo — Planner + Evaluator

```bash
uv run python -m src.planner_agent.runtime.local_server
# segunda terminal:
uv run python scripts/send_request.py --city "Buenos Aires" --participants 30000 --watch
```

### Demo visual — `adk web`

```bash
uv run python -m src.simulator_agent.runtime.local_server        # terminal 1
make web                                                          # terminal 2 → http://127.0.0.1:8000
```

En la ADK Dev UI, elegí `planner_agent`, enviá el pedido y observá la traza de
eventos: llamadas a `plan_marathon_route`, delegación a `evaluator_agent` y el
salto A2A hacia `simulator_agent`. Esa traza explica la arquitectura técnica;
el mapa del notebook explica sus consecuencias sobre la carrera.

El notebook agrega una vista animada de Buenos Aires construida con el GeoJSON
determinístico del Planner: circuito, landmarks, hidratación, puestos médicos y
una muestra controlable de los 30.000 corredores. Es una visualización liviana
para el workshop, no la simulación Angular/Three.js completa del keynote, que
también necesita gateway Go, Redis, WebSockets y otros componentes.

### Modo Full Team — cuatro agentes, una frontera A2A

```bash
# terminal 1
uv run python -m src.simulator_agent.runtime.local_server

# terminal 2 — esta variable activa el modo Full Team
SIMULATOR_AGENT_RESOURCE_NAME=local:8089 \
  uv run python -m src.planner_agent.runtime.local_server

# terminal 3
uv run python scripts/send_request.py --city Austin --theme charity --watch
```

El log del Planner debe mostrar estas dos líneas:

```
Added local Evaluator tool
Added A2A Simulation Controller tool
```

Si falta la segunda, `SIMULATOR_AGENT_RESOURCE_NAME` no estaba definida cuando
arrancó el Planner. El Simulator muestra su propia línea `Tools:`; el
`AgentTool` de esa lista es la delegación local a `runner_agent`.

## Estructura del repositorio

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

## Variables de entorno

| Variable | Requerida | Significado |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | sí | Proyecto GCP con billing y Vertex AI API habilitados |
| `GOOGLE_CLOUD_LOCATION` | no | Región; para los modelos del workshop se recomienda `global` |
| `GOOGLE_GENAI_USE_VERTEXAI` | sí | `true` para usar Vertex AI y no AI Studio |
| `SIMULATOR_AGENT_RESOURCE_NAME` | no | `local:8089` o un recurso de Agent Engine; sin valor activa modo Solo |
| `PLANNER_MODEL` / `EVALUATOR_MODEL` / `SIMULATOR_MODEL` / `RUNNER_MODEL` | no | Modelo utilizado por cada agente |
| `EVAL_MODE` | no | `heuristic` fuerza el fallback rápido, sin llamadas al juez LLM |
| `AGENT_ENGINE_ID` | no | Habilita Memory Bank y sesiones persistentes |
| `USE_ADK_EXECUTOR` | no | `1` ejecuta el Planner con el executor A2A genérico de ADK |

## Pruebas

```bash
uv run --extra dev pytest -q          # suite completa
uv run --no-project --with pytest python -m pytest tests/test_route_planning.py -q   # ruta offline
```

## Notebook generado

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jorgeucano/Multi-Agent-Marathon-Planner-Workshop/blob/main/notebooks/marathon_agents_workshop.ipynb)

`notebooks/marathon_agents_workshop.ipynb` ejecuta el sistema completo en una VM
de Colab. `auth.authenticate_user()` reemplaza la autenticación ADC local, los
servidores corren como procesos de la misma VM y la ruta aparece en un mapa
animado con corredores. Cada paso contiene explicación, guion para presentar y
una comprobación intermedia.

El notebook se genera desde `notebooks/build_notebook.py` para que las celdas
sean código revisable. Si modificás el generador, ejecutalo y versioná ambos
archivos.

## Cómo dictar el workshop

Cada paso del codelab tiene un tag. Si alguien se queda atrás puede avanzar a
un checkpoint conocido:

```bash
git tag -l              # step-0-scaffold ... step-6-runtime, workshop-extras
git checkout step-3-evaluator
```

La agenda minuto a minuto está en [docs/WORKSHOP.md](docs/WORKSHOP.md).

## License

Apache 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Original codelab
material © Google LLC (code Apache 2.0, prose CC BY 4.0).
