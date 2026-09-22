#!/usr/bin/env python3
"""Generate notebooks/marathon_agents_workshop.ipynb.

The notebook is the attendee-facing version of the workshop: it runs the whole
system on a Colab VM. It is generated from this script so that the cells live
in git as reviewable source and the .ipynb never carries stale outputs.

    python notebooks/build_notebook.py
"""

from __future__ import annotations

import json
import pathlib
import uuid

OUT = pathlib.Path(__file__).with_name("marathon_agents_workshop.ipynb")
REPO_URL = "https://github.com/jorgeucano/Multi-Agent-Marathon-Planner-Workshop"

cells: list[tuple[str, str]] = []


def md(src: str) -> None:
    cells.append(("markdown", src.strip("\n")))


def code(src: str) -> None:
    cells.append(("code", src.strip("\n")))


# ---------------------------------------------------------------------------
# Intro + prerequisites
# ---------------------------------------------------------------------------
md(r'''
# 🏃 Multi-Agent Marathon Planner — Workshop

**ADK + A2A + Vertex AI Evaluation**, corriendo entero acá en Colab.

## ✅ Antes de empezar — lo que necesitás tener listo

| # | Requisito | Cómo lo verificás |
|---|---|---|
| 1 | **Una cuenta Google** con acceso a un **proyecto de Google Cloud** | [console.cloud.google.com](https://console.cloud.google.com) → el selector de proyectos arriba muestra al menos uno |
| 2 | **Facturación habilitada** en ese proyecto | Menú ☰ → *Facturación* → el proyecto tiene una cuenta de facturación vinculada. **Sin esto Vertex AI no responde.** El costo del workshop es de centavos, pero la API exige billing. |
| 3 | **Permiso** de Owner o Editor en el proyecto (o el rol *Vertex AI User*) | IAM → tu usuario aparece con ese rol. Si el proyecto lo creaste vos, ya sos Owner. |
| 4 | El **Project ID** a mano (no el nombre: el id, tipo `mi-proyecto-123456`) | En el selector de proyectos, columna *ID* |
| 5 | **Guardá tu propia copia** de este notebook: *Archivo → Guardar una copia en Drive* | Si no, los cambios que hagas no se guardan |

**No hace falta instalar nada en tu máquina.** Todo corre en la VM de Colab: dependencias, autenticación, los dos servidores A2A. El Paso 0.2 habilita la API de Vertex AI por vos.

Si no tenés proyecto: [crear uno nuevo](https://console.cloud.google.com/projectcreate) lleva 1 minuto; vincular facturación, 2 más. Hacelo **antes** de la sesión — es el único paso que no podemos acelerar en vivo.

---

## Qué vamos a construir

Tres agentes especializados que planifican una maratón entre los tres:

```
                        ┌──────────────────────┐
   tu pedido  ────────► │    planner_agent     │  thinking_budget=2048
                        │  (orquestador líder) │
                        └───┬──────────────┬───┘
            AgentTool       │              │      A2A / JSON-RPC
       (sub-agente local)   │              │      :8089
                        ┌───▼──────┐   ┌───▼──────────────────┐
                        │evaluator │   │ simulator_agent      │
                        │  agent   │   │ (server A2A propio)  │
                        │budget=1024│  │ thinking=0           │
                        │          │   │ checklist determin.  │
                        └───┬──────┘   └──────────────────────┘
                            │
                    Vertex AI Evaluation
                    7 métricas custom (MetricPromptBuilder)
                    + fallback heurístico
```

Modelo: `gemini-3.1-flash-lite` en los tres (elegible en el Paso 0.2). El codelab usa `gemini-3-flash-preview` + `gemini-3.1-pro-preview`: también funcionan, pero **solo en `location=global`** — con el `us-central1` del propio codelab dan 404.

### Por qué Colab y no local

| Problema del codelab | Acá |
|---|---|
| `gcloud auth application-default login` en la laptop | `auth.authenticate_user()`, una celda |
| Dos terminales de Cloud Shell | Dos procesos en la misma VM, `localhost` |
| `uv sync` en el wifi del evento | `pip install` en la VM de Google |
| La prueba final es un `curl` al agent card | Pedido real + **ADK Dev UI** con la traza + mapa de la ruta |

### Ruta del workshop

| Paso | Qué pasa | Tiempo |
|---|---|---|
| 0 | Setup: auth, proyecto, dependencias, repo | ~4 min |
| 1 | El Evaluator: 7 criterios y cómo puntúa | ~8 min |
| 2 | La ruta: Dijkstra sobre la red vial + mapa | ~8 min |
| 3 | Levantar los 3 agentes, conectarlos por A2A y abrir la **ADK Dev UI** | ~12 min |
| 4 | El pedido real end-to-end (~1 min de corrida) | ~10 min |
| 5 | Matar Vertex AI Eval en vivo (fallback híbrido) | ~5 min |

> 📦 Repo del workshop (tags por paso, `docs/GOTCHAS.md`, `docs/WORKSHOP.md`): ''' + REPO_URL + r'''
''')

# ---------------------------------------------------------------------------
# Paso 0
# ---------------------------------------------------------------------------
md(r'''
---
## Paso 0 — Setup

Tres celdas: dependencias, autenticación, código. La primera tarda ~2 minutos (baja ADK, el SDK de Vertex AI y a2a-sdk); arrancala y seguí explicando la arquitectura mientras corre.
''')

code(r'''
# @title Paso 0.1 — Instalar dependencias (~2 min) { display-mode: "form" }
# Las mismas versiones del pyproject.toml del repo, CON techo de major.
#
# El codelab declara solo pisos (>=). Hoy eso resuelve a google-adk 2.x,
# a2a-sdk 1.x y aiplatform 2.x, donde `a2a.server.apps` ya no existe y los
# servidores A2A no se pueden ni construir. Los techos son lo que hace que
# este notebook funcione. Ver docs/GOTCHAS.md #10 en el repo.

%pip install -q \
    "google-cloud-aiplatform[agent_engines,adk,evaluation]>=1.121.0,<2" \
    "google-adk>=1.25.0,<2" \
    "a2a-sdk>=0.3.9,<1" \
    "pydantic>=2.12.0" \
    "python-dotenv>=1.0.0" \
    "httpx>=0.27.0" \
    "uvicorn>=0.30.0" \
    "google-auth>=2.0.0" \
    "pandas>=2.0.0" \
    folium

import importlib.metadata as md

print("Instalado:")
for pkg, esperado in (("google-adk", "1."), ("a2a-sdk", "0."), ("google-cloud-aiplatform", "1."), ("pydantic", "2.")):
    try:
        v = md.version(pkg)
        ok = "✓" if v.startswith(esperado) else "✗ MAJOR INCORRECTO"
        print(f"  {ok} {pkg:28s} {v}")
    except md.PackageNotFoundError:
        print(f"  ✗ {pkg:28s} NO INSTALADO")

# El simbolo que desaparece en a2a-sdk 1.x: si esto importa, estamos en la linea correcta.
try:
    from a2a.server.apps import A2AStarletteApplication  # noqa: F401
    print("\n✓ a2a.server.apps importa — versiones compatibles con el codelab")
except ModuleNotFoundError:
    print("\n✗ a2a.server.apps NO existe — quedó instalado a2a-sdk 1.x. Reiniciá el runtime y volvé a correr esta celda.")

print("\n⚠️  Si Colab pide reiniciar el runtime, reinicialo y volvé a correr SOLO esta celda.")
''')

