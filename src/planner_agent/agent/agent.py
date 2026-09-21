"""Marathon Planner Agent - LlmAgent wiring.

Wires config + prompts + tools + skills into the LlmAgent.
"""

import os

import vertexai
from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig, ThinkingConfig

from ..services.memory_manager import auto_save_memories
from .config import AGENT_DESCRIPTION, AGENT_NAME, MODEL, OUTPUT_SCHEMA
from .prompts import INSTRUCTION
from .tools import get_tools

# Initialize Vertex AI
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
if project_id:
    vertexai.init(project=project_id, location=location)

agent_kwargs = dict(
    name=AGENT_NAME,
    model=MODEL,
    description=AGENT_DESCRIPTION,
    static_instruction=INSTRUCTION,
    tools=get_tools(),
    generate_content_config=GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_budget=2048),
    ),
    after_agent_callback=auto_save_memories,
)

if OUTPUT_SCHEMA is not None:
    agent_kwargs["output_schema"] = OUTPUT_SCHEMA

root_agent = LlmAgent(**agent_kwargs)
