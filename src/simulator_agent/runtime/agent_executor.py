"""A2A Agent Executor for Simulation Controller Agent."""

import os

import vertexai
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, TextPart, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.genai import types

from ..services.memory_manager import create_memory_service
from ..services.session_manager import SessionManager, create_session_service


class SimulationControllerExecutor(AgentExecutor):
    def __init__(self):
        self.agent = None
        self.runner = None
        self.session_manager = None

    def _init_agent(self):
        if self.agent is None:
            try:
                from simulator_agent.agent import root_agent
            except ImportError:
                from ..agent.agent import root_agent
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("AGENT_ENGINE_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            vertexai.init(project=project_id, location=location)
            self.agent = root_agent

        if self.runner is None:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("AGENT_ENGINE_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            session_service = create_session_service(project=project_id, location=location)
            memory_service = create_memory_service(project=project_id, location=location)

            from google.adk.agents.context_cache_config import ContextCacheConfig
            from google.adk.apps import App
            app = App(name=self.agent.name, root_agent=self.agent,
                      context_cache_config=ContextCacheConfig(cache_intervals=10, ttl_seconds=3600, min_tokens=4096))
            self.runner = Runner(app=app, session_service=session_service, memory_service=memory_service)

        if self.session_manager is None:
            self.session_manager = SessionManager(session_service=self.runner.session_service)

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        if self.agent is None:
            self._init_agent()
        user_id = context.message.metadata.get("user_id") if context.message and context.message.metadata else "planner_agent"
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not hasattr(context, "current_task") or not context.current_task:
            await updater.submit()
        await updater.start_work()
        plan_data = context.get_user_input()
        if not plan_data:
            await updater.update_status(TaskState.failed, message=new_agent_text_message("No plan data"), final=True)
            return
        try:
            await updater.update_status(TaskState.working, message=new_agent_text_message("Reviewing plan..."))
            session_id = await self.session_manager.get_or_create_session(
                context_id=context.context_id, app_name=self.runner.app_name, user_id=user_id)
            content = types.Content(role="user", parts=[types.Part(text=plan_data)])
            final_event = None
            async for event in self.runner.run_async(session_id=session_id, user_id=user_id, new_message=content):
                if event.is_final_response():
                    final_event = event
            if final_event and final_event.content and final_event.content.parts:
                text = "".join(p.text for p in final_event.content.parts if hasattr(p, "text") and p.text)
                if text:
                    await updater.add_artifact([TextPart(text=text)], name="result")
                    await updater.complete()
                    return
            await updater.update_status(TaskState.failed, message=new_agent_text_message("Failed"), final=True)
        except Exception as e:
            await updater.update_status(TaskState.failed, message=new_agent_text_message(f"Review failed: {e}"), final=True)

    async def cancel(self, context, event_queue):
        raise ServerError(error=UnsupportedOperationError())
