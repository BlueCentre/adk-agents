"""Factory for creating Runner instances with standardized configuration."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import BaseArtifactService
from google.adk.auth.credential_service.base_credential_service import (
    BaseCredentialService,
)
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session


class RunnerFactory:
    """Factory for creating Runner instances with standardized configuration."""

    @staticmethod
    def create_runner(
        session: Session,
        agent: LlmAgent,
        artifact_service: BaseArtifactService,
        session_service: BaseSessionService,
        credential_service: BaseCredentialService,
    ) -> Runner:
        """
        Create a Runner instance with standardized configuration.

        Args:
            session: The session to use
            agent: The LLM agent to run
            artifact_service: The artifact service to use
            session_service: The session service to use
            credential_service: The credential service to use

        Returns:
            Configured Runner instance
        """
        return Runner(
            app_name=session.app_name,
            agent=agent,
            artifact_service=artifact_service,
            session_service=session_service,
            credential_service=credential_service,
        )

    @staticmethod
    def create_runner_from_app_name(
        app_name: str,
        agent: LlmAgent,
        artifact_service: BaseArtifactService,
        session_service: BaseSessionService,
        credential_service: BaseCredentialService,
    ) -> Runner:
        """
        Create a Runner instance using an app name.

        Args:
            app_name: The application name
            agent: The LLM agent to run
            artifact_service: The artifact service to use
            session_service: The session service to use
            credential_service: The credential service to use

        Returns:
            Configured Runner instance
        """
        return Runner(
            app_name=app_name,
            agent=agent,
            artifact_service=artifact_service,
            session_service=session_service,
            credential_service=credential_service,
        )
