"""Tools for the Marathon Planner Agent.

Contains:
- A2A infrastructure (SerializableRemoteA2aAgent, URL helpers)
- Remote A2A agent creators for Evaluator and Simulation Controller
- get_tools() - assembles all tools including SkillToolset
"""

import logging
import os

import httpx
from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory
from a2a.types import TransportProtocol as A2ATransport
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.function_tool import FunctionTool

from ..evaluator.agent import root_agent as evaluator_agent
from .auth import GoogleAuthRefresh

logger = logging.getLogger(__name__)

AGENT_TIMEOUT_SECONDS = 120

# Default port for the local Simulation Controller. Keep this in sync with
# src/simulator_agent/runtime/local_server.py::AGENT_PORT.
SIMULATOR_DEFAULT_PORT = 8089

# ============================================================================
# A2A INFRASTRUCTURE
# ============================================================================

def _get_agent_a2a_endpoint(resource_name: str, default_port: int = SIMULATOR_DEFAULT_PORT) -> str:
    """Construct A2A card endpoint URL from resource name or local address."""
    if resource_name.startswith("local"):
        port = resource_name.split(":")[1] if ":" in resource_name else default_port
        return f"http://127.0.0.1:{port}/.well-known/agent-card.json"

    parts = resource_name.split("/")
    try:
        location = parts[parts.index("locations") + 1]
        return f"https://{location}-aiplatform.googleapis.com/v1beta1/{resource_name}/a2a/v1/card"
    except (ValueError, IndexError):
        return resource_name


def _get_agent_a2a_url(resource_name: str) -> str | None:
    """Construct the regional A2A message URL from Agent Engine resource name."""
    if resource_name.startswith("local"):
        return None
    parts = resource_name.split("/")
    location = parts[parts.index("locations") + 1]
    return f"https://{location}-aiplatform.googleapis.com/v1beta1/{resource_name}/a2a"


class SerializableRemoteA2aAgent(RemoteA2aAgent):
    """RemoteA2aAgent with authentication and Agent Engine URL fix.

    Handles two Agent Engine issues:
    1. Creates httpx client lazily with Google Cloud auth
    2. Fixes agent card URL (Agent Engine returns global URL that 404s)
    """

    def __init__(self, *, a2a_url: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._a2a_url_override = a2a_url

    async def _ensure_httpx_client(self) -> httpx.AsyncClient:
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout=AGENT_TIMEOUT_SECONDS),
                headers={"Content-Type": "application/json"},
                auth=GoogleAuthRefresh(),
            )
            self._httpx_client_needs_cleanup = True

        if self._a2a_client_factory is None:
            self._a2a_client_factory = A2AClientFactory(
                config=A2AClientConfig(
                    httpx_client=self._httpx_client,
                    streaming=False, polling=False,
                    supported_transports=[A2ATransport.http_json, A2ATransport.jsonrpc],
                )
            )
        return self._httpx_client

    async def _resolve_agent_card_from_url(self, url: str):
        card = await super()._resolve_agent_card_from_url(url)
        if self._a2a_url_override:
            logger.info(f"Overriding agent card URL: {card.url} -> {self._a2a_url_override}")
            card.url = self._a2a_url_override
        return card


def create_evaluator_tool() -> AgentTool:
    """Create Evaluator Agent tool - local sub-agent, no A2A needed."""
    return AgentTool(agent=evaluator_agent)


def create_simulator_agent() -> RemoteA2aAgent:
    """Create remote connection to Simulation Controller Agent via A2A."""
    resource_name = os.environ.get("SIMULATOR_AGENT_RESOURCE_NAME")
    if not resource_name:
        raise ValueError("SIMULATOR_AGENT_RESOURCE_NAME environment variable must be set")

    endpoint = _get_agent_a2a_endpoint(resource_name, default_port=SIMULATOR_DEFAULT_PORT)
    logger.info(f"Creating Simulation Controller Agent connection: {endpoint}")

    return SerializableRemoteA2aAgent(
        name="simulator_agent",
        description=(
            "Simulation Controller Agent for marathon plans. "
            "Reviews plans for simulation readiness, assessing route feasibility, "
            "logistics completeness, and safety clearance."
        ),
        agent_card=endpoint,
        a2a_url=_get_agent_a2a_url(resource_name),
    )


def create_simulation_controller_tool() -> AgentTool:
    return AgentTool(agent=create_simulator_agent())


# ============================================================================
# TOOL EXPORT
# ============================================================================

def get_tools() -> list:
    """Return the tools for the Marathon Planner Agent."""
    import importlib.util
    import pathlib

    from google.adk.skills import load_skill_from_dir
    from google.adk.tools.preload_memory_tool import PreloadMemoryTool
    from google.adk.tools.skill_toolset import SkillToolset

    # Load ADK Skills
    skills_dir = pathlib.Path(__file__).parent.parent / "skills"
    skills = [
        load_skill_from_dir(skills_dir / name)
        for name in sorted(skills_dir.iterdir())
        if name.is_dir() and not name.name.startswith("_")
    ]
    skill_toolset = SkillToolset(skills=skills)

    # Load route-planning tools dynamically (handles hyphenated directory names)
    def load_tool_from_skill(skill_name, tool_name):
        skill_tool_path = skills_dir / skill_name / "tools.py"
        if not skill_tool_path.exists():
            logger.error(
                f"Skill tool file missing: {skill_tool_path}. "
                f"'{tool_name}' will NOT be available to the agent."
            )
            return None
        try:
            spec = importlib.util.spec_from_file_location(f"{skill_name}.tools", skill_tool_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, tool_name, None)
        except Exception as e:
            logger.error(f"Error loading tool {tool_name} from {skill_name}: {e}")
            return None

    tools = [skill_toolset, PreloadMemoryTool()]

    # DEVIATION FROM THE CODELAB (docs/GOTCHAS.md #2): the codelab only wires
    # plan_marathon_route. The route skill also ships add_water_stations and
    # add_medical_tents, and the logistics score depends on them being real
    # numbers rather than invented ones.
    for tool_name in ("plan_marathon_route", "add_water_stations", "add_medical_tents"):
        func = load_tool_from_skill("route-planning", tool_name)
        if func:
            tools.append(FunctionTool(func=func))
            logger.info(f"Added route-planning tool: {tool_name}")

    # Add local evaluator sub-agent
    tools.append(create_evaluator_tool())
    logger.info("Added local Evaluator tool")

    # Add remote Simulation Controller via A2A (if configured)
    if os.environ.get("SIMULATOR_AGENT_RESOURCE_NAME"):
        tools.append(create_simulation_controller_tool())
        logger.info("Added A2A Simulation Controller tool")
    else:
        logger.info(
            "SIMULATOR_AGENT_RESOURCE_NAME not set - running in Solo mode "
            "(Planner + Evaluator). Set it to local:%s for Full Team mode.",
            SIMULATOR_DEFAULT_PORT,
        )

    return tools
