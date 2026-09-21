"""Marathon Planner Agent.

DEVIATION FROM THE CODELAB (docs/GOTCHAS.md #1): the codelab eagerly imports
root_agent here inside `try/except Exception`, which (a) builds the whole agent
- Skills, sub-agents, Vertex init - as a side effect of importing the package,
and (b) swallows every error so a broken agent looks like a missing attribute.
PEP 562 lazy attributes keep `from planner_agent import root_agent` working
while letting tests import submodules without standing up an agent.
"""

__all__ = ["root_agent", "AGENT_NAME", "MODEL"]


def __getattr__(name: str):
    if name == "root_agent":
        from .agent import root_agent
        return root_agent
    if name in ("AGENT_NAME", "MODEL"):
        from .agent import config
        return getattr(config, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
