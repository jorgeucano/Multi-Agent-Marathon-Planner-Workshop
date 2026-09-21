"""Memory Manager for Simulation Controller Agent."""

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

APPROVAL_HISTORY = MemoryTopic(
    custom_memory_topic=CustomMemoryTopic(
        label="approval_history",
        description="""Track approval decisions: verdicts, readiness scores, common blockers.""",
    )
)


def create_memory_service(project=None, location=None, agent_engine_id=None):
    project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = location or os.environ.get("AGENT_ENGINE_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    agent_engine_id = agent_engine_id or os.environ.get("AGENT_ENGINE_ID")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT required")
    if not agent_engine_id:
        return None
    return VertexAiMemoryBankService(project=project, location=location, agent_engine_id=agent_engine_id)


async def auto_save_memories(callback_context: "CallbackContext") -> None:
    agent_engine_id = os.environ.get("AGENT_ENGINE_ID")
    if not agent_engine_id:
        return
    try:
        svc = VertexAiMemoryBankService(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("AGENT_ENGINE_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            agent_engine_id=agent_engine_id,
        )
        await svc.add_session_to_memory(callback_context._invocation_context.session)
    except Exception as e:
        print(f"Warning: Failed to save memories: {e}")