code(r'''
# @title Paso 0.2 — Autenticación, proyecto y modelos { display-mode: "form" }
# Completá tu project id. El popup de Google te va a pedir permiso: aceptá.

PROJECT_ID = ""  # @param {type:"string"}
LOCATION = "global"  # @param ["global", "us-central1"]
MODEL = "gemini-3.1-flash-lite"  # @param ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3-flash-preview"]

import os

assert PROJECT_ID, "Poné tu GOOGLE_CLOUD_PROJECT arriba y volvé a correr la celda."

from google.colab import auth
auth.authenticate_user(project_id=PROJECT_ID)
print("✓ Credenciales listas (esto reemplaza al `gcloud auth application-default login`)")

# La única API que hace falta.
!gcloud config set project {PROJECT_ID} 2>/dev/null
!gcloud services enable aiplatform.googleapis.com 2>&1 | tail -1

os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
# Un solo modelo flash para los tres agentes: barato, rápido, y la corrida
# completa tarda ~1 minuto. El codelab usa gemini-3-flash-preview +
# gemini-3.1-pro-preview; también existen, pero SOLO en location=global.
for var in ("PLANNER_MODEL", "EVALUATOR_MODEL", "SIMULATOR_MODEL"):
    os.environ[var] = MODEL

print(f"✓ Proyecto: {PROJECT_ID}  ·  región: {LOCATION}  ·  modelo: {MODEL}")

# Chequeo real: ¿responde el modelo en esta región?
# TRAMPA DEL CODELAB: pone GOOGLE_CLOUD_LOCATION=us-central1 y ahí TODOS los
# Gemini 3.x devuelven 404. Viven en `global`. Verificado 2026-09-21.
from google import genai

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
try:
    r = client.models.generate_content(model=MODEL, contents="Respondé solo: ok")
    print(f"  ✓ {MODEL} responde en {LOCATION}: {r.text.strip()[:30]!r}")
except Exception as e:
    msg = str(e)
    print(f"  ✗ {MODEL} en {LOCATION}\n      {msg[:200]}")
    if "billing" in msg.lower() or msg.startswith("403"):
        print("      → Casi seguro el proyecto no tiene facturación habilitada. Ver la tabla 'Antes de empezar'.")
    else:
        print("      → probá LOCATION='global' o MODEL='gemini-2.5-flash' (ese existe en us-central1).")
''')

code(r'''
# @title Paso 0.3 — Traer el código y correr el preflight { display-mode: "form" }

REPO_URL = "''' + REPO_URL + r'''.git"  # @param {type:"string"}
BRANCH = "main"  # @param {type:"string"}

import os, subprocess, sys

REPO_DIR = "/content/marathon-agents"

if not REPO_URL:
    raise SystemExit("Falta REPO_URL: pegá arriba la URL del repo del workshop.")

if not os.path.isdir(REPO_DIR):
    !git clone --branch {BRANCH} --depth 1 {REPO_URL} {REPO_DIR}
else:
    # Si ya existe, ACTUALIZARLO. Saltear esto es una trampa silenciosa: seguís
    # corriendo el código de la primera vez que clonaste y no hay ninguna señal.
    # fetch + reset (no pull): la historia del repo puede haber sido reescrita.
    print(f"{REPO_DIR} ya existe → actualizando a origin/{BRANCH}")
    !cd {REPO_DIR} && git fetch --tags --force origin && git reset --hard origin/{BRANCH}

assert os.path.isdir(REPO_DIR), "El clone falló. Revisá la URL y que el repo sea público."

os.chdir(REPO_DIR)
sys.path.insert(0, REPO_DIR)

# El .env que leen todos los agentes (misma config que os.environ de la celda 0.2).
with open(".env", "w") as f:
    for var in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "GOOGLE_GENAI_USE_VERTEXAI",
                "PLANNER_MODEL", "EVALUATOR_MODEL", "SIMULATOR_MODEL"):
        f.write(f"{var}={os.environ[var]}\n")
print("✓ .env escrito:\n")
!cat .env
print()

# Qué versión del código estás corriendo, para que nunca sea una sorpresa.
print("Commit:")
!git log --oneline -1
print()

# Si ya importaste los módulos del repo (celdas 1.x) ANTES de actualizar, Python
# tiene la versión vieja en memoria: reiniciá la sesión y volvé a correr.
import sys
if any(m.startswith("src.") for m in sys.modules):
    print("⚠️  Ya habías importado módulos del repo en esta sesión.")
    print("   Si el commit de arriba cambió: Entorno de ejecución → Reiniciar sesión,")
    print("   y volvé a correr desde la celda 0.1.\n")

# Un tag de git por paso del codelab: si alguien se queda atrás, salta acá.
!git tag -l

# Preflight: falla acá y no adelante de la sala.
!python scripts/preflight.py
''')

md(r"""
### 0.4 — Reparación: ¿estoy corriendo el código viejo?

Si ya habías corrido este notebook antes de una actualización del repo, en disco
tenés el código de la primera vez **y** en memoria los módulos ya importados.
Esta celda arregla las dos cosas de una, sin reiniciar la sesión. Es idempotente:
corrila las veces que quieras.
""")

code(r"""
# @title 0.4 — Actualizar el repo y purgar los módulos cacheados { display-mode: "form" }

import os, sys, subprocess

REPO_DIR = "/content/marathon-agents"

antes = subprocess.run(["git", "-C", REPO_DIR, "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True).stdout.strip()

# fetch + reset, NO pull: la historia del repo puede haber sido reescrita.
!cd {REPO_DIR} && git fetch --tags --force origin && git reset --hard origin/main

despues = subprocess.run(["git", "-C", REPO_DIR, "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()

# Actualizar archivos no sirve de nada si Python ya tiene el módulo cacheado:
# sacarlos de sys.modules hace que el próximo import lea el código nuevo.
purgados = [m for m in list(sys.modules) if m == "src" or m.startswith("src.")]
for m in purgados:
    del sys.modules[m]

os.chdir(REPO_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

print(f"\ncommit: {antes} → {despues}" + ("  (sin cambios)" if antes == despues else "  ✓ ACTUALIZADO"))
print(f"módulos purgados de la memoria: {len(purgados)}" + (f" → {', '.join(sorted(purgados)[:4])}..." if purgados else ""))
if antes != despues:
    print("\nVolvé a correr las celdas 1.x en adelante: ahora usan el código nuevo.")
    print("Si alguna sigue rara, Entorno de ejecución → Reiniciar sesión y empezá desde 0.1.")
""")

