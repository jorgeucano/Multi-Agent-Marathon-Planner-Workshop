"""Runner Cohort Agent - runner-centered interpretation of the race plan."""

from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool
from google.genai.types import GenerateContentConfig, ThinkingConfig

from .config import AGENT_DESCRIPTION, AGENT_NAME, MODEL
from .prompts import INSTRUCTION
from .tools import simulate_runner_cohorts


root_agent = LlmAgent(
    name=AGENT_NAME,
    model=MODEL,
    description=AGENT_DESCRIPTION,
    static_instruction=INSTRUCTION,
    tools=[FunctionTool(func=simulate_runner_cohorts)],
    generate_content_config=GenerateContentConfig(
        thinking_config=ThinkingConfig(thinking_budget=0),
        max_output_tokens=2048,
    ),
)
