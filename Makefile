.PHONY: help install preflight planner planner-full simulator demo demo-fast test lint clean

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## uv sync + dev extras
	uv sync --extra dev

preflight:  ## check env, credentials, models, ports
	uv run python scripts/preflight.py

planner:  ## start the Planner in Solo mode (:8084)
	uv run python -m src.planner_agent.runtime.local_server

planner-full:  ## start the Planner in Full Team mode (needs the simulator up)
	SIMULATOR_AGENT_RESOURCE_NAME=local:8089 uv run python -m src.planner_agent.runtime.local_server

simulator:  ## start the Simulation Controller (:8089)
	uv run python -m src.simulator_agent.runtime.local_server

demo:  ## send a real request over A2A
	uv run python scripts/send_request.py --city "Las Vegas" --participants 30000 --watch

demo-fast:  ## same, but force the heuristic evaluator (no LLM judges)
	EVAL_MODE=heuristic uv run python scripts/send_request.py --city "Las Vegas" --participants 30000 --watch

test:  ## full test suite
	uv run --extra dev pytest -q

test-offline:  ## tests that need no GCP and no deps
	uv run --no-project --with pytest python -m pytest tests/test_route_planning.py tests/test_readiness_check.py -q

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