# ---------------------------------------------------------------------------
# Paso 1 — Evaluator
# ---------------------------------------------------------------------------
md(r'''
---
## Paso 1 — El Evaluator: el juez del sistema

El Evaluator es el agente más interesante del sistema y conviene entenderlo **antes** de levantar nada.

Su trabajo: puntuar un plan de maratón en **7 criterios**. Pero no lo hace "preguntándole a Gemini si el plan está bueno". Usa **Vertex AI Evaluation** con métricas custom construidas con `MetricPromptBuilder`, que es un patrón distinto:

```python
builder = types.MetricPromptBuilder(
    metric_definition="Evaluar si la ruta mantiene acceso de emergencia...",
    criteria={
        "Emergency corridor access": "La ruta no bloquea hospitales sin desvío documentado.",
        "Evacuation routes":        "Las rutas de evacuación siguen accesibles.",
    },
    rating_scores={
        "1":   "Peligroso - corredores bloqueados sin desvíos",
        "50":  "Preocupante - algunos accesos comprometidos",
        "100": "Seguro - acceso de emergencia mantenido",
    },
)
```

Tres cosas que esto te da y un prompt suelto no:

1. **La rúbrica es explícita.** El juez no inventa la escala: 1, 25, 50, 75, 100 tienen definición.
2. **Es auditable.** Cada score viene con su `explanation`. Podés mostrarle a un cliente por qué su plan sacó 42.
3. **Es comparable entre corridas.** La misma rúbrica hoy y en tres meses.

Y una métrica de las 7 **no usa LLM en absoluto**: `distance_compliance` es una regex que busca 26.2 millas. Si el plan dice 24 millas, el score es 1 y no hay modelo que lo salve. Mezclar juez-LLM con checks determinísticos es la idea de fondo del diseño.
''')

code(r'''
# @title 1.1 — Los 7 criterios y sus pesos { display-mode: "form" }
# Nada de red todavía: esto es leer la config del Evaluator.

from src.planner_agent.evaluator.config import (
    CRITERION_WEIGHTS, SEVERITY_THRESHOLDS, MODEL as EVALUATOR_MODEL,
)

print(f"Modelo juez: {EVALUATOR_MODEL}\n")
print(f"{'criterio':28s} {'peso':>6s}")
print("-" * 55)
for criterio, peso in sorted(CRITERION_WEIGHTS.items(), key=lambda kv: -kv[1]):
    barra = "█" * int(peso * 100 / 2.5)
    print(f"{criterio:28s} {peso:>5.0%}   {barra}")
print("-" * 55)
print(f"{'TOTAL':28s} {sum(CRITERION_WEIGHTS.values()):>5.0%}\n")

print("Severidad por score:", SEVERITY_THRESHOLDS)
print("\nAprobación: overall_score >= 85  Y  cero hallazgos de severidad 'high'.")
print("Fijate que safety y logistics pesan 20% cada uno: 40% del score es")
print("'¿esto se puede correr sin que se muera nadie?'")
''')

md(r'''
### 1.2 — La aritmética del veredicto

El score final es un promedio ponderado, pero **el promedio no alcanza para aprobar**. Mirá esta regla en `_build_result`:

```python
overall_score = sum(scores[c] * w for c, w in CRITERION_WEIGHTS.items())
passed = overall_score >= 85.0 and not any(f["severity"] == "high" for f in findings)
```

Un plan puede sacar 92 de promedio y **no pasar** si un solo criterio cayó por debajo de 40. Eso es deliberado: en un evento con 30.000 personas, "excelente en todo salvo en seguridad" no es un aprobado, es un problema.

La celda siguiente lo demuestra sin gastar un token: fuerza dos escenarios y muestra el veredicto.
''')

code(r'''
# @title 1.2 — Un promedio alto NO alcanza (sin llamar a ningún modelo) { display-mode: "form" }

from src.planner_agent.evaluator.tools import _build_result

def veredicto(titulo, scores):
    r = _build_result(scores, {}, eval_method="demo")
    print(f"\n{titulo}")
    print(f"  overall_score : {r['overall_score']}")
    print(f"  passed        : {r['passed']}")
    for f in r["findings"]:
        print(f"    [{f['severity']:6s}] {f['criterion']}")
    return r

# Escenario A: todo bien.
veredicto("A) Plan sólido en todo", {c: 90.0 for c in CRITERION_WEIGHTS})

# Escenario B: casi todo excelente, pero seguridad colapsa.
scores_b = {c: 95.0 for c in CRITERION_WEIGHTS}
scores_b["safety_compliance"] = 30.0
veredicto("B) 95 en todo, 30 en seguridad", scores_b)

print("\n" + "=" * 60)
print("El escenario B saca un promedio altísimo y IGUAL no pasa.")
print("Un hallazgo 'high' es un veto, no un descuento.")
print("=" * 60)
''')

md(r'''
### 1.3 — Evaluación híbrida: el juez caro y el plan B

`evaluate_plan` tiene dos caminos:

```python
if project_id and eval_mode != "heuristic":
    try:
        scores, details = await _run_custom_eval(...)   # Vertex AI Eval, 7 métricas
        return _build_result(scores, details, "vertex_ai_eval")
    except Exception as e:
        logger.warning(f"Vertex AI Eval falló, uso heurísticas: {e}")

scores, details = _heuristic_eval(...)                  # keywords, instantáneo
return _build_result(scores, details, "heuristic")
```

Esto no es un parche defensivo: es una decisión de arquitectura. Siete métricas, seis con juez LLM. Si la API se cae, tenés dos opciones: que el sistema entero se caiga con ella, o que degrade a algo peor pero útil.

Corramos primero el camino barato para ver la forma de la respuesta, y recién después el caro.
''')

