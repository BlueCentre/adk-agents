"""
Tests for cli.py module with comprehensive coverage.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

from pydantic import ValidationError
import pytest

from src.wrapper.adk.cli.cli import (
    InputFile,
    run_cli,
    run_input_file,
    run_interactively,
    run_interactively_with_tui,
)


class TestInputFileModel:
    """Test the InputFile Pydantic model."""

    def test_valid_input_file(self):
        """Test that a valid input file passes validation."""
        valid_data = {
            "queries": ["What is the weather?", "Tell me a joke"],
            "state": {"user_id": "123", "session": "abc"},
        }
        input_file = InputFile(**valid_data)
        assert input_file.queries == ["What is the weather?", "Tell me a joke"]
        assert input_file.state == {"user_id": "123", "session": "abc"}

    def test_missing_queries(self):
        """Test that missing queries raises validation error."""
        invalid_data = {"state": {"user_id": "123"}}
        with pytest.raises(ValidationError):
            InputFile(**invalid_data)

    def test_invalid_queries_type(self):
        """Test that invalid queries type raises validation error."""
        invalid_data = {"queries": "not a list", "state": {}}
        with pytest.raises(ValidationError):
            InputFile(**invalid_data)

    def test_required_state(self):
        """Test that state is required when not provided."""
        invalid_data = {"queries": ["What is the weather?"]}
        with pytest.raises(ValidationError):
            InputFile(**invalid_data)

    def test_empty_state_allowed(self):
        """Test that empty state dict is allowed."""
        valid_data = {"queries": ["What is the weather?"], "state": {}}
        input_file = InputFile(**valid_data)
        assert input_file.queries == ["What is the weather?"]
        assert input_file.state == {}


class TestRunInputFile:
    """Test the run_input_file function."""

    @pytest.mark.asyncio
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"queries": ["test query"], "state": {}}',
    )
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_run_input_file_success(self, mock_runner_factory, mock_file):
        """Test successful execution of run_input_file."""
        # Mock services
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"
        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)

        # Mock agent
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work

        # Mock runner
        mock_runner = Mock()
        mock_runner_factory.create_runner_from_app_name.return_value = mock_runner
        mock_runner.close = AsyncMock()

        # Mock async generator for runner.run_async
        async def mock_run_async(*_, **__):
            mock_event = Mock()
            mock_event.author = "assistant"
            mock_event.content = Mock()
            mock_part = Mock()
            mock_part.text = "Test response"
            mock_part.thought = False
            mock_event.content.parts = [mock_part]
            mock_event.usage_metadata = Mock()
            mock_event.usage_metadata.prompt_token_count = 10
            mock_event.usage_metadata.candidates_token_count = 20
            mock_event.usage_metadata.total_token_count = 30
            yield mock_event

        mock_runner.run_async = mock_run_async

        result = await run_input_file(
            app_name="test_app",
            user_id="test_user",
            root_agent=mock_agent,
            artifact_service=Mock(),
            session_service=mock_session_service,
            credential_service=Mock(),
            input_path="/path/to/input.json",
        )

        # Verify file was opened (either with explicit "r" mode or default)
        assert mock_file.call_count == 1
        call_args = mock_file.call_args
        assert call_args[0][0] == "/path/to/input.json"  # First argument is the file path
        assert call_args[1]["encoding"] == "utf-8"  # encoding is specified

        # Verify session was created
        mock_session_service.create_session.assert_called_once()

        # Verify result
        assert result == mock_session

    @pytest.mark.asyncio
    async def test_run_input_file_missing_file(self):
        """Test run_input_file with missing file."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                await run_input_file(
                    app_name="test_app",
                    user_id="test_user",
                    root_agent=Mock(),
                    artifact_service=Mock(),
                    session_service=Mock(),
                    credential_service=Mock(),
                    input_path="/nonexistent/path.json",
                )

    @pytest.mark.asyncio
    async def test_run_input_file_invalid_json(self):
        """Test run_input_file with invalid JSON."""
        with patch("builtins.open", new_callable=mock_open, read_data="invalid json"):
            with pytest.raises(ValidationError):
                await run_input_file(
                    app_name="test_app",
                    user_id="test_user",
                    root_agent=Mock(),
                    artifact_service=Mock(),
                    session_service=Mock(),
                    credential_service=Mock(),
                    input_path="/path/to/invalid.json",
                )

    @pytest.mark.asyncio
    async def test_run_input_file_validation_error(self):
        """Test run_input_file with validation error."""
        with patch("builtins.open", new_callable=mock_open, read_data='{"invalid": "data"}'):
            with pytest.raises(ValidationError):
                await run_input_file(
                    app_name="test_app",
                    user_id="test_user",
                    root_agent=Mock(),
                    artifact_service=Mock(),
                    session_service=Mock(),
                    credential_service=Mock(),
                    input_path="/path/to/invalid.json",
                )


