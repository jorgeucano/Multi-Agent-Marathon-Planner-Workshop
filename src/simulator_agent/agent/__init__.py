"""Simulation Controller agent package."""

from .config import AGENT_NAME, MODEL

__all__ = ["root_agent", "AGENT_NAME", "MODEL"]


def __getattr__(name: str):
    if name == "root_agent":
        from .agent import root_agent
        return root_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