code(r'''
# @title 1.3 — Camino heurístico: instantáneo, cero tokens { display-mode: "form" }

import json, os

PLAN_FLOJO = "Vamos a hacer una maratón en Buenos Aires. Va a estar buena."

PLAN_COMPLETO = """
Maratón de Buenos Aires. Recorrido de 26.2 miles (42.195 km) con largada y
llegada en el Obelisco: Plaza de Mayo, Puerto Madero, Reserva Ecológica,
La Boca, San Telmo, Recoleta, Bosques de Palermo y Barrancas de Belgrano.
Water station cada 2.5 km, medical tent cada 5 km con ambulancia después del
km 30, chip timing en start line y finish line, emergency vehicle crossings
cada 2 miles con desvío señalizado alrededor del Hospital Argerich y el
Hospital Fernández. Cheer zones con community engagement en 4 barrios.
Budget de USD 2.74M con revenue de inscripciones, sponsors y expo.
Landmarks escénicos: Obelisco, Puente de la Mujer, Caminito, Floralis Genérica.
Post-race: medals, comida y recovery area en los Bosques de Palermo.
"""
os.environ["EVAL_MODE"] = "heuristic"   # fuerza el fallback
from src.planner_agent.evaluator.tools import evaluate_plan

for nombre, plan in [("PLAN FLOJO", PLAN_FLOJO), ("PLAN COMPLETO", PLAN_COMPLETO)]:
    r = await evaluate_plan(json.dumps({
        "user_intent": "Maratón escénica en Buenos Aires para 30.000 personas",
        "proposed_plan": plan,
    }))
    print(f"\n{'=' * 60}\n{nombre}  →  método: {r['eval_method']}")
    print(f"  overall_score: {r['overall_score']}   passed: {r['passed']}")
    for c, s in sorted(r["scores"].items(), key=lambda kv: kv[1]):
        print(f"    {c:28s} {s:6.1f}")
    if r["improvement_suggestions"]:
        print("  sugerencias:")
        for s in r["improvement_suggestions"][:3]:
            print(f"    · {s}")

print("\n→ Mismo código, mismo schema de salida. Solo cambia de dónde salen los números.")
''')

code(r'''
# @title 1.4 — Ahora el juez de verdad: Vertex AI Eval { display-mode: "form" }
# El mismo plan, puntuado por las 7 métricas reales: 6 con juez LLM y una
# determinística (la distancia, que es una regex). Con flash-lite tarda
# unos segundos; con el gemini-3.1-pro-preview del codelab, 1-3 minutos.
#
# Lo que tenés que mirar: que los scores sean DISTINTOS entre sí. Seis 50.0
# y un overall de 52.5 significa que los jueces fallaron y alguien los
# reemplazó por un 50 (el bug del codelab, docs/GOTCHAS.md #17 y #18).

import os, time, json

os.environ["EVAL_MODE"] = "auto"        # volvemos al camino Vertex AI Eval

t0 = time.time()
r = await evaluate_plan(json.dumps({
    "user_intent": "Maratón escénica en Buenos Aires para 30.000 personas",
    "proposed_plan": PLAN_COMPLETO,
}))
print(f"⏱  {time.time() - t0:.0f}s   método: {r['eval_method']}\n")

print(f"overall_score: {r['overall_score']}   passed: {r['passed']}")
print("-" * 70)
for c, s in sorted(r["scores"].items(), key=lambda kv: kv[1]):
    peso = CRITERION_WEIGHTS.get(c, 0)
    print(f"{c:28s} {s:6.1f}  × {peso:.0%}  = {s * peso:5.2f}")
print("-" * 70)

for f in r["findings"]:
    print(f"\n[{f['severity'].upper()}] {f['criterion']}")
    print(f"  {f['description'][:400]}")

if r["eval_method"] == "heuristic":
    print("\n⚠️  Cayó al fallback heurístico. Mirá el WARNING de arriba: puede ser")
    print("   cuota, región, o un juez que no devolvió JSON parseable.")
    print("   Para el workshop no es un drama: el sistema siguió respondiendo.")
    print("   Eso es exactamente el punto de la evaluación híbrida.")
else:
    distintos = len(set(r["scores"].values()))
    print(f"\n✓ {distintos} valores distintos entre 7 criterios.")
    if distintos <= 2:
        print("  ⚠️  Sospechoso: si ves seis 50.0, los jueces fallaron en silencio.")
''')

# ---------------------------------------------------------------------------
# Paso 2 — Ruta
# ---------------------------------------------------------------------------
md(r'''
---
## Paso 2 — La ruta: el ADK Skill que sí calcula

Acá hay una lección que no está en el codelab.

El instruction del Planner dice: *"Route Design: GeoJSON via `plan_marathon_route` tool"*. El `SKILL.md` de `route-planning` dice que `tools.py` contiene esa función. Y `get_tools()` la carga así:

```python
plan_marathon_route_func = load_tool_from_skill("route-planning", "plan_marathon_route")
if plan_marathon_route_func:
    tools.append(FunctionTool(func=plan_marathon_route_func))
```

**El codelab nunca crea ese `tools.py`.** `load_tool_from_skill` devuelve `None` cuando el archivo no existe, el `if` no se cumple, y la tool simplemente no se agrega — sin error, sin warning. El agente entonces *inventa* una ruta que suena bien y nadie se entera.

Es el bug más instructivo de todo el codelab: **una tool que falta en silencio no se ve como un error, se ve como una alucinación.** Cuando un agente invente datos, la primera pregunta no es "¿qué modelo uso?" sino "¿la tool está realmente cargada?".

En este repo el archivo existe: red vial por ciudad, Dijkstra, cierre de loop sobre los 42.195 km y GeoJSON de salida.
''')

code(r'''
# @title 2.1 — Calcular la ruta (Dijkstra, sin LLM) { display-mode: "form" }

CIUDAD = "Buenos Aires"  # @param ["Buenos Aires", "Las Vegas", "Austin", "Tokyo"]

import importlib.util

spec = importlib.util.spec_from_file_location(
    "route_tools", "/content/marathon-agents/src/planner_agent/skills/route-planning/tools.py"
)
route_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route_tools)

ruta = route_tools.plan_marathon_route(CIUDAD)

print(f"Ciudad            : {ruta['city']}   (red: {ruta['network_source']})")
print(f"Largada/llegada   : {ruta['start_finish']}")
print(f"Distancia red     : {ruta['raw_network_distance_km']} km")
print(f"Ajuste de medición: {ruta['course_adjustment_km']:+} km")
print(f"Distancia oficial : {ruta['total_distance_km']} km / {ruta['total_distance_miles']} mi")
print(f"Waypoints         : {len(ruta['waypoints'])} ({ruta['unique_landmarks']} únicos)\n")

print("Primeros tramos:")
print(f"{'desde':32s} {'hasta':32s} {'km':>6s}  {'tipo':10s} {'corte':>5s}")
print("-" * 92)
for seg, cierre in list(zip(ruta["segments"], ruta["road_closures"]))[:8]:
    print(f"{seg['from'][:30]:32s} {seg['to'][:30]:32s} {seg['distance_km']:6.2f}  "
          f"{seg['road_type']:10s} {cierre['closure_severity']:>5d}")

print(f"\nTramos que necesitan desvío: "
      f"{sum(1 for c in ruta['road_closures'] if c['detour_required'])} de {len(ruta['road_closures'])}")
print("\n→ Esto es un número calculado, no una estimación de un modelo.")
''')

