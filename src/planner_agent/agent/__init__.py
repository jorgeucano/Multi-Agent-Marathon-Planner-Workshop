"""Marathon Planner agent package."""

from .config import AGENT_DESCRIPTION, AGENT_NAME, MODEL, OUTPUT_SCHEMA

__all__ = ["root_agent", "AGENT_NAME", "MODEL", "AGENT_DESCRIPTION", "OUTPUT_SCHEMA"]


def __getattr__(name: str):
    if name == "root_agent":
        from .agent import root_agent
        return root_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
