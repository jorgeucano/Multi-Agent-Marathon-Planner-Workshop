"""System instructions for the Marathon Planner Agent."""

import pathlib

_PROMPT_DIR = pathlib.Path(__file__).parent
INSTRUCTION = (_PROMPT_DIR / "planner-instruction.md").read_text()
