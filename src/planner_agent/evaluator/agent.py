"""Evaluator Agent - scores marathon plans using Vertex AI Evaluation.

Uses gemini-3.1-pro-preview for best evaluation quality.
"""

import os

import vertexai
from google.adk.agents import LlmAgent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai.types import GenerateContentConfig, ThinkingConfig

from .config import (
    AGENT_DESCRIPTION,
    AGENT_NAME,
    CRITERION_WEIGHTS,
    MODEL,
    SEVERITY_THRESHOLDS,
)
from .prompts import INSTRUCTION
from .schemas import EvaluationResult
from .services.memory_manager import auto_save_memories
from .tools import evaluate_plan

# Structured output schema - guarantees every response matches EvaluationResult
OUTPUT_SCHEMA = EvaluationResult

# Initialize Vertex AI
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
if project_id:
    vertexai.init(project=project_id, location=location)

# Enable thinking for better evaluation reasoning
evaluator_config = GenerateContentConfig(max_output_tokens=4096)
if "pro" in MODEL:
    evaluator_config.thinking_config = ThinkingConfig(thinking_budget=1024)

evaluator_agent = LlmAgent(
    name=AGENT_NAME,
    model=MODEL,
    description=AGENT_DESCRIPTION,
    static_instruction=INSTRUCTION,
    output_schema=OUTPUT_SCHEMA,
    generate_content_config=evaluator_config,
    include_contents='none',
    tools=[PreloadMemoryTool(), evaluate_plan],
    after_agent_callback=auto_save_memories,
)

root_agent = evaluator_agent

__all__ = [
    "AGENT_NAME",
    "AGENT_DESCRIPTION",
    "CRITERION_WEIGHTS",
    "MODEL",
    "OUTPUT_SCHEMA",
    "SEVERITY_THRESHOLDS",
    "evaluator_agent",
    "root_agent",
]
