"""Local A2A server for the Marathon Planner Agent.

Usage: uv run python -m src.planner_agent.runtime.local_server
"""

import os

from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

# El wiring de tools loguea en import-time, antes de que uvicorn instale su
# logging. Sin esto, las lineas "Added local Evaluator tool" / "Added A2A
# Simulation Controller tool" nunca llegan al log y no podes verificar el modo.
import logging  # noqa: E402
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(name)s: %(message)s",
)

import asyncio  # noqa: E402

import uvicorn  # noqa: E402
from a2a.server.apps import A2AStarletteApplication  # noqa: E402
from a2a.server.request_handlers import DefaultRequestHandler  # noqa: E402
from a2a.server.tasks import InMemoryTaskStore  # noqa: E402
from a2a.types import TransportProtocol  # noqa: E402

AGENT_PORT = int(os.environ.get("PLANNER_PORT", "8084"))

# DEVIATION FROM THE CODELAB (docs/GOTCHAS.md #3): the codelab writes
# MarathonPlannerExecutor and then never uses it - local_server.py builds ADK's
# generic A2aAgentExecutor with a legacy Runner signature, so the custom
# session/memory wiring is dead code. Here the custom executor is the default
# (symmetric with the simulator) and the ADK one is one env var away.
USE_ADK_EXECUTOR = os.environ.get("USE_ADK_EXECUTOR", "").lower() in ("1", "true", "yes")


def create_marathon_planner_server():
    from .agent_card import create_marathon_planner_card

    if USE_ADK_EXECUTOR:
        from google.adk import Runner
        from google.adk.a2a.executor.a2a_agent_executor import (
            A2aAgentExecutor,
            A2aAgentExecutorConfig,
        )
        from google.adk.sessions import InMemorySessionService

        from ..agent import root_agent

        runner = Runner(
            app_name=root_agent.name,
            agent=root_agent,
            session_service=InMemorySessionService(),
        )
        executor = A2aAgentExecutor(runner=runner, config=A2aAgentExecutorConfig())
    else:
        from .agent_executor import MarathonPlannerExecutor

        executor = MarathonPlannerExecutor()

    handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())

    card = create_marathon_planner_card()
    card.url = f"http://localhost:{AGENT_PORT}"
    card.preferred_transport = TransportProtocol.jsonrpc

    return A2AStarletteApplication(agent_card=card, http_handler=handler)


async def run_server():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT must be set. Check .env file.")

    simulator = os.environ.get("SIMULATOR_AGENT_RESOURCE_NAME")

    print("=" * 60)
    print("Starting Marathon Planner Agent Local A2A Server")
    print(f"Project:   {project}")
    print(f"Executor:  {'ADK A2aAgentExecutor' if USE_ADK_EXECUTOR else 'MarathonPlannerExecutor'}")
    print(f"Mode:      {'FULL TEAM -> ' + simulator if simulator else 'SOLO (Planner + Evaluator)'}")
    print("=" * 60)

    # Construir el agente ACA, no en el primer request: si algo del wiring esta
    # roto (una Skill que no resuelve, una tool que no carga, el A2A mal
    # configurado) queremos el traceback al arrancar y no en vivo.
    from ..agent import root_agent

    print(f"Agent:     {root_agent.name} ({root_agent.model})")
    print(f"Tools:     {len(root_agent.tools)}")
    for t in root_agent.tools:
        print(f"             - {getattr(t, 'name', type(t).__name__)}")
    print("=" * 60)

    app = create_marathon_planner_server()
    config = uvicorn.Config(app.build(), host="127.0.0.1", port=AGENT_PORT, log_level="info", loop="none")

    print(f"Planner A2A server: http://127.0.0.1:{AGENT_PORT}")
    print(f"Agent card: http://127.0.0.1:{AGENT_PORT}/.well-known/agent-card.json")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(run_server())