code(r'''
# @title 2.2 — El GeoJSON en un mapa (acá se despierta la sala) { display-mode: "form" }

import folium

coords = ruta["route_geojson"]["features"][0]["geometry"]["coordinates"]  # [lon, lat]
latlon = [[c[1], c[0]] for c in coords]

# Esri World Street Map: sin API key y sin bloqueo desde Colab.
# (OpenStreetMap devuelve 403 desde Colab por politica de uso; CartoDB pide key.)
m = folium.Map(
    location=latlon[0], zoom_start=13,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri",
)

folium.PolyLine(latlon, weight=6, opacity=0.85, color="#FF6B35",
                tooltip="26.2 mi / 42.195 km").add_to(m)

folium.Marker(latlon[0], tooltip=f"Largada / Llegada: {ruta['start_finish']}",
              icon=folium.Icon(color="green", icon="flag")).add_to(m)

# Un cartel por landmark único.
vistos = set()
for nombre in ruta["waypoints"]:
    if nombre in vistos:
        continue
    vistos.add(nombre)
    idx = ruta["waypoints"].index(nombre)
    folium.Marker(latlon[idx], tooltip=nombre, icon=folium.DivIcon(
        html=f'<div style="font:12px Arial;background:#fff;padding:2px 5px;'
             f'border-radius:3px;border:1px solid #999;white-space:nowrap">{nombre}</div>'
    )).add_to(m)

# Puestos de hidratación, ubicados proporcionalmente sobre el trazado.
agua = route_tools.add_water_stations(participants=30000)
for est in agua["stations"]:
    frac = est["km_mark"] / ruta["total_distance_km"]
    idx = min(int(frac * (len(latlon) - 1)), len(latlon) - 1)
    folium.CircleMarker(
        latlon[idx], radius=5, color="#0077B6", fill=True, fill_opacity=0.9,
        tooltip=f"{est['station_id']} · km {est['km_mark']} · {est['cups_required']:,} vasos",
    ).add_to(m)

m.fit_bounds(latlon)

print(f"{agua['water_station_count']} puestos de hidratación · "
      f"{agua['total_cups']:,} vasos · {agua['total_volunteers']} voluntarios")
med = route_tools.add_medical_tents(participants=30000)
print(f"{med['medical_tent_count']} puestos médicos · {med['total_medical_staff']} personas · "
      f"{med['ambulances']} ambulancias")
m
''')

# ---------------------------------------------------------------------------
# Paso 3 — A2A
# ---------------------------------------------------------------------------
md(r'''
---
## Paso 3 — Los tres agentes y el protocolo A2A

Hasta acá corrimos piezas sueltas. Ahora las conectamos.

El Planner arma sus tools con **tres patrones distintos**, y esa es la clase entera:

| Patrón | Qué conecta | Dónde corre |
|---|---|---|
| `SkillToolset` | conocimiento procedural (`SKILL.md` + referencias) | en el proceso |
| `AgentTool(agent=evaluator_agent)` | el Evaluator como sub-agente | en el proceso |
| `RemoteA2aAgent(agent_card=...)` | el Simulator | **otro proceso, por HTTP** |

El tercero es el interesante. El Simulator no es un import: es un servidor con su propia **agent card** en `/.well-known/agent-card.json`, al que el Planner le habla por JSON-RPC. Podría estar en otra máquina, en Cloud Run o en Agent Engine y el código del Planner no cambia una línea.

Y la bisagra entre los dos modos es **una variable de entorno**:

```python
if os.environ.get("SIMULATOR_AGENT_RESOURCE_NAME"):
    tools.append(create_simulation_controller_tool())   # Full Team
# sin la variable: Solo mode, Planner + Evaluator nomás
```

- `local:8089` → servidor local
- `projects/.../reasoningEngines/123` → Agent Engine en producción

**Mismo binario, misma imagen, distinta topología.** El olvido más común del workshop es reiniciar el Planner sin esa variable y no entender por qué el Simulator nunca contesta: el banner de arranque te dice `SOLO` o `FULL TEAM` justamente por eso.
''')

code(r'''
# @title 3.1 — Levantar el Simulation Controller (:8089) { display-mode: "form" }
# En el codelab esto es una segunda pestaña de Cloud Shell. Acá es un proceso más.

import os, socket, subprocess, time

REPO_DIR = "/content/marathon-agents"
LOGS = "/content/logs"
os.makedirs(LOGS, exist_ok=True)

def puerto_vivo(port, timeout=0.4):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex(("127.0.0.1", port)) == 0

def esperar_puerto(port, nombre, log_path, segundos=90):
    for i in range(segundos):
        if puerto_vivo(port):
            print(f"✓ {nombre} escuchando en :{port}  ({i}s)")
            return True
        time.sleep(1)
    print(f"✗ {nombre} no levantó en {segundos}s. Últimas líneas del log:\n")
    print(open(log_path).read()[-2500:])
    return False

env = {**os.environ, "PYTHONUNBUFFERED": "1"}
sim_log = f"{LOGS}/simulator.log"

simulador = subprocess.Popen(
    ["python", "-m", "src.simulator_agent.runtime.local_server"],
    cwd=REPO_DIR, env=env,
    stdout=open(sim_log, "w"), stderr=subprocess.STDOUT,
)
print(f"Simulator arrancando (pid {simulador.pid})...")
esperar_puerto(8089, "Simulator", sim_log)
''')

code(r'''
# @title 3.2 — La agent card del Simulator: lo que el Planner va a leer { display-mode: "form" }
# Antes de conectar nada, mirá qué publica el agente sobre sí mismo.

import json, httpx

card = httpx.get("http://127.0.0.1:8089/.well-known/agent-card.json", timeout=10).json()

print(json.dumps(card, indent=2)[:1200])
print("\n" + "=" * 60)
print("Ojo con la ruta: es /.well-known/agent-card.json")
print("El codelab imprime /.well-known/agent.json, que da 404 y te hace")
print("pensar que A2A no anda. Es solo el print, no el protocolo.")
print("=" * 60)
''')

