#!/usr/bin/env python3
"""Send a real marathon planning request to the Planner over A2A.

NOT IN THE CODELAB. The codelab's "test the multi-agent system" step only curls
the agent card - it never sends a message, so the three agents never actually
talk. This is the client that makes the demo a demo.

Usage:
    uv run python scripts/send_request.py --city "Buenos Aires" --participants 30000
    uv run python scripts/send_request.py --city Austin --theme charity --watch
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid

import httpx

DEFAULT_PORT = 8084
POLL_SECONDS = 2.0


def build_prompt(args) -> str:
    bits = [
        f"Plan a {args.theme} city marathon in {args.city}",
        f"for {args.participants:,} participants",
    ]
    if args.date:
        bits.append(f"on {args.date}")
    if args.budget:
        bits.append(f"with a budget of {args.budget}")
    prompt = " ".join(bits) + "."
    prompt += (
        " Produce the full plan, then send it to the Evaluator for scoring and to the "
        "Simulation Controller for the readiness verdict. Report the waypoints, the "
        "per-criterion scores with the overall score, and the simulation verdict."
    )
    return prompt


async def send(base_url: str, prompt: str, timeout: float, watch: bool) -> int:
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": prompt}],
                "metadata": {"user_id": "workshop_user"},
            }
        },
    }

    started = time.time()
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        try:
            card = (await client.get(f"{base_url}/.well-known/agent-card.json")).json()
            print(f"-> agent: {card.get('name')} :: {card.get('description', '')[:70]}...")
        except Exception as e:
            print(f"!! cannot reach the planner at {base_url}: {e}")
            print("   Is `uv run python -m src.planner_agent.runtime.local_server` running?")
            return 2

        print(f"-> prompt: {prompt[:100]}...")
        print("-> waiting (the Evaluator runs 7 LLM judges; 1-3 min is normal)\n")

        try:
            resp = await client.post(base_url, json=payload)
        except httpx.ReadTimeout:
            print(f"!! timed out after {timeout:.0f}s. Retry with --timeout 600.")
            return 3

        data = resp.json()
        if "error" in data:
            print(f"!! A2A error: {json.dumps(data['error'], indent=2)}")
            return 4

        result = data.get("result", {})
        task_id = result.get("id")
        state = (result.get("status") or {}).get("state")

        while watch and task_id and state in ("submitted", "working"):
            await asyncio.sleep(POLL_SECONDS)
            poll = await client.post(base_url, json={
                "jsonrpc": "2.0", "id": str(uuid.uuid4()),
                "method": "tasks/get", "params": {"id": task_id},
            })
            result = poll.json().get("result", {})
            state = (result.get("status") or {}).get("state")
            msg = ((result.get("status") or {}).get("message") or {})
            text = "".join(p.get("text", "") for p in msg.get("parts", []))
            print(f"   [{time.time() - started:5.0f}s] {state}: {text[:80]}")

    print("\n" + "=" * 70)
    print(f"STATE: {state}   ({time.time() - started:.0f}s)")
    print("=" * 70)

    if state != "completed":
        # El motivo va en status.message, no en los artifacts. Mostralo primero:
        # enterrarlo en un dump de JSON es lo que hace que un error de
        # credenciales parezca un problema de A2A.
        msg = (result.get("status") or {}).get("message") or {}
        motivo = "".join(p.get("text", "") for p in msg.get("parts", []))
        print(f"\nMOTIVO: {motivo or '(sin mensaje)'}")
        print("\nRevisá el log del planner: el traceback completo está ahí.")

    for artifact in result.get("artifacts", []) or []:
        for part in artifact.get("parts", []):
            if part.get("text"):
                print(part["text"])

    if not result.get("artifacts") and state == "completed":
        print(json.dumps(result, indent=2)[:4000])

    return 0 if state == "completed" else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Send a marathon plan request over A2A.")
    p.add_argument("--city", default="Buenos Aires")
    p.add_argument("--participants", type=int, default=30000)
    p.add_argument("--theme", default="scenic")
    p.add_argument("--date", default="")
    p.add_argument("--budget", default="")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--timeout", type=float, default=600.0, help="HTTP timeout in seconds")
    p.add_argument("--watch", action="store_true", help="poll and print task status while it runs")
    args = p.parse_args()

    return asyncio.run(
        send(f"http://127.0.0.1:{args.port}", build_prompt(args), args.timeout, args.watch)
    )


if __name__ == "__main__":
    sys.exit(main())
