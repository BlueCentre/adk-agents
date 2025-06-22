# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import time
import traceback
import typing
from typing import Any
from typing import List
from typing import Literal
from typing import Optional

import rich_click as click
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
from fastapi.websockets import WebSocketDisconnect
from google.genai import types
import graphviz
from pydantic import Field
from pydantic import ValidationError
from starlette.types import Lifespan
from typing_extensions import override

from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.llm_agent import Agent
from google.adk.agents.run_config import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.artifacts.gcs_artifact_service import GcsArtifactService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.errors.not_found_error import NotFoundError
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from .utils import cleanup
from .utils import common
from .utils import create_empty_state
from .utils import envs
from .utils.agent_loader import AgentLoader

logger = logging.getLogger("google_adk." + __name__)

_EVAL_SET_FILE_EXTENSION = ".evalset.json"


class AgentRunRequest(common.BaseModel):
  app_name: str
  user_id: str
  session_id: str
  new_message: types.Content
  streaming: bool = False


class GetEventGraphResult(common.BaseModel):
  dot_src: str


def get_fast_api_app(
    *,
    agents_dir: str,
    session_db_url: str = "",
    artifact_storage_uri: Optional[str] = None,
    allow_origins: Optional[list[str]] = None,
    web: bool,
    trace_to_cloud: bool = False,
) -> FastAPI:
  # InMemory tracing dict.
  trace_dict: dict[str, Any] = {}

  @asynccontextmanager
  async def internal_lifespan(app: FastAPI):
    try:
      yield
    finally:
      pass

  app = FastAPI(lifespan=internal_lifespan)
  app.add_middleware(
      CORSMiddleware,
      allow_origins=allow_origins if allow_origins else [],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  # Serve static files from the build directory.
  if web:
    import os
    browser_dir = os.path.join(os.path.dirname(__file__), "browser")
    app.mount("/dev-ui", StaticFiles(directory=browser_dir, html=True))

  @app.get("/list-apps")
  def list_apps() -> list[str]:
    return AgentLoader.get_available_agent_modules(agents_dir)

  @app.get("/debug/trace/{event_id}")
  def get_trace_dict(event_id: str) -> Any:
    return trace_dict.get(event_id, None)

  @app.get("/debug/trace/session/{session_id}")
  def get_session_trace(session_id: str) -> Any:
    return trace_dict.get(session_id, None)

  @app.get(
      "/apps/{app_name}/users/{user_id}/sessions/{session_id}",
      response_model_exclude_none=True,
  )
  async def get_session(
      app_name: str, user_id: str, session_id: str
  ) -> Session:
    # Connect to managed session if agent_engine_id is set.
    session_service = common.get_session_service(
        session_db_url=session_db_url
    )
    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if session is None:
      raise HTTPException(status_code=404, detail="Session not found.")
    return session

  @app.get(
      "/apps/{app_name}/users/{user_id}/sessions",
      response_model_exclude_none=True,
  )
  async def list_sessions(app_name: str, user_id: str) -> list[Session]:
    # Connect to managed session if agent_engine_id is set.
    session_service = common.get_session_service(
        session_db_url=session_db_url
    )
    response = await session_service.list_sessions(
        app_name=app_name, user_id=user_id
    )
    return response.sessions

  @app.post(
      "/apps/{app_name}/users/{user_id}/sessions/{session_id}",
      response_model_exclude_none=True,
  )
  async def create_session_with_id(
      app_name: str,
      user_id: str,
      session_id: str,
      state: Optional[dict[str, Any]] = None,
  ) -> Session:
    # Connect to managed session if agent_engine_id is set.
    session_service = common.get_session_service(
        session_db_url=session_db_url
    )
    return await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id, state=state
    )

  @app.post(
      "/apps/{app_name}/users/{user_id}/sessions",
      response_model_exclude_none=True,
  )
  async def create_session(
      app_name: str,
      user_id: str,
      state: Optional[dict[str, Any]] = None,
  ) -> Session:
    # Connect to managed session if agent_engine_id is set.
    session_service = common.get_session_service(
        session_db_url=session_db_url
    )
    return await session_service.create_session(
        app_name=app_name, user_id=user_id, state=state
    )

  @app.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
  async def delete_session(app_name: str, user_id: str, session_id: str):
    # Connect to managed session if agent_engine_id is set.
    session_service = common.get_session_service(
        session_db_url=session_db_url
    )
    await session_service.delete_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

  @app.get(
      "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}",
      response_model_exclude_none=True,
  )
  async def load_artifact(
      app_name: str,
      user_id: str,
      session_id: str,
      artifact_name: str,
      version: Optional[int] = Query(None),
  ) -> Optional[types.Part]:
    artifact_service = common.get_artifact_service(artifact_storage_uri)
    return await artifact_service.load_artifact(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename=artifact_name,
        version=version,
    )

  @app.get(
      "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}/versions/{version_id}",
      response_model_exclude_none=True,
  )
  async def load_artifact_version(
      app_name: str,
      user_id: str,
      session_id: str,
      artifact_name: str,
      version_id: int,
  ) -> Optional[types.Part]:
    artifact_service = common.get_artifact_service(artifact_storage_uri)
    return await artifact_service.load_artifact(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename=artifact_name,
        version=version_id,
    )

  @app.get(
      "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts",
      response_model_exclude_none=True,
  )
  async def list_artifact_names(
      app_name: str, user_id: str, session_id: str
  ) -> list[str]:
    artifact_service = common.get_artifact_service(artifact_storage_uri)
    return await artifact_service.list_artifact_keys(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

  @app.get(
      "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}/versions",
      response_model_exclude_none=True,
  )
  async def list_artifact_versions(
      app_name: str, user_id: str, session_id: str, artifact_name: str
  ) -> list[int]:
    artifact_service = common.get_artifact_service(artifact_storage_uri)
    return await artifact_service.list_versions(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename=artifact_name,
    )

  @app.delete(
      "/apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_name}",
  )
  async def delete_artifact(
      app_name: str, user_id: str, session_id: str, artifact_name: str
  ):
    artifact_service = common.get_artifact_service(artifact_storage_uri)
    await artifact_service.delete_artifact(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        filename=artifact_name,
    )

  @app.post("/run", response_model_exclude_none=True)
  async def agent_run(req: AgentRunRequest) -> list[Event]:
    # Connect to managed session if agent_engine_id is set.
    session_service = common.get_session_service(
        session_db_url=session_db_url
    )
    artifact_service = common.get_artifact_service(artifact_storage_uri)
    agent_loader = AgentLoader(agents_dir)

    try:
      agent = agent_loader.load_agent(req.app_name)
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))

    runner = Runner(
        agent=agent,
        app_name=req.app_name,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    if req.streaming:
      run_config = RunConfig(streaming_mode=StreamingMode.SSE)
    else:
      run_config = RunConfig(streaming_mode=StreamingMode.NONE)

    events = []
    try:
      async for event in runner.run_async(
          user_id=req.user_id,
          session_id=req.session_id,
          new_message=req.new_message,
          run_config=run_config,
      ):
        if trace_to_cloud:
          # trace_dict[event.id] = ApiServerSpanExporter().get_spans_for_trace(
          #     event.trace_id
          # ) # Re-added trace_dict update
          pass
        events.append(event)
    except ValueError as e:
      if "Session not found" in str(e):
        # Create a new session and retry
        logger.info(f"Session {req.session_id} not found, creating new session")
        await session_service.create_session(
            app_name=req.app_name, 
            user_id=req.user_id, 
            session_id=req.session_id
        )
        # Retry the request
        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=req.session_id,
            new_message=req.new_message,
            run_config=run_config,
        ):
          if trace_to_cloud:
            pass
          events.append(event)
      else:
        raise HTTPException(status_code=500, detail=str(e))

    return events

  @app.post("/run_sse")
  async def agent_run_sse(req: AgentRunRequest) -> StreamingResponse:
    # Connect to managed session if agent_engine_id is set.
    session_service = common.get_session_service(
        session_db_url=session_db_url
    )
    artifact_service = common.get_artifact_service(artifact_storage_uri)
    agent_loader = AgentLoader(agents_dir)

    try:
      agent = agent_loader.load_agent(req.app_name)
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))

    runner = Runner(
        agent=agent,
        app_name=req.app_name,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    if req.streaming:
      run_config = RunConfig(streaming_mode=StreamingMode.SSE)
    else:
      run_config = RunConfig(streaming_mode=StreamingMode.NONE)

    async def event_generator():
      try:
        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=req.session_id,
            new_message=req.new_message,
            run_config=run_config,
        ):
          if trace_to_cloud:
            # trace_dict[event.id] = ApiServerSpanExporter().get_spans_for_trace(
            #     event.trace_id
            # ) # Re-added trace_dict update
            pass
          yield f"data: {event.model_dump_json()}\n\n"
      except ValueError as e:
        if "Session not found" in str(e):
          # Create a new session and retry
          logger.info(f"Session {req.session_id} not found, creating new session")
          await session_service.create_session(
              app_name=req.app_name, 
              user_id=req.user_id, 
              session_id=req.session_id
          )
          # Retry the request
          async for event in runner.run_async(
              user_id=req.user_id,
              session_id=req.session_id,
              new_message=req.new_message,
              run_config=run_config,
          ):
            if trace_to_cloud:
              pass
            yield f"data: {event.model_dump_json()}\n\n"
        else:
          # Send error event to client
          error_event = {
            "type": "error",
            "message": str(e),
            "timestamp": "2025-06-22T11:00:00Z"
          }
          yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

  @app.get("/")
  async def redirect_root_to_dev_ui():
    return RedirectResponse(url="/dev-ui")

  @app.get("/dev-ui")
  async def redirect_dev_ui_add_slash():
    return RedirectResponse(url="/dev-ui/")

  return app