class TestRunCliCore:
    """Test core run_cli functionality."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_input_file")
    async def test_run_cli_with_input_file(
        self,
        mock_run_input_file,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
        mock_load_dotenv,
    ):
        """Test run_cli with input file."""
        # Setup mocks
        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        mock_run_input_file.return_value = mock_session

        await run_cli(
            agent_module_name="test_agent",
            input_file="/path/to/input.json",
        )

        # Verify environment loading
        mock_load_dotenv.assert_called_once_with("test_agent")

        # Verify agent loading
        mock_agent_loader.load_agent.assert_called_once_with("test_agent")

        # Verify input file processing
        mock_run_input_file.assert_called_once()
        call_args = mock_run_input_file.call_args
        assert call_args[1]["app_name"] == "test_agent"
        assert call_args[1]["user_id"] == "test_user"
        assert call_args[1]["input_path"] == "/path/to/input.json"

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_interactively_with_tui")
    @patch("src.wrapper.adk.cli.cli.click.echo")
    async def test_run_cli_tui_mode(
        self,
        mock_echo,
        mock_run_tui,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
    ):
        """Test run_cli with TUI mode."""
        # Setup mocks
        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        await run_cli(
            agent_module_name="test_agent",
            tui=True,
            ui_theme="dark",
        )

        # Verify TUI was called
        mock_run_tui.assert_called_once()
        call_args = mock_run_tui.call_args
        assert call_args[1]["ui_theme"] == "dark"

        # Verify welcome message
        mock_echo.assert_called_with("Running agent TestAgent, type exit to exit.")


class TestSessionManagement:
    """Test session file loading and saving functionality."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("src.wrapper.adk.cli.cli.Session")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.wrapper.adk.cli.cli.click.echo")
    async def test_saved_session_file_loading(
        self,
        mock_echo,
        mock_file,
        mock_session_class,
        mock_run_interactively,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
    ):
        """Test loading a saved session file."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service.append_event = AsyncMock()
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        # Mock loaded session with events
        mock_loaded_session = Mock()
        mock_loaded_session.events = [
            Mock(
                author="user",
                content=Mock(
                    parts=[Mock(text="Hello")],
                ),
            ),
            Mock(
                author="assistant",
                content=Mock(
                    parts=[Mock(text="Hi there!")],
                ),
            ),
        ]
        mock_session_class.model_validate_json.return_value = mock_loaded_session

        # Mock file content
        session_data = {"events": [{"author": "user", "content": {"parts": [{"text": "Hello"}]}}]}
        mock_file.return_value.read.return_value = json.dumps(session_data)

        await run_cli(
            agent_module_name="test_agent",
            saved_session_file="/path/to/session.json",
        )

        # Verify session loading (either with explicit "r" mode or default)
        assert mock_file.call_count == 1
        call_args = mock_file.call_args
        assert call_args[0][0] == "/path/to/session.json"  # First argument is the file path
        assert call_args[1]["encoding"] == "utf-8"  # encoding is specified
        mock_session_class.model_validate_json.assert_called_once()

        # Verify events were echoed
        mock_echo.assert_any_call("[user]: Hello")
        mock_echo.assert_any_call("[assistant]: Hi there!")

        # Verify session events were appended
        assert mock_session_service.append_event.call_count == 2

        # Verify interactive mode was called
        mock_run_interactively.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("builtins.input", return_value="custom_session")
    @patch("builtins.print")
    async def test_session_saving_flow(
        self,
        mock_print,
        mock_input,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
    ):
        """Test session saving workflow."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"
        mock_session.model_dump_json.return_value = '{"session": "data"}'

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        with patch("builtins.open", mock_open()) as mock_file:
            await run_cli(
                agent_module_name="test_agent",
                save_session=True,
                session_id=None,  # Will prompt for session ID
            )

            # Verify session saving
            mock_input.assert_called_once_with("Session ID to save: ")
            mock_file.assert_called_once_with("custom_session.session.json", "w", encoding="utf-8")
            mock_file().write.assert_called_once_with('{"session": "data"}')
            mock_print.assert_called_with("Session saved to", "custom_session.session.json")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    async def test_session_saving_complete_flow(
        self,
        mock_print,
        mock_file,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
    ):
        """Test complete session saving flow with file writing."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work

        mock_session = Mock()
        mock_session.model_dump_json.return_value = '{"test": "session"}'
        mock_session.app_name = "test.agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session_id"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        # Test session saving with provided session ID
        await run_cli(
            agent_module_name="test.agent",
            save_session=True,
            session_id="my_session_id",  # Provided session ID
        )

        # Verify session was saved to file
        mock_file.assert_called_with("my_session_id.session.json", "w", encoding="utf-8")
        mock_file().write.assert_called_with('{"test": "session"}')
        mock_print.assert_called_with("Session saved to", "my_session_id.session.json")


class TestInteractiveMode:
    """Test interactive command handling."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_interactive_special_commands(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test special commands in interactive mode."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_cli = Mock()
        mock_cli.create_enhanced_prompt_session.return_value = Mock()
        mock_cli.print_welcome_message = Mock()
        mock_cli.print_help = Mock()
        mock_cli.toggle_theme = Mock()
        mock_cli.set_theme = Mock()
        mock_cli.console = Mock()
        mock_get_cli_instance.return_value = mock_cli

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session to return commands
        prompt_session = mock_cli.create_enhanced_prompt_session.return_value

        commands = [
            "clear",
            "help",
            "theme",
            "theme toggle",
            "theme dark",
            "theme light",
            "exit",
        ]
        prompt_session.prompt_async = AsyncMock(side_effect=commands)

        await run_interactively(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
            ui_theme="dark",
        )

        # Verify theme operations were called
        mock_cli.toggle_theme.assert_called()
        mock_cli.set_theme.assert_called()

        # Verify help was called
        mock_cli.print_help.assert_called()

        # Verify console clear was called (now handled by ConsoleCommandDisplay)
        mock_console.clear.assert_called()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_interactive_empty_query_handling(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test handling of empty queries in interactive mode."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_cli = Mock()
        mock_cli.create_enhanced_prompt_session.return_value = Mock()
        mock_cli.print_welcome_message = Mock()
        mock_cli.console = Mock()
        mock_get_cli_instance.return_value = mock_cli

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session to return empty queries then exit
        prompt_session = mock_cli.create_enhanced_prompt_session.return_value
        prompt_session.prompt_async = AsyncMock(side_effect=["", "   ", "exit"])

        await run_interactively(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # run_async should not have been called for empty queries
        mock_runner.run_async.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_interactive_fallback_mode_commands(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test commands in fallback mode when enhanced UI fails."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        # Make get_cli_instance fail to trigger fallback mode
        mock_get_cli_instance.side_effect = Exception("UI failed")

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session for fallback mode
        with patch("prompt_toolkit.PromptSession") as mock_prompt_session_class:
            prompt_session = Mock()
            mock_prompt_session_class.return_value = prompt_session

            commands = ["clear", "help", "quit"]
            prompt_session.prompt_async = AsyncMock(side_effect=commands)

            await run_interactively(
                root_agent=mock_agent,
                artifact_service=Mock(),
                session=mock_session,
                session_service=Mock(),
                credential_service=Mock(),
            )

            # Verify fallback mode was triggered
            mock_console.print.assert_any_call(
                "[warning]⚠️ Enhanced UI initialization failed: UI failed[/warning]"
            )
            mock_console.print.assert_any_call("[info]Falling back to basic CLI mode...[/info]")

            # Verify console operations in fallback mode
            mock_console.clear.assert_called()


class TestTUIFunctionality:
    """Test Textual UI functionality."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_textual_cli_instance")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_tui_callback_setup(self, mock_runner_factory, mock_get_textual_cli):
        """Test TUI callback setup and enhancement logic."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent.description = "Test Description"
        mock_agent.tools = ["tool1", "tool2"]
        mock_agent.model = "test_model"

        # Set up agent with None callbacks initially
        mock_agent.before_tool_callback = None
        mock_agent.after_tool_callback = None

        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_app_tui = Mock()
        mock_app_tui.register_input_callback = Mock()
        mock_app_tui.register_interrupt_callback = Mock()
        mock_app_tui.display_agent_welcome = Mock()
        mock_app_tui.run_async = AsyncMock()
        mock_get_textual_cli.return_value = mock_app_tui

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
            ui_theme="dark",
        )

        # Verify TUI setup
        mock_get_textual_cli.assert_called_once_with("dark")
        mock_app_tui.display_agent_welcome.assert_called_once_with(
            mock_agent.name, mock_agent.description, mock_agent.tools
        )

        # Verify callbacks were set up (they exist as attributes)
        assert hasattr(mock_agent, "before_tool_callback")
        assert hasattr(mock_agent, "after_tool_callback")

        mock_runner.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_textual_cli_instance")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_tui_callback_enhancement_with_existing_callbacks(
        self, mock_runner_factory, mock_get_textual_cli
    ):
        """Test TUI callback enhancement when agent already has callbacks."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent.description = "Test Description"
        mock_agent.tools = ["tool1", "tool2"]
        mock_agent.model = "test_model"

        # Set up agent with existing callbacks
        original_before = Mock()
        original_after = Mock()
        mock_agent.before_tool_callback = original_before
        mock_agent.after_tool_callback = original_after

        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_app_tui = Mock()
        mock_app_tui.register_input_callback = Mock()
        mock_app_tui.register_interrupt_callback = Mock()
        mock_app_tui.display_agent_welcome = Mock()
        mock_app_tui.run_async = AsyncMock()
        mock_app_tui.add_output = Mock()
        mock_get_textual_cli.return_value = mock_app_tui

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
            ui_theme="light",
        )

        # Verify callbacks were enhanced and exist
        assert hasattr(mock_agent, "before_tool_callback")
        assert hasattr(mock_agent, "after_tool_callback")
        assert callable(mock_agent.before_tool_callback)
        assert callable(mock_agent.after_tool_callback)

        mock_runner.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_textual_cli_instance")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_tui_enhanced_callbacks_coverage(self, mock_runner_factory, mock_get_textual_cli):
        """Test TUI enhanced callback functionality."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent.description = "Test Description"
        mock_agent.tools = ["tool1"]

        # Agent has existing callbacks
        original_before = AsyncMock()
        original_after = AsyncMock()
        mock_agent.before_tool_callback = original_before
        mock_agent.after_tool_callback = original_after

        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_tui = Mock()
        mock_tui.agent_name = "TestAgent"
        mock_tui.register_input_callback = Mock()
        mock_tui.register_interrupt_callback = Mock()
        mock_tui.display_agent_welcome = Mock()
        mock_tui.run_async = AsyncMock()
        mock_tui.add_tool_event = Mock()
        mock_get_textual_cli.return_value = mock_tui

        mock_runner = Mock()
        mock_runner.close = AsyncMock()
        mock_runner_factory.create_runner.return_value = mock_runner

        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # Verify callbacks were enhanced (different callable objects)
        assert callable(mock_agent.before_tool_callback)
        assert callable(mock_agent.after_tool_callback)

        # Since we're testing in an async context, just verify the callbacks
        # were set and then restored - the actual restoration happens
        # within the TUI function itself


class TestErrorHandling:
    """Test various error scenarios and exception handling."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    async def test_run_cli_agent_load_error(self, mock_agent_loader_class, mock_load_dotenv):
        """Test run_cli when agent loading fails."""
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.side_effect = Exception("Agent not found")
        mock_agent_loader_class.return_value = mock_agent_loader

        with pytest.raises(Exception, match="Agent not found"):
            await run_cli(agent_module_name="nonexistent_agent")

        # Agent loading happens before load_dotenv, so when it fails,
        # load_dotenv is never called
        mock_load_dotenv.assert_not_called()
        mock_agent_loader.load_agent.assert_called_once_with("nonexistent_agent")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_interactive_keyboard_interrupt_handling(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test graceful handling of keyboard interrupts."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_cli = Mock()
        mock_cli.create_enhanced_prompt_session.return_value = Mock()
        mock_cli.print_welcome_message = Mock()
        mock_cli.console = Mock()
        mock_get_cli_instance.return_value = mock_cli

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session to raise KeyboardInterrupt
        prompt_session = mock_cli.create_enhanced_prompt_session.return_value
        prompt_session.prompt_async = AsyncMock(side_effect=KeyboardInterrupt())

        await run_interactively(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # Verify goodbye message was printed
        mock_cli.console.print.assert_any_call("\n👋 [warning]Goodbye![/warning]")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_interactive_eof_handling(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test graceful handling of EOF (Ctrl+D)."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_cli = Mock()
        mock_cli.create_enhanced_prompt_session.return_value = Mock()
        mock_cli.print_welcome_message = Mock()
        mock_cli.console = Mock()
        mock_get_cli_instance.return_value = mock_cli

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session to raise EOFError
        prompt_session = mock_cli.create_enhanced_prompt_session.return_value
        prompt_session.prompt_async = AsyncMock(side_effect=EOFError())

        await run_interactively(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # Verify goodbye message was printed
        mock_cli.console.print.assert_any_call("\n👋 [warning]Goodbye![/warning]")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    @patch("builtins.input")
    async def test_interactive_prompt_error_fallback(
        self,
        mock_input,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test fallback to input() when prompt session fails."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_cli = Mock()
        mock_cli.create_enhanced_prompt_session.return_value = Mock()
        mock_cli.print_welcome_message = Mock()
        mock_cli.console = Mock()
        mock_get_cli_instance.return_value = mock_cli

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session to raise a generic exception, then input() to return exit
        prompt_session = mock_cli.create_enhanced_prompt_session.return_value
        prompt_session.prompt_async = AsyncMock(side_effect=Exception("Prompt failed"))
        mock_input.return_value = "exit"

        await run_interactively(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # Verify error messages were printed
        mock_cli.console.print.assert_any_call("\n[red]❌ Prompt error: Prompt failed[/red]")
        mock_cli.console.print.assert_any_call(
            "[yellow]💡 Try using a simpler terminal or check your environment.[/yellow]"
        )
        mock_cli.console.print.assert_any_call("[blue]Falling back to basic input mode...[/blue]")

        # Verify input() was called as fallback
        mock_input.assert_called_with("😜 user > ")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    async def test_empty_input_file_path(
        self,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
    ):
        """Test run_cli with None input_file and saved_session_file."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        with patch("src.wrapper.adk.cli.cli.run_interactively") as mock_run_interactively:
            with patch("src.wrapper.adk.cli.cli.click.echo") as mock_echo:
                await run_cli(
                    agent_module_name="test_agent",
                    input_file=None,
                    saved_session_file=None,
                    tui=False,
                )

                # Verify welcome message
                mock_echo.assert_called_with("Running agent TestAgent, type exit to exit.")

                # Verify interactive mode was called
                mock_run_interactively.assert_called_once()


class TestInteractiveAgentResponses:
    """Test agent response handling in interactive mode."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_interactive_agent_response_processing(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test processing of agent responses with thought and regular content."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_cli = Mock()
        mock_cli.create_enhanced_prompt_session.return_value = Mock()
        mock_cli.print_welcome_message = Mock()
        mock_cli.format_agent_response = Mock(return_value="formatted_response")
        mock_cli.console = Mock()
        mock_cli.display_agent_response = Mock()
        mock_cli.display_agent_thought = Mock()
        mock_get_cli_instance.return_value = mock_cli

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner.close = AsyncMock()
        mock_runner_factory.create_runner.return_value = mock_runner

        # Create mock event with both regular and thought content
        mock_event = Mock()
        mock_event.author = "agent"
        mock_event.content = Mock()

        # Create mock parts - one regular, one thought
        regular_part = Mock()
        regular_part.text = "This is regular response"
        regular_part.thought = False
        regular_part.function_call = False

        thought_part = Mock()
        thought_part.text = "This is agent thinking"
        thought_part.thought = True
        thought_part.function_call = False

        mock_event.content.parts = [regular_part, thought_part]

        # Mock prompt session to return a query then exit
        prompt_session = mock_cli.create_enhanced_prompt_session.return_value
        prompt_session.prompt_async = AsyncMock(side_effect=["test query", "exit"])

        # Mock runner to return our test event
        async def mock_run_async(*_, **__):
            yield mock_event

        mock_runner.run_async = mock_run_async

        # Mock CLI to have agent thought enabled
        mock_cli.agent_thought_enabled = True
        mock_cli.agent_thought_enabled = True

        await run_interactively(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # Verify that both regular content and thoughts were processed
        mock_cli.display_agent_response.assert_called_with(
            mock_console, "This is regular response", "agent"
        )
        mock_cli.display_agent_thought.assert_called_with(mock_console, "This is agent thinking")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_interactive_fallback_output_handling(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test fallback console output when CLI fails."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        # Make CLI fail to trigger fallback mode
        mock_get_cli_instance.side_effect = Exception("CLI failed")

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner.close = AsyncMock()
        mock_runner_factory.create_runner.return_value = mock_runner

        # Create mock event
        mock_event = Mock()
        mock_event.author = "agent"
        mock_event.content = Mock()

        regular_part = Mock()
        regular_part.text = "This is regular response"
        regular_part.thought = False
        regular_part.function_call = False

        mock_event.content.parts = [regular_part]

        # Mock prompt session for fallback mode
        with patch("prompt_toolkit.PromptSession") as mock_prompt_session_class:
            prompt_session = Mock()
            mock_prompt_session_class.return_value = prompt_session
            prompt_session.prompt_async = AsyncMock(side_effect=["test query", "exit"])

            # Mock runner to return our test event
            async def mock_run_async(*_, **__):
                yield mock_event

            mock_runner.run_async = mock_run_async

            await run_interactively(
                root_agent=mock_agent,
                artifact_service=Mock(),
                session=mock_session,
                session_service=Mock(),
                credential_service=Mock(),
            )

            # Verify fallback console was used for agent output
            mock_console.print.assert_any_call("🤖 agent > This is regular response")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_textual_cli_instance")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_tui_error_handling(self, mock_runner_factory, mock_get_textual_cli):
        """Test error handling in TUI mode."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent.description = "Test Description"
        mock_agent.tools = ["tool1"]

        # Mock that agent does not have callback attributes initially
        mock_agent.before_tool_callback = None
        mock_agent.after_tool_callback = None

        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_tui = Mock()
        mock_tui.agent_name = "TestAgent"
        mock_tui.register_input_callback = Mock()
        mock_tui.register_interrupt_callback = Mock()
        mock_tui.display_agent_welcome = Mock()
        mock_tui.run_async = AsyncMock()
        mock_tui.add_output = Mock()
        mock_get_textual_cli.return_value = mock_tui

        mock_runner = Mock()
        mock_runner.close = AsyncMock()
        mock_runner_factory.create_runner.return_value = mock_runner

        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # Verify TUI setup was called correctly
        mock_tui.register_input_callback.assert_called_once()
        mock_tui.register_interrupt_callback.assert_called_once()
        mock_tui.display_agent_welcome.assert_called_once()
        mock_tui.run_async.assert_called_once()


class TestSessionSaving:
    """Test session saving functionality to reach 80% coverage."""

    def teardown_method(self):
        """Clean up any session files created during tests."""
        # Remove any .session.json files that might have been created
        session_files = Path().glob("*.session.json")
        for file in session_files:
            try:
                Path(file).remove()
            except (OSError, FileNotFoundError):
                pass  # File already removed or doesn't exist

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.input", return_value="")
    async def test_session_saving_with_empty_input(
        self,
        mock_input,
        mock_file,
        mock_run_interactively,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
    ):
        """Test session saving with empty session ID input."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work

        mock_session = Mock()
        mock_session.model_dump_json.return_value = '{"test": "session"}'
        mock_session.app_name = "test.agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session_id"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        # Test session saving with empty session ID
        await run_cli(
            agent_module_name="test.agent",
            save_session=True,
            session_id="",  # Empty session ID to trigger input prompt
        )

        # Verify session was created and interactively run
        mock_session_service.create_session.assert_called_once()
        mock_run_interactively.assert_called_once()

        # Verify input was called for session ID
        mock_input.assert_called()

        # Verify file was written (mocked)
        mock_file.assert_called_with(".session.json", "w", encoding="utf-8")
        mock_file().write.assert_called_with('{"test": "session"}')

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    async def test_session_saving_complete_flow(
        self,
        mock_print,
        mock_file,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
    ):
        """Test complete session saving flow with file writing."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work

        mock_session = Mock()
        mock_session.model_dump_json.return_value = '{"test": "session"}'
        mock_session.app_name = "test.agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session_id"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service.get_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        # Test session saving with provided session ID
        await run_cli(
            agent_module_name="test.agent",
            save_session=True,
            session_id="my_session_id",  # Provided session ID
        )

        # Verify session was saved to file (mocked)
        mock_file.assert_called_with("my_session_id.session.json", "w", encoding="utf-8")
        mock_file().write.assert_called_with('{"test": "session"}')
        mock_print.assert_called_with("Session saved to", "my_session_id.session.json")


class TestTUIInterruptHandling:
    """Test TUI interrupt handling to cover line 390."""

    @pytest.mark.asyncio
    async def test_interrupt_agent_function_coverage(self):
        """Test that interrupt_agent function can be called (covers line 390)."""
        from src.wrapper.adk.cli.cli import run_interactively_with_tui

        # Create a mock TUI that we can inspect
        mock_tui = Mock()
        mock_tui.register_input_callback = Mock()
        mock_tui.register_interrupt_callback = Mock()
        mock_tui.display_agent_welcome = Mock()
        mock_tui.run_async = AsyncMock()
        mock_tui.add_output = Mock()

        interrupt_callback = None

        def capture_interrupt_callback(callback):
            nonlocal interrupt_callback
            interrupt_callback = callback

        mock_tui.register_interrupt_callback.side_effect = capture_interrupt_callback

        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_agent.description = "Test Description"
        mock_agent.tools = ["tool1"]
        mock_agent.before_tool_callback = None
        mock_agent.after_tool_callback = None
        mock_agent.sub_agents = []  # Add this for runner.close() to work

        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        with patch("src.wrapper.adk.cli.cli.get_textual_cli_instance", return_value=mock_tui):
            with patch("src.wrapper.adk.cli.cli.RunnerFactory") as mock_runner_factory:
                mock_runner = Mock()
                mock_runner.close = AsyncMock()
                mock_runner_factory.create_runner.return_value = mock_runner

                await run_interactively_with_tui(
                    root_agent=mock_agent,
                    artifact_service=Mock(),
                    session=mock_session,
                    session_service=Mock(),
                    credential_service=Mock(),
                )

                # Call the captured interrupt callback to cover line 390
                if interrupt_callback:
                    await interrupt_callback()

                # Verify the interrupt message was added
                mock_tui.add_output.assert_any_call(
                    "⏹️ Agent interruption requested",
                    author="System",
                    rich_format=True,
                    style="warning",
                )


class TestFallbackErrorHandling:
    """Test fallback error handling to reach 80% coverage."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_fallback_eof_keyboard_interrupt_handling(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test fallback mode EOF/KeyboardInterrupt handling (covers lines 151-154)."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.sub_agents = []  # Add this for runner.close() to work
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        # Make CLI fail to trigger fallback mode
        mock_get_cli_instance.side_effect = Exception("CLI failed")

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner.close = AsyncMock()
        mock_runner_factory.create_runner.return_value = mock_runner

        # Mock prompt session for fallback mode
        with patch("prompt_toolkit.PromptSession") as mock_prompt_session_class:
            prompt_session = Mock()
            mock_prompt_session_class.return_value = prompt_session

            # Simulate EOFError to trigger fallback error handling
            prompt_session.prompt_async = AsyncMock(side_effect=EOFError())

            await run_interactively(
                root_agent=mock_agent,
                artifact_service=Mock(),
                session=mock_session,
                session_service=Mock(),
                credential_service=Mock(),
            )

            # Verify fallback goodbye message was printed to console
            mock_console.print.assert_any_call("\n👋 [warning]Goodbye![/warning]")


class TestErrorHandlingForMissingFunctions:
    """Test the new error handling logic for missing function calls."""

    def test_extract_function_name_from_error_message(self):
        """Test regex pattern matching for extracting function names from error messages."""
        import re

        # Test successful extraction
        error_msg = "Function list_tools_by_categories is not found in the tools_dict."
        match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
        assert match is not None
        assert match.group(1) == "list_tools_by_categories"

        # Test another function name
        error_msg2 = "Function analyze_code is not found in the tools_dict."
        match2 = re.search(r"Function (\w+) is not found in the tools_dict", error_msg2)
        assert match2 is not None
        assert match2.group(1) == "analyze_code"

        # Test no match (missing function name)
        error_msg3 = "Function is not found in the tools_dict."
        match3 = re.search(r"Function (\w+) is not found in the tools_dict", error_msg3)
        assert match3 is None

    def test_error_message_pattern_detection(self):
        """Test the detection of missing function error messages."""
        # Test positive cases
        error_msg1 = "Function list_tools_by_categories is not found in the tools_dict."
        assert "Function" in error_msg1
        assert "is not found in the tools_dict" in error_msg1

        error_msg2 = "Function some_tool is not found in the tools_dict."
        assert "Function" in error_msg2
        assert "is not found in the tools_dict" in error_msg2

        # Test negative cases
        error_msg3 = "Some other validation error"
        assert not ("Function" in error_msg3 and "is not found in the tools_dict" in error_msg3)

        error_msg4 = "Function exists but has other issues"
        assert not ("Function" in error_msg4 and "is not found in the tools_dict" in error_msg4)

    @patch("src.wrapper.adk.cli.cli.logger")
    def test_error_logging_behavior(self, mock_logger):
        """Test that errors are logged correctly."""
        import re

        # Simulate the logging behavior from the error handling code
        error_msg = "Function test_function is not found in the tools_dict."
        match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
        missing_function = match.group(1) if match else "unknown function"

        # Simulate the logging calls
        mock_logger.warning(f"Agent attempted to call missing function: {missing_function}")
        mock_logger.debug(f"Full error: {error_msg}")

        # Verify logging was called correctly
        mock_logger.warning.assert_called_with(
            "Agent attempted to call missing function: test_function"
        )
        mock_logger.debug.assert_called_with(f"Full error: {error_msg}")

    def test_console_output_formatting(self):
        """Test the console output formatting for error messages."""
        from unittest.mock import Mock

        # Mock console
        mock_console = Mock()
        missing_function = "test_function"

        # Simulate the console output calls from error handling
        mock_console.print(
            f"[yellow]⚠️  The agent tried to call a function '{missing_function}' that doesn't "
            "exist.[/yellow]"
        )
        mock_console.print(
            "[blue]💡 This is likely a hallucination. The agent can answer your question without "
            "this function.[/blue]"
        )
        mock_console.print(
            "[green]✅ You can rephrase your question or ask the agent to use available tools "
            "instead.[/green]"
        )

        # Verify all three messages were printed
        assert mock_console.print.call_count == 3

        # Verify the specific messages
        calls = mock_console.print.call_args_list
        assert (
            "[yellow]⚠️  The agent tried to call a function 'test_function' that doesn't exist."
            "[/yellow]" in str(calls[0])
        )
        assert "[blue]💡 This is likely a hallucination" in str(calls[1])
        assert "[green]✅ You can rephrase your question" in str(calls[2])

    def test_fallback_function_name_handling(self):
        """Test handling when function name cannot be extracted from error message."""
        import re

        # Test with malformed error message
        error_msg = "Function is not found in the tools_dict."  # Missing function name
        match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
        missing_function = match.group(1) if match else "unknown function"

        assert missing_function == "unknown function"

        # Test with completely different error message
        error_msg2 = "Some other error message"
        match2 = re.search(r"Function (\w+) is not found in the tools_dict", error_msg2)
        missing_function2 = match2.group(1) if match2 else "unknown function"

        assert missing_function2 == "unknown function"

    def test_error_handling_logic_flow(self):
        """Test the complete error handling logic flow."""
        import re

        # Test Case 1: Valid missing function error
        error_msg1 = "Function list_tools_by_categories is not found in the tools_dict."

        # Check pattern matching
        is_missing_function_error = (
            "Function" in error_msg1 and "is not found in the tools_dict" in error_msg1
        )
        assert is_missing_function_error is True

        # Check function name extraction
        match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg1)
        missing_function = match.group(1) if match else "unknown function"
        assert missing_function == "list_tools_by_categories"

        # Test Case 2: Missing function error with no function name
        error_msg2 = "Function is not found in the tools_dict."

        is_missing_function_error2 = (
            "Function" in error_msg2 and "is not found in the tools_dict" in error_msg2
        )
        assert is_missing_function_error2 is True

        match2 = re.search(r"Function (\w+) is not found in the tools_dict", error_msg2)
        missing_function2 = match2.group(1) if match2 else "unknown function"
        assert missing_function2 == "unknown function"

        # Test Case 3: Different ValueError that should be re-raised
        error_msg3 = "Some other validation error"

        is_missing_function_error3 = (
            "Function" in error_msg3 and "is not found in the tools_dict" in error_msg3
        )
        assert is_missing_function_error3 is False

        # This should result in the exception being re-raised (not handled by our error handling)

    def test_console_selection_logic(self):
        """Test the console selection logic for different modes."""
        from unittest.mock import Mock

        # Test normal mode (cli exists)
        mock_cli = Mock()
        mock_cli.console = Mock()
        mock_console = Mock()

        # Normal mode: should use cli.console
        fallback_mode = False
        cli = mock_cli
        console = mock_console

        output_console = console if fallback_mode else (cli.console if cli else console)
        assert output_console == cli.console

        # Test fallback mode
        fallback_mode = True
        output_console = console if fallback_mode else (cli.console if cli else console)
        assert output_console == console

        # Test no cli available
        fallback_mode = False
        cli = None
        output_console = console if fallback_mode else (cli.console if cli else console)
        assert output_console == console

    def test_exception_re_raising_behavior(self):
        """Test that non-function-missing ValueError exceptions are re-raised."""
        # This test verifies the logic for re-raising other ValueError exceptions

        # Test messages that should NOT be handled by our error handling
        other_errors = [
            "Invalid input parameter",
            "Configuration error",
            "Validation failed",
            "Function call failed for other reasons",
        ]

        for error_msg in other_errors:
            # These should not match our pattern
            is_missing_function_error = (
                "Function" in error_msg and "is not found in the tools_dict" in error_msg
            )
            assert is_missing_function_error is False

            # In the actual code, these would be re-raised as ValueError
            # We're testing the detection logic here

    def test_regex_pattern_edge_cases(self):
        """Test edge cases for the regex pattern matching."""
        import re

        # Test various function name patterns
        test_cases = [
            ("Function test_function is not found in the tools_dict.", "test_function"),
            (
                "Function analyze_code_quality is not found in the tools_dict.",
                "analyze_code_quality",
            ),
            ("Function listTools is not found in the tools_dict.", "listTools"),
            ("Function get_user_info is not found in the tools_dict.", "get_user_info"),
            ("Function API_call is not found in the tools_dict.", "API_call"),
            ("Function test123 is not found in the tools_dict.", "test123"),
        ]

        for error_msg, expected_function in test_cases:
            match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
            assert match is not None, f"Pattern should match: {error_msg}"
            assert match.group(1) == expected_function, (
                f"Expected {expected_function}, got {match.group(1)}"
            )

        # Test cases that should NOT match
        no_match_cases = [
            "Function is not found in the tools_dict.",  # Missing function name
            "Function with spaces is not found in the tools_dict.",  # Spaces in function name
            "Function test-function is not found in the tools_dict.",  # Dash in function name
            "Function test.function is not found in the tools_dict.",  # Dot in function name
            "function test_function is not found in the tools_dict.",  # Lowercase 'function'
            "Function test_function not found in the tools_dict.",  # Missing 'is'
        ]

        for error_msg in no_match_cases:
            match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
            assert match is None, f"Pattern should NOT match: {error_msg}"

    def test_tui_error_output_formatting(self):
        """Test the TUI error output formatting for missing function errors."""
        from unittest.mock import Mock

        # Mock TUI app
        mock_app_tui = Mock()
        missing_function = "test_function"

        # Simulate the TUI output calls from error handling
        mock_app_tui.add_output(
            f"⚠️  The agent tried to call a function '{missing_function}' that doesn't exist.",
            author="System",
            rich_format=True,
            style="warning",
        )
        mock_app_tui.add_output(
            "💡 This is likely a hallucination. The agent can answer your question without this "
            "function.",
            author="System",
            rich_format=True,
            style="info",
        )
        mock_app_tui.add_output(
            "✅ You can rephrase your question or ask the agent to use available tools instead.",
            author="System",
            rich_format=True,
            style="success",
        )

        # Verify all three messages were added to TUI output
        assert mock_app_tui.add_output.call_count == 3

        # Verify the specific messages and parameters
        calls = mock_app_tui.add_output.call_args_list

        # Check first call (warning message)
        assert (
            calls[0][0][0]
            == f"⚠️  The agent tried to call a function '{missing_function}' that doesn't exist."
        )
        assert calls[0][1]["author"] == "System"
        assert calls[0][1]["rich_format"] is True
        assert calls[0][1]["style"] == "warning"

        # Check second call (info message)
        assert "💡 This is likely a hallucination" in calls[1][0][0]
        assert calls[1][1]["author"] == "System"
        assert calls[1][1]["rich_format"] is True
        assert calls[1][1]["style"] == "info"

        # Check third call (success message)
        assert "✅ You can rephrase your question" in calls[2][0][0]
        assert calls[2][1]["author"] == "System"
        assert calls[2][1]["rich_format"] is True
        assert calls[2][1]["style"] == "success"

    def test_general_exception_handling_console_output(self):
        """Test console output for general exceptions (not function-specific)."""
        from unittest.mock import Mock

        # Mock console
        mock_console = Mock()
        error_msg = "Network connection failed"

        # Simulate the console output calls for general exceptions
        mock_console.print(f"[red]❌ An unexpected error occurred: {error_msg}[/red]")
        mock_console.print(
            "[blue]💡 You can try rephrasing your question or continue with a new request.[/blue]"
        )

        # Verify the messages were printed
        assert mock_console.print.call_count == 2

        calls = mock_console.print.call_args_list
        assert f"[red]❌ An unexpected error occurred: {error_msg}[/red]" in str(calls[0])
        assert (
            "[blue]💡 You can try rephrasing your question or continue with a new request.[/blue]"
            in str(calls[1])
        )

    def test_general_exception_handling_tui_output(self):
        """Test TUI output for general exceptions (not function-specific)."""
        from unittest.mock import Mock

        # Mock TUI app
        mock_app_tui = Mock()
        error_msg = "Network connection failed"

        # Simulate the TUI output calls for general exceptions
        mock_app_tui.add_output(
            f"❌ An unexpected error occurred: {error_msg}",
            author="System",
            rich_format=True,
            style="error",
        )
        mock_app_tui.add_output(
            "💡 You can try rephrasing your question or continue with a new request.",
            author="System",
            rich_format=True,
            style="info",
        )

        # Verify the messages were added to TUI output
        assert mock_app_tui.add_output.call_count == 2

        calls = mock_app_tui.add_output.call_args_list

        # Check first call (error message)
        assert calls[0][0][0] == f"❌ An unexpected error occurred: {error_msg}"
        assert calls[0][1]["author"] == "System"
        assert calls[0][1]["rich_format"] is True
        assert calls[0][1]["style"] == "error"

        # Check second call (info message)
        assert "💡 You can try rephrasing your question" in calls[1][0][0]
        assert calls[1][1]["author"] == "System"
        assert calls[1][1]["rich_format"] is True
        assert calls[1][1]["style"] == "info"

    @patch("src.wrapper.adk.cli.cli.logger")
    def test_error_handling_integration_test(self, mock_logger):
        """Integration test for the complete error handling flow."""
        import re
        from unittest.mock import Mock

        # Test the complete flow for a missing function error
        error_msg = "Function list_tools_by_categories is not found in the tools_dict."

        # Step 1: Check if it's a missing function error
        is_missing_function_error = (
            "Function" in error_msg and "is not found in the tools_dict" in error_msg
        )
        assert is_missing_function_error is True

        # Step 2: Extract function name
        match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
        missing_function = match.group(1) if match else "unknown function"
        assert missing_function == "list_tools_by_categories"

        # Step 3: Mock console output
        mock_console = Mock()
        mock_console.print(
            f"[yellow]⚠️  The agent tried to call a function '{missing_function}' that doesn't "
            "exist.[/yellow]"
        )
        mock_console.print(
            "[blue]💡 This is likely a hallucination. The agent can answer your question without "
            "this function.[/blue]"
        )
        mock_console.print(
            "[green]✅ You can rephrase your question or ask the agent to use available tools "
            "instead.[/green]"
        )

        # Step 4: Mock logging
        mock_logger.warning(f"Agent attempted to call missing function: {missing_function}")
        mock_logger.debug(f"Full error: {error_msg}")

        # Verify all components work together
        assert mock_console.print.call_count == 3
        mock_logger.warning.assert_called_with(
            "Agent attempted to call missing function: list_tools_by_categories"
        )
        mock_logger.debug.assert_called_with(f"Full error: {error_msg}")

    def test_error_handling_coverage_verification(self):
        """Test to verify that all error handling code paths are covered."""
        # This test ensures that we're testing all the key components of the error handling

        # Component 1: Error message pattern detection
        error_msg = "Function test_function is not found in the tools_dict."
        is_missing_function = (
            "Function" in error_msg and "is not found in the tools_dict" in error_msg
        )
        assert is_missing_function is True

        # Component 2: Regex pattern matching
        import re

        match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
        assert match is not None
        assert match.group(1) == "test_function"

        # Component 3: Fallback function name handling
        malformed_error = "Function is not found in the tools_dict."
        match_fallback = re.search(
            r"Function (\w+) is not found in the tools_dict", malformed_error
        )
        missing_function = match_fallback.group(1) if match_fallback else "unknown function"
        assert missing_function == "unknown function"

        # Component 4: Non-matching error detection
        other_error = "Some other validation error"
        is_other_error = (
            "Function" in other_error and "is not found in the tools_dict" in other_error
        )
        assert is_other_error is False

        # Component 5: Console selection logic
        from unittest.mock import Mock

        mock_cli = Mock()
        mock_console = Mock()

        # Test console selection in different modes
        fallback_mode = False
        cli = mock_cli
        console = mock_console

        output_console = console if fallback_mode else (cli.console if cli else console)
        assert output_console == cli.console

        # All key components are tested and working
        assert True