code(r'''
# @title 3.3 — Levantar el Planner en modo FULL TEAM (:8084) { display-mode: "form" }
# La variable de entorno es TODA la diferencia entre Solo y Full Team.

MODO = "FULL TEAM (Planner + Evaluator + Simulator)"  # @param ["FULL TEAM (Planner + Evaluator + Simulator)", "SOLO (Planner + Evaluator)"]

planner_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
if MODO.startswith("FULL"):
    planner_env["SIMULATOR_AGENT_RESOURCE_NAME"] = "local:8089"
else:
    planner_env.pop("SIMULATOR_AGENT_RESOURCE_NAME", None)

plan_log = f"{LOGS}/planner.log"

planner = subprocess.Popen(
    ["python", "-m", "src.planner_agent.runtime.local_server"],
    cwd=REPO_DIR, env=planner_env,
    stdout=open(plan_log, "w"), stderr=subprocess.STDOUT,
)
print(f"Planner arrancando (pid {planner.pid})...")
esperar_puerto(8084, "Planner", plan_log)

print("\n--- arranque del Planner ---")
log = open(plan_log).read()
for linea in log.splitlines():
    if any(k in linea for k in ("Mode:", "Executor:", "Agent:", "Tools:", "Added ", "  - ")):
        print(" ", linea.rstrip())

print("\n" + "=" * 60)
if "Added A2A Simulation Controller tool" in log:
    print("✓ Las DOS tools cargaron: Evaluator local + Simulator por A2A.")
else:
    print("· Solo el Evaluator. Sin SIMULATOR_AGENT_RESOURCE_NAME no hay tercer agente.")
print("=" * 60)
''')

code(r"""
# @title 3.4 — La UI: ADK Dev UI dentro de Colab { display-mode: "form" }
# `adk web` es la interfaz de desarrollo de ADK: un chat con el agente y, al
# lado, la traza de cada tool call, del sub-agente Evaluator y del salto A2A al
# Simulator. El codelab no la menciona. Corre en la VM y Colab la proxea.
#
# La URL NO es fija: Colab firma un subdominio por sesion y por usuario
# (https://8000-m-s-<hash>.<region>.prod.colab.dev). Por eso hay que pedirla en
# runtime con google.colab.kernel.proxyPort(8000). Copiarla de un tutorial no
# funciona nunca.

import os, shutil, subprocess, sys, time
import httpx
from google.colab import output
from google.colab.output import eval_js
from IPython.display import HTML, display

ADK_PORT = 8000
UI_PATH = "/dev-ui/?app=planner_agent"

adk_env = {**os.environ, "SIMULATOR_AGENT_RESOURCE_NAME": "local:8089", "PYTHONUNBUFFERED": "1"}
# --host 0.0.0.0: escucha en todas las interfaces de la VM, no solo en loopback.
adk_bin = shutil.which("adk")
adk_cmd = ([adk_bin] if adk_bin else [sys.executable, "-m", "google.adk.cli"]) + \
          ["web", "--host", "0.0.0.0", "--port", str(ADK_PORT), "src"]

adkweb = subprocess.Popen(
    adk_cmd, cwd=REPO_DIR, env=adk_env,
    stdout=open(f"{LOGS}/adkweb.log", "w"), stderr=subprocess.STDOUT,
)
print(f"ADK Dev UI arrancando (pid {adkweb.pid}):\n  {' '.join(adk_cmd)}\n")

if not esperar_puerto(ADK_PORT, "ADK Dev UI", f"{LOGS}/adkweb.log", segundos=120):
    raise SystemExit("adk web no levantó. Mirá el log de arriba.")

# Health check DESDE la VM antes de dar la URL: si esto responde, el servidor
# está bien y cualquier problema posterior es del proxy o de la cuenta.
apps = httpx.get(f"http://127.0.0.1:{ADK_PORT}/list-apps", timeout=10).json()
print(f"✓ el servidor responde en :{ADK_PORT} y ve los agentes: {apps}")

# URL de ESTA sesión.
base = eval_js(f"google.colab.kernel.proxyPort({ADK_PORT})").rstrip("/")
url = base + UI_PATH
print("\nCómo se arma la URL de esta sesión (no la anotes, pedila):")
print(f"  base = google.colab.kernel.proxyPort({ADK_PORT})")
print(f"       = {base}")
print(f"  url  = base + '{UI_PATH}'")
print(f"\n  {url}\n")
print("(esa URL sirve para entender el mecanismo; para USAR la UI, mirá el iframe de abajo)")

# IMPORTANTE: abrir en PESTAÑA NUEVA no funciona. El HTML carga, pero el proxy
# de Colab devuelve 403 en los chunks de JavaScript (las sub-peticiones no
# llevan la autenticación de la sesión) y ves una página en blanco con cuatro
# errores 403 en la consola. Es la razón por la que serve_kernel_port_as_window
# está deprecada. El iframe corre dentro del contexto autenticado del notebook
# y sí carga. Ver docs/GOTCHAS.md #21.
print("\nLa UI, acá abajo (agente `planner_agent` → escribí el pedido → panel Events):")
output.serve_kernel_port_as_iframe(ADK_PORT, path=UI_PATH, height="700")
""")

# ---------------------------------------------------------------------------
# Paso 4 — Pedido real
# ---------------------------------------------------------------------------
md(r'''
---
## Paso 4 — El pedido real

Acá está el otro agujero del codelab: su paso final "Deploy and test the multi-agent system" **nunca manda un mensaje**. La única verificación es un `curl` a la agent card. O sea: comprobás que el servidor arrancó, no que los tres agentes colaboran.

Lo que sigue es un `message/send` de A2A de verdad. La secuencia que vas a ver (verificada — en la corrida de ensayo fueron **17 eventos en 57 segundos**):

1. `list_skills` → `load_skill` ×2 — el Planner descubre y carga sus Skills.
2. `plan_marathon_route` → waypoints y GeoJSON reales (Dijkstra, no el modelo).
3. `add_water_stations`, `add_medical_tents` — logística con números calculados.
4. Redacta el plan completo (tráfico, comunidad, economía, timeline, riesgos).
5. `evaluator_agent` — sub-agente **en proceso** (`AgentTool`): 7 métricas en Vertex AI Evaluation.
6. `simulator_agent` — agente **remoto** (`RemoteA2aAgent`, HTTP al `:8089`): veredicto de readiness.
7. Devuelve el plan con scores y veredicto.

Con `gemini-3.1-flash-lite` tarda **alrededor de 1 minuto**. Si usás el `gemini-3.1-pro-preview` del codelab como juez, contá 2-5. El silencio largo siempre es el Evaluator: no es que se colgó.

> Truco para la sala: la celda 4.2 muestra la traza etiquetada de qué hizo cada agente. Corrala en cuanto termine esta.
''')

code(r'''
# @title 4.1 — Mandar el pedido end-to-end (~1 min) { display-mode: "form" }

CIUDAD_PEDIDO = "Buenos Aires"  # @param {type:"string"}
PARTICIPANTES = 30000  # @param {type:"integer"}
TEMA = "scenic"  # @param ["scenic", "fast", "charity"]

import subprocess, sys, time

t0 = time.time()
proc = subprocess.Popen(
    [sys.executable, "scripts/send_request.py",
     "--city", CIUDAD_PEDIDO,
     "--participants", str(PARTICIPANTES),
     "--theme", TEMA,
     "--watch", "--timeout", "900"],
    cwd=REPO_DIR, env=planner_env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
)
for linea in proc.stdout:
    print(linea, end="")
proc.wait()
print(f"\n⏱  {time.time() - t0:.0f}s   exit={proc.returncode}")
''')

