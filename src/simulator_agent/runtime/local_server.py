"""Local A2A server for the Simulation Controller Agent.

Usage: uv run python -m src.simulator_agent.runtime.local_server
"""

import asyncio
import os

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

import uvicorn  # noqa: E402
from a2a.server.apps import A2AStarletteApplication  # noqa: E402
from a2a.server.request_handlers import DefaultRequestHandler  # noqa: E402
from a2a.server.tasks import InMemoryTaskStore  # noqa: E402
from a2a.types import TransportProtocol  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

AGENT_PORT = int(os.environ.get("SIMULATOR_PORT", "8089"))


async def run_server():
    from .agent_card import create_simulation_controller_card
    from .agent_executor import SimulationControllerExecutor

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT must be set.")

    print("=" * 60)
    print("Starting Simulation Controller Agent Local A2A Server")
    print(f"Project: {project}")
    print("=" * 60)

    agent_card = create_simulation_controller_card()
    # The planner resolves this card over A2A - the URL it advertises has to be
    # the one the planner can actually reach.
    agent_card.url = f"http://127.0.0.1:{AGENT_PORT}"
    agent_card.preferred_transport = TransportProtocol.jsonrpc

    executor = SimulationControllerExecutor()
    handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())

    app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
    config = uvicorn.Config(app.build(), host="127.0.0.1", port=AGENT_PORT, log_level="info", loop="none")

    print(f"Simulator A2A server: http://127.0.0.1:{AGENT_PORT}")
    # DEVIATION FROM THE CODELAB (docs/GOTCHAS.md #6): the codelab prints
    # /.well-known/agent.json here, but A2AStarletteApplication serves the card
    # at /.well-known/agent-card.json - and that is the path the planner fetches.
    print(f"Agent card: http://127.0.0.1:{AGENT_PORT}/.well-known/agent-card.json")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(run_server())
