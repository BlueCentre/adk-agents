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

import logging

import pydantic
from pydantic import alias_generators
from typing import Any
from typing import Optional
import os

from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.base_session_service import BaseSessionService as SessionService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
from google.adk.artifacts.gcs_artifact_service import GcsArtifactService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.artifacts.base_artifact_service import BaseArtifactService as ArtifactService
# from google.adk.logs.console_logger import ConsoleLogger # Removed as ConsoleLogger not found
# from google.adk.logs.logger import Logger # Removed as Logger not found
# from google.adk.state.in_memory_state_manager import InMemoryStateManager # Removed as InMemoryStateManager not found
# from google.adk.state.state_manager import StateManager # Removed as StateManager not found
# from google.adk.utils.get_envs import get_envs as get_adk_envs # Removed as get_envs not found
from google.adk.events.event import Event

# logger = logging.getLogger("google_adk." + __name__) # Removed as Logger not found


class BaseModel(pydantic.BaseModel):
  model_config = pydantic.ConfigDict(
      alias_generator=alias_generators.to_camel,
      populate_by_name=True,
  )

def get_session_service(session_db_url: str = "") -> SessionService:
  if session_db_url:
    if session_db_url.startswith("agentengine://"):
      # Create vertex session service
      agent_engine_id = session_db_url.split("://")[1]
      if not agent_engine_id:
        raise ValueError("Agent engine id can not be empty.")
      # Assuming GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are set as envs.
      # This will be handled by the envs.load_dotenv_for_agent call in AgentLoader
      return VertexAiSessionService(
          os.environ["GOOGLE_CLOUD_PROJECT"],
          os.environ["GOOGLE_CLOUD_LOCATION"],
      )
    else:
      return DatabaseSessionService(db_url=session_db_url)
  else:
    return InMemorySessionService()

def get_artifact_service(artifact_storage_uri: Optional[str] = None) -> ArtifactService:
  if artifact_storage_uri:
    if artifact_storage_uri.startswith("gs://"):
      gcs_bucket = artifact_storage_uri.split("://")[1]
      return GcsArtifactService(bucket_name=gcs_bucket)
    else:
      raise ValueError("Unsupported artifact storage URI: %s" % artifact_storage_uri)
  else:
    return InMemoryArtifactService()

# def get_logger() -> Logger: # Removed as Logger not found
#   return ConsoleLogger() # Removed as ConsoleLogger not found

# def get_state_manager() -> StateManager: # Removed as StateManager not found
#   return InMemoryStateManager() # Removed as InMemoryStateManager not found

# def get_envs() -> dict[str, str]: # Removed as get_envs not found
#   return get_adk_envs() # Removed as get_envs not found

# def get_event_graph_dot_src( # Removed as get_agent_graph_dot_src not found
#     event: Event,
#     session_service: SessionService,
#     artifact_service: ArtifactService,
#     app_name: str,
#     user_id: str,
#     session_id: str,
# ) -> str:
#   return get_adk_event_graph_dot_src( # Removed as get_agent_graph_dot_src not found
#       event=event,
#       session_service=session_service,
#       artifact_service=artifact_service,
#       app_name=app_name,
#       user_id=user_id,
#       session_id=session_id,
#   )