code(r'''
# @title 4.2 — Qué pasó por dentro: la traza de los tres agentes { display-mode: "form" }
# Corré esto DESPUÉS (o en paralelo, en otra pestaña) para mostrar la coreografía.

import re

log = open(f"{LOGS}/planner.log").read()

interesantes = [
    ("TOOL",   r"plan_marathon_route|add_water_stations|add_medical_tents|load_skill|list_skills"),
    ("EVAL",   r"evaluate_plan|vertex_ai_eval|_evals_common|heuristic|evaluator_agent"),
    ("A2A",    r"agent-card|simulator_agent|Overriding agent card|a2a"),
    ("ERROR",  r"ERROR|Traceback"),
]

for linea in log.splitlines():
    for etiqueta, patron in interesantes:
        if re.search(patron, linea, re.I):
            print(f"[{etiqueta:5s}] {linea.strip()[:150]}")
            break

print("\n--- log del Simulator ---")
sim = open(f"{LOGS}/simulator.log").read()
for linea in sim.splitlines()[-25:]:
    if linea.strip():
        print(" ", linea.strip()[:150])
''')

md(r"""
### 4.3 — La coreografía completa, evento por evento

Las celdas anteriores te dieron el resultado y el log. Esta te da **la película**: manda el pedido por la API de `adk web` y dibuja cada evento en orden, con quién lo originó y cuánto tardó.

Es la vista que cierra el workshop, porque hace visible lo único que no se ve en el texto final: que hubo **tres agentes distintos**, que el Evaluator corrió *dentro* del proceso del Planner y que el Simulator contestó *por HTTP*. En la salida vas a poder señalar con el dedo el momento exacto en que el Planner deja de trabajar y delega.

> Necesita la celda 3.4 corrida (la UI levantada en el :8000).
""")

code(r"""
# @title 4.3 — La coreografía completa, evento por evento { display-mode: "form" }

import json, time
import httpx
from IPython.display import HTML, display

PEDIDO = "Plan a scenic marathon in Buenos Aires for 30,000 runners. Send it to the evaluator and then to the simulation controller, and report the scores and the verdict."  # @param {type:"string"}

BASE = f"http://127.0.0.1:{ADK_PORT}"
sid = httpx.post(f"{BASE}/apps/planner_agent/users/user/sessions", json={}, timeout=30).json()["id"]
print(f"session: {sid}\nmandando el pedido... (~1 min)\n")

COLOR = {"planner_agent": "#FF6B35", "evaluator_agent": "#0077B6", "simulator_agent": "#2A9D8F"}
DONDE = {
    "list_skills": ("Skill", "en proceso"), "load_skill": ("Skill", "en proceso"),
    "plan_marathon_route": ("Tool", "en proceso · Dijkstra, sin LLM"),
    "add_water_stations": ("Tool", "en proceso · calculado"),
    "add_medical_tents": ("Tool", "en proceso · calculado"),
    "evaluator_agent": ("AgentTool", "MISMO proceso · 6 jueces LLM + 1 regex"),
    "simulator_agent": ("RemoteA2aAgent", "OTRO proceso · HTTP al :8089"),
}

filas, t0, final = [], time.time(), ""
with httpx.stream("POST", f"{BASE}/run_sse", timeout=900, json={
    "app_name": "planner_agent", "user_id": "user", "session_id": sid,
    "new_message": {"role": "user", "parts": [{"text": PEDIDO}]}, "streaming": False,
}) as resp:
    for linea in resp.iter_lines():
        if not linea.startswith("data:"):
            continue
        ev = json.loads(linea[5:])
        t = time.time() - t0
        for parte in (ev.get("content") or {}).get("parts", []):
            if "functionCall" in parte:
                n = parte["functionCall"]["name"]
                tipo, donde = DONDE.get(n, ("Tool", ""))
                filas.append((t, ev.get("author", "?"), "llama", n, tipo, donde))
                print(f"  [{t:5.1f}s] → {n}")
            elif "functionResponse" in parte:
                n = parte["functionResponse"]["name"]
                filas.append((t, ev.get("author", "?"), "responde", n, "", ""))
            elif parte.get("text"):
                final = parte["text"]
                filas.append((t, ev.get("author", "?"), "responde al usuario", "", "", f"{len(final)} caracteres"))

total = time.time() - t0
print(f"\n{len(filas)} eventos en {total:.0f}s\n")

html = ['<div style="font-family:system-ui;max-width:900px">',
        f'<h3 style="margin:0 0 4px">Una corrida completa · {len(filas)} eventos · {total:.0f}s</h3>',
        '<table style="border-collapse:collapse;width:100%;font-size:13px">']
for t, autor, verbo, nombre, tipo, donde in filas:
    c = COLOR.get(autor, "#888")
    destacar = "font-weight:700" if tipo in ("AgentTool", "RemoteA2aAgent") else ""
    html.append(
        f'<tr style="border-bottom:1px solid #eee">'
        f'<td style="padding:6px 10px;color:#999;white-space:nowrap">{t:5.1f}s</td>'
        f'<td style="padding:6px 10px"><span style="background:{c};color:#fff;padding:2px 8px;'
        f'border-radius:10px;white-space:nowrap">{autor}</span></td>'
        f'<td style="padding:6px 10px;color:#666">{verbo}</td>'
        f'<td style="padding:6px 10px;{destacar}">{nombre}</td>'
        f'<td style="padding:6px 10px;color:#666">{tipo}</td>'
        f'<td style="padding:6px 10px;color:#888">{donde}</td></tr>')
html.append('</table><p style="color:#666;font-size:13px;margin-top:10px">'
            'Las dos filas en negrita son la clase entera: <b>evaluator_agent</b> corre dentro de este '
            'mismo proceso (AgentTool) y <b>simulator_agent</b> vive en otro, alcanzado por A2A sobre '
            'HTTP. El Planner los llama igual: no sabe dónde están.</p></div>')
display(HTML("".join(html)))

print("=" * 70)
print("PLAN FINAL")
print("=" * 70)
print(final)
""")

# ---------------------------------------------------------------------------
# Paso 5 — Romperlo
# ---------------------------------------------------------------------------
md(r'''
---
## Paso 5 — Romperlo a propósito

Un sistema multiagente que solo mostrás cuando funciona no enseña nada. Los dos experimentos que dejan la clase:

**A. Matar el juez.** Reiniciamos el Planner con `EVAL_MODE=heuristic`. Vertex AI Eval deja de usarse por completo y el sistema **sigue contestando**, más rápido y peor. La evaluación híbrida deja de ser un bullet de slide y pasa a ser un comportamiento que la sala vio.

**B. Apagar el tercer agente.** Matamos el Simulator y mandamos el mismo pedido. El Planner intenta el A2A, falla y tiene que arreglárselas. Acá se ve la diferencia real entre un sub-agente en proceso (`AgentTool`, no puede fallar por red) y uno remoto (`RemoteA2aAgent`, sí puede) — que es exactamente la clase de falla que tenés en producción y no en tu notebook.

Corré A, B o los dos según cómo venga el tiempo.
''')

