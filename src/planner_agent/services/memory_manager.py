"""Memory Manager for Marathon Planner Agent.

Manages Memory Bank integration with custom topics.
Enables cross-session learning.
"""

import os
from typing import TYPE_CHECKING

from google.adk.memory import VertexAiMemoryBankService
from vertexai._genai.types import (
    MemoryBankCustomizationConfig,
    MemoryBankCustomizationConfigMemoryTopic as MemoryTopic,
    MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic as CustomMemoryTopic,
)

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext

# Custom memory topics for cross-session learning
PLANNING_HISTORY = MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
        label="planning_history",
        description="""Track marathon plans generated across sessions.
        Extract: City, date, key route decisions, final score, iteration count.
        Format: "Plan: city={city}, date={date}, score={score}, iterations={n}"
        """,
    )
)

USER_PREFERENCES = MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
        label="user_preferences",
        description="""Track user preferences and constraints across sessions.
        Extract: Preferred themes, budget priorities, scale, city preferences.
        Format: "Preference: type={type}, value={value}"
        """,
    )
)

ROUTE_PATTERNS = MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
        label="route_patterns",
        description="""Track successful route patterns and lessons learned.
        Extract: Route segments with positive feedback, landmark combinations.
        Format: "Route: city={city}, pattern={pattern}, outcome={outcome}"
        """,
    )
)

LOGISTICS_INSIGHTS = MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
        label="logistics_insights",
        description="""Track logistics decisions and capacity learnings.
        Extract: Water station placement, venue capacity, crowd management.
        Format: "Logistics: category={cat}, insight={insight}"
        """,
    )
)


def create_marathon_planner_memory_topics() -> MemoryBankCustomizationConfig:
    """Create Memory Bank customization config with custom topics."""
    return MemoryBankCustomizationConfig(
        memory_topics=[
            PLANNING_HISTORY, USER_PREFERENCES,
            ROUTE_PATTERNS, LOGISTICS_INSIGHTS,
        ]
    )


def create_memory_service(
    project: str | None = None,
    location: str | None = None,
    agent_engine_id: str | None = None,
) -> VertexAiMemoryBankService | None:
    """Create a VertexAiMemoryBankService.

    Returns None if agent_engine_id is not set (local development).
    """
    project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = location or (
        os.environ.get("AGENT_ENGINE_LOCATION")
        or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    agent_engine_id = agent_engine_id or os.environ.get("AGENT_ENGINE_ID")

    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable required")
    if not agent_engine_id:
        return None

    return VertexAiMemoryBankService(
        project=project, location=location,
        agent_engine_id=agent_engine_id,
    )


async def auto_save_memories(callback_context: "CallbackContext") -> None:
    """Automatically save session to Memory Bank after agent responds."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = (
        os.environ.get("AGENT_ENGINE_LOCATION")
        or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    agent_engine_id = os.environ.get("AGENT_ENGINE_ID")

    if not agent_engine_id:
        return

    try:
        memory_service = VertexAiMemoryBankService(
            project=project_id, location=location,
            agent_engine_id=agent_engine_id,
        )
        await memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )
    except Exception as e:
        print(f"Warning: Failed to save memories: {e}")
