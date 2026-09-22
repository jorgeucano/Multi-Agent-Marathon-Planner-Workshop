"""Lazy exports for the Runner Cohort Agent."""


def __getattr__(name):
    if name == "root_agent":
        from .agent import root_agent

        return root_agent
    raise AttributeError(name)


__all__ = ["root_agent"]