code(r'''
# @title 5.A — Sin el juez LLM: reiniciar con EVAL_MODE=heuristic { display-mode: "form" }

import signal, time

def frenar(proc, nombre):
    if proc and proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"· {nombre} detenido")

frenar(planner, "Planner")
time.sleep(2)

planner_env["EVAL_MODE"] = "heuristic"
plan_log = f"{LOGS}/planner_heuristic.log"
planner = subprocess.Popen(
    ["python", "-m", "src.planner_agent.runtime.local_server"],
    cwd=REPO_DIR, env=planner_env,
    stdout=open(plan_log, "w"), stderr=subprocess.STDOUT,
)
esperar_puerto(8084, "Planner (heurístico)", plan_log)

t0 = time.time()
proc = subprocess.Popen(
    [sys.executable, "scripts/send_request.py", "--city", CIUDAD_PEDIDO,
     "--participants", str(PARTICIPANTES), "--theme", TEMA, "--watch", "--timeout", "600"],
    cwd=REPO_DIR, env=planner_env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
)
for linea in proc.stdout:
    print(linea, end="")
proc.wait()

print(f"\n⏱  {time.time() - t0:.0f}s  —  compará con la corrida con juez LLM.")
print("Mismo sistema, misma interfaz, sin una sola llamada al evaluador LLM.")
''')

code(r'''
# @title 5.B — Apagar el Simulator y ver qué hace el Planner { display-mode: "form" }

frenar(simulador, "Simulator")
time.sleep(1)
print(f"Puerto 8089 vivo: {puerto_vivo(8089)}  (debería ser False)\n")

t0 = time.time()
proc = subprocess.Popen(
    [sys.executable, "scripts/send_request.py", "--city", CIUDAD_PEDIDO,
     "--participants", str(PARTICIPANTES), "--theme", TEMA, "--watch", "--timeout", "600"],
    cwd=REPO_DIR, env=planner_env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
)
for linea in proc.stdout:
    print(linea, end="")
proc.wait()
print(f"\n⏱  {time.time() - t0:.0f}s")

print("\n" + "=" * 60)
print("Preguntale a la sala: ¿entregó un plan igual, avisó que le faltó el")
print("veredicto de simulación, o falló entero? Las tres son respuestas")
print("posibles y ninguna está en el código: está en el instruction del")
print("Planner. Ahí se ve por qué el prompt de un orquestador es diseño de")
print("sistema, no redacción.")
print("=" * 60)
''')

# ---------------------------------------------------------------------------
# Cierre
# ---------------------------------------------------------------------------
md(r'''
---
## Cierre

Lo que quedó construido:

- **ADK**: `LlmAgent` con `static_instruction`, salida estructurada con Pydantic y `ThinkingConfig` calibrado por tarea — 2048 para planificar, 1024 para juzgar, **0** para un checklist. El presupuesto de razonamiento es una decisión de diseño, no un default.
- **Vertex AI Evaluation**: 7 métricas propias con `MetricPromptBuilder`, seis con juez LLM y una determinística, con rúbricas explícitas y fallback heurístico.
- **A2A**: un agente remoto que se descubre por su agent card y se enchufa con una variable de entorno.
- **ADK Skills**: conocimiento procedural en archivos, no en el prompt.

### Lo que NO quedó demostrado (decilo en voz alta)

**Memory Bank no está funcionando.** `VertexAiMemoryBankService` necesita un Agent Engine; sin `AGENT_ENGINE_ID` el `auto_save_memories` corta al primer `if` y todo corre en `InMemorySessionService`. El código está listo para producción, pero acá no persistió nada. Presentalo como "esta es la línea que cambiás al desplegar", nunca como una feature andando.

### Para seguir

| Recurso | Dónde |
|---|---|
| Codelab original | [Build a Multi-Agent Marathon Planner](https://codelabs.developers.google.com/next26/dev-keynote/build-multi-agent-marathon-planner) |
| Repo del workshop | ''' + REPO_URL + r''' — un tag de git por paso (`git tag -l`) |
| Trampas y desvíos | `docs/GOTCHAS.md` en el repo |
| Guion cronometrado (60 min) | `docs/WORKSHOP.md` |
| La implementación completa del keynote | [GoogleCloudPlatform/race-condition](https://github.com/GoogleCloudPlatform/race-condition) — frontend 3D con modo *cached* |

Corré la última celda antes de cerrar: si no, los dos servidores quedan vivos en la VM.
''')

code(r'''
# @title Limpieza — apagar los dos servidores { display-mode: "form" }

for proc, nombre in [(planner, "Planner"), (simulador, "Simulator"), (globals().get("adkweb"), "ADK Dev UI")]:
    frenar(proc, nombre)

!pkill -f "src.planner_agent.runtime.local_server" 2>/dev/null
!pkill -f "src.simulator_agent.runtime.local_server" 2>/dev/null
!pkill -f "adk.*web" 2>/dev/null

import time
time.sleep(1)
print(f"\nPuerto 8084 vivo: {puerto_vivo(8084)}")
print(f"Puerto 8000 vivo: {puerto_vivo(8000)}")
print(f"Puerto 8089 vivo: {puerto_vivo(8089)}")
print("\nNo hay nada más que borrar: este workshop no crea recursos persistentes")
print("en Google Cloud (ni Cloud Run, ni Agent Engine). Solo llamadas a la API.")
print("La VM de Colab se libera sola cuando cerrás la sesión.")
''')


# ---------------------------------------------------------------------------
# Emit nbformat v4
# ---------------------------------------------------------------------------
def to_lines(src: str) -> list[str]:
    lines = src.split("\n")
    return [l + "\n" for l in lines[:-1]] + [lines[-1]]


nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True, "name": "marathon_agents_workshop.ipynb"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "cells": [],
}
for kind, src in cells:
    cell = {
        "cell_type": kind,
        "id": uuid.uuid4().hex[:12],
        "metadata": {},
        "source": to_lines(src),
    }
    if kind == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
        if src.startswith("# @title"):
            cell["metadata"]["cellView"] = "form"
    nb["cells"].append(cell)

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
n_code = sum(1 for k, _ in cells if k == "code")
print(f"wrote {OUT.name}: {len(cells)} cells ({n_code} code, {len(cells) - n_code} markdown)")
