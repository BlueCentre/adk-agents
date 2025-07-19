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
import os
from typing import Optional

from google.adk.artifacts.gcs_artifact_service import GcsArtifactService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.memory.vertex_ai_rag_memory_service import VertexAiRagMemoryService
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService
import rich_click as click

from .cli.utils import envs

logger = logging.getLogger("google_adk." + __name__)


class ServiceFactory:
    def __init__(self, agents_dir: str):
        self.agents_dir = agents_dir

    def get_artifact_service(self, artifact_service_uri: Optional[str]):
        if artifact_service_uri:
            if artifact_service_uri.startswith("gs://"):
                gcs_bucket = artifact_service_uri.split("://")[1]
                return GcsArtifactService(bucket_name=gcs_bucket)
            raise click.ClickException(f"Unsupported artifact service URI: {artifact_service_uri}")
        return InMemoryArtifactService()

    def get_session_service(self, session_service_uri: Optional[str]):
        if session_service_uri:
            if session_service_uri.startswith("agentengine://"):
                agent_engine_id = session_service_uri.split("://")[1]
                if not agent_engine_id:
                    raise click.ClickException("Agent engine id can not be empty.")
                envs.load_dotenv_for_agent("", self.agents_dir)
                return VertexAiSessionService(
                    project=os.environ["GOOGLE_CLOUD_PROJECT"],
                    location=os.environ["GOOGLE_CLOUD_LOCATION"],
                    agent_engine_id=agent_engine_id,
                )
            return DatabaseSessionService(db_url=session_service_uri)
        return InMemorySessionService()

    def get_memory_service(self, memory_service_uri: Optional[str]):
        if memory_service_uri:
            if memory_service_uri.startswith("rag://"):
                rag_corpus = memory_service_uri.split("://")[1]
                if not rag_corpus:
                    raise click.ClickException("Rag corpus can not be empty.")
                envs.load_dotenv_for_agent("", self.agents_dir)
                return VertexAiRagMemoryService(
                    rag_corpus=f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}/locations/{os.environ['GOOGLE_CLOUD_LOCATION']}/ragCorpora/{rag_corpus}"
                )
            if memory_service_uri.startswith("agentengine://"):
                agent_engine_id = memory_service_uri.split("://")[1]
                if not agent_engine_id:
                    raise click.ClickException("Agent engine id can not be empty.")
                envs.load_dotenv_for_agent("", self.agents_dir)
                # Assuming VertexAiMemoryBankService exists and is correctly imported/used
                # from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
                # return VertexAiMemoryBankService(
                #     project=os.environ["GOOGLE_CLOUD_PROJECT"],
                #     location=os.environ["GOOGLE_CLOUD_LOCATION"],
                #     agent_engine_id=agent_engine_id,
                # )
                raise NotImplementedError(
                    "VertexAiMemoryBankService is not yet implemented in ServiceFactory."
                )
            raise click.ClickException(f"Unsupported memory service URI: {memory_service_uri}")
        return InMemoryMemoryService()

    def get_credential_service(self):
        return InMemoryCredentialService()
