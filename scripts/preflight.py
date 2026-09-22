#!/usr/bin/env python3
"""Pre-workshop check: fail loudly here instead of in front of the room.

NOT IN THE CODELAB. Run this before every session and have attendees run it
before the first code step.

Usage: uv run python scripts/preflight.py
"""

from __future__ import annotations

import importlib
import os
import socket
import sys

from dotenv import load_dotenv

load_dotenv()

OK, WARN, FAIL = "  OK  ", " WARN ", " FAIL "
failures = 0
warnings = 0


def check(label: str, status: str, detail: str = "") -> None:
    global failures, warnings
    if status == FAIL:
        failures += 1
    if status == WARN:
        warnings += 1
    print(f"[{status}] {label}" + (f"\n         {detail}" if detail else ""))


def main() -> int:
    print("=" * 70)
    print("marathon-agents preflight")
    print("=" * 70)

    # 1. Python
    v = sys.version_info
    check(
        f"Python {v.major}.{v.minor}.{v.micro}",
        OK if (v.major, v.minor) >= (3, 10) else FAIL,
        "" if (v.major, v.minor) >= (3, 10) else "requires-python = >=3.10",
    )

    # 2. Environment
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    check("GOOGLE_CLOUD_PROJECT", OK if project else FAIL,
          project or "missing - copy .env.example to .env and fill it in")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    check("GOOGLE_CLOUD_LOCATION", OK, location)
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower()
    check("GOOGLE_GENAI_USE_VERTEXAI", OK if use_vertex == "true" else WARN,
          use_vertex or "not set - agents may try the AI Studio API instead of Vertex")

    # 3. Dependencies
    for mod in ("google.adk", "a2a", "vertexai", "pandas", "httpx", "uvicorn"):
        try:
            m = importlib.import_module(mod)
            check(f"import {mod}", OK, getattr(m, "__version__", ""))
        except Exception as e:
            check(f"import {mod}", FAIL, f"{type(e).__name__}: {e} - run `uv sync`")

    # 4. Credentials (the #1 laptop failure: no ADC outside Cloud Shell)
    try:
        from google.auth import default
        creds, adc_project = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        check("Application Default Credentials", OK, f"project={adc_project}")
        if project and adc_project and adc_project != project:
            check("ADC project matches .env", WARN, f"{adc_project} != {project}")
    except Exception as e:
        check("Application Default Credentials", FAIL,
              f"{e}\n         Run: gcloud auth application-default login")

    # 5. Models actually reachable in this project/region
    models = {
        "PLANNER_MODEL": os.environ.get("PLANNER_MODEL", "gemini-3-flash-preview"),
        "EVALUATOR_MODEL": os.environ.get("EVALUATOR_MODEL", "gemini-3.1-pro-preview"),
        "SIMULATOR_MODEL": os.environ.get("SIMULATOR_MODEL", "gemini-3-flash-preview"),
        "RUNNER_MODEL": os.environ.get("RUNNER_MODEL", "gemini-3-flash-preview"),
    }
    if project:
        try:
            from google import genai
            client = genai.Client(vertexai=True, project=project, location=location)
            for var, model in models.items():
                try:
                    client.models.generate_content(model=model, contents="ping")
                    check(f"{var} = {model}", OK, "responds in " + location)
                except Exception as e:
                    check(f"{var} = {model}", FAIL,
                          f"{str(e)[:180]}\n         Override it in .env if the preview model moved.")
        except Exception as e:
            check("Vertex AI client", FAIL, str(e)[:200])
    else:
        for var, model in models.items():
            check(f"{var} = {model}", WARN, "skipped - no project set")

    # 6. Ports free
    for name, port in (("planner", 8084), ("simulator", 8089)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            busy = s.connect_ex(("127.0.0.1", port)) == 0
        check(f"port {port} ({name})", WARN if busy else OK,
              "already in use - a server is running, or kill it" if busy else "free")

    # 7. Skill files the agents load at import time
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for rel in (
        "src/planner_agent/skills/route-planning/SKILL.md",
        "src/planner_agent/skills/route-planning/tools.py",
        "src/planner_agent/skills/plan-evaluation/SKILL.md",
        "src/simulator_agent/skills/review-marathon-plan/SKILL.md",
        "src/runner_agent/agent/tools.py",
    ):
        check(rel, OK if (root / rel).exists() else FAIL, "" if (root / rel).exists() else "missing")

    print("=" * 70)
    print(f"{failures} failure(s), {warnings} warning(s)")
    print("=" * 70)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
