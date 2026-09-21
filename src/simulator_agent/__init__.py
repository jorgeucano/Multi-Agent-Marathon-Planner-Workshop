"""Simulation Controller Agent. See docs/GOTCHAS.md #1 for why this is lazy."""

__all__ = ["root_agent", "AGENT_NAME", "MODEL"]


def __getattr__(name: str):
    if name == "root_agent":
        from .agent import root_agent
        return root_agent
    if name in ("AGENT_NAME", "MODEL"):
        from .agent import config
        return getattr(config, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
