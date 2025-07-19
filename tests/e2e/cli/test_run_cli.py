import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.wrapper.adk.cli.cli import run_cli


class TestRunCli:
    """Test cases for the run_cli function."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.run_input_file")
    async def test_run_cli_with_input_file(
        self,
        mock_run_input_file,
        mock_load_dotenv,
        mock_agent_loader_class,
        mock_credential_service_class,
        mock_session_service_class,
        mock_artifact_service_class,
        mock_services,
        mock_agent,
    ):
        """Test run_cli with an input file."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        mock_artifact_service_class.return_value = artifact_service
        mock_session_service_class.return_value = session_service
        mock_credential_service_class.return_value = credential_service

        mock_agent_loader = MagicMock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        mock_run_input_file.return_value = mock_session

        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            input_data = {"state": {"test": "state"}, "queries": ["test query"]}
            json.dump(input_data, f)
            input_file_path = f.name

        try:
            # Test function
            await run_cli(agent_module_name="test_agent", input_file=input_file_path)

            # Assertions
            mock_agent_loader.load_agent.assert_called_once_with("test_agent")
            mock_load_dotenv.assert_called_once_with("test_agent")
            mock_run_input_file.assert_called_once()

        finally:
            # Cleanup
            Path(input_file_path).unlink()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    async def test_run_cli_with_saved_session(
        self,
        mock_run_interactively,
        mock_load_dotenv,
        mock_agent_loader_class,
        mock_credential_service_class,
        mock_session_service_class,
        mock_artifact_service_class,
        mock_services,
        mock_agent,
    ):
        """Test run_cli with a saved session file."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        mock_artifact_service_class.return_value = artifact_service
        mock_session_service_class.return_value = session_service
        mock_credential_service_class.return_value = credential_service

        mock_agent_loader = MagicMock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        # Create temporary session file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            session_data = {
                "id": "session123",
                "user_id": "user123",
                "app_name": "test_agent",
                "events": [{"author": "user", "content": {"parts": [{"text": "hello"}]}}],
            }
            json.dump(session_data, f)
            session_file_path = f.name

        try:
            # Test function
            await run_cli(agent_module_name="test_agent", saved_session_file=session_file_path)

            # Assertions
            mock_agent_loader.load_agent.assert_called_once_with("test_agent")
            mock_load_dotenv.assert_called_once_with("test_agent")
            mock_run_interactively.assert_called_once()

        finally:
            # Cleanup
            Path(session_file_path).unlink()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("src.wrapper.adk.cli.cli.click.echo")
    async def test_run_cli_interactive_mode(
        self,
        mock_click_echo,
        mock_run_interactively,
        mock_load_dotenv,
        mock_agent_loader_class,
        mock_credential_service_class,
        mock_session_service_class,
        mock_artifact_service_class,
        mock_services,
        mock_agent,
    ):
        """Test run_cli in interactive mode (no input file or saved session)."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        mock_artifact_service_class.return_value = artifact_service
        mock_session_service_class.return_value = session_service
        mock_credential_service_class.return_value = credential_service

        mock_agent_loader = MagicMock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        # Test function
        await run_cli(agent_module_name="test_agent")

        # Assertions
        mock_agent_loader.load_agent.assert_called_once_with("test_agent")
        mock_load_dotenv.assert_called_once_with("test_agent")
        mock_click_echo.assert_called_once_with(
            f"Running agent {mock_agent.name}, type exit to exit."
        )
        mock_run_interactively.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.run_interactively_with_tui")
    @patch("src.wrapper.adk.cli.cli.click.echo")
    async def test_run_cli_with_tui(
        self,
        mock_click_echo,
        mock_run_interactively_with_tui,
        mock_load_dotenv,
        mock_agent_loader_class,
        mock_credential_service_class,
        mock_session_service_class,
        mock_artifact_service_class,
        mock_services,
        mock_agent,
    ):
        """Test run_cli with TUI mode enabled."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        mock_artifact_service_class.return_value = artifact_service
        mock_session_service_class.return_value = session_service
        mock_credential_service_class.return_value = credential_service

        mock_agent_loader = MagicMock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        # Test function
        await run_cli(agent_module_name="test_agent", tui=True, ui_theme="dark")

        # Assertions
        mock_agent_loader.load_agent.assert_called_once_with("test_agent")
        mock_load_dotenv.assert_called_once_with("test_agent")
        mock_click_echo.assert_called_once_with(
            f"Running agent {mock_agent.name}, type exit to exit."
        )
        mock_run_interactively_with_tui.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("builtins.input", return_value="test_session_123")
    @patch("builtins.open")
    @patch("builtins.print")
    async def test_run_cli_with_session_saving(
        self,
        mock_print,
        mock_open,
        mock_input,
        mock_run_interactively,
        mock_load_dotenv,
        mock_agent_loader_class,
        mock_credential_service_class,
        mock_session_service_class,
        mock_artifact_service_class,
        mock_services,
        mock_agent,
    ):
        """Test run_cli with session saving enabled."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        mock_artifact_service_class.return_value = artifact_service
        mock_session_service_class.return_value = session_service
        mock_credential_service_class.return_value = credential_service

        mock_agent_loader = MagicMock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        # Mock file context manager
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock session dump
        mock_session.model_dump_json.return_value = '{"test": "session"}'

        # Test function
        await run_cli(agent_module_name="test_agent", save_session=True)

        # Assertions
        mock_agent_loader.load_agent.assert_called_once_with("test_agent")
        mock_load_dotenv.assert_called_once_with("test_agent")
        mock_run_interactively.assert_called_once()
        mock_input.assert_called_once_with("Session ID to save: ")
        mock_open.assert_called_once_with("test_session_123.session.json", "w", encoding="utf-8")
        mock_file.write.assert_called_once_with('{"test": "session"}')
        mock_print.assert_called_once_with("Session saved to", "test_session_123.session.json")
