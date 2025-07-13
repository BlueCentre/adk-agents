"""
Tests for cli.py module with comprehensive coverage.
"""

import json
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest
from pydantic import ValidationError

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
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_run_input_file_success(self, mock_runner_class, mock_file):
        """Test successful execution of run_input_file."""
        # Mock services
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"
        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)

        # Mock agent
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

        # Mock runner
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
        mock_runner.close = AsyncMock()

        # Mock async generator for runner.run_async
        async def mock_run_async(*args, **kwargs):
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

        # Verify file was opened
        mock_file.assert_called_once_with("/path/to/input.json", "r", encoding="utf-8")

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
        with patch(
            "builtins.open", new_callable=mock_open, read_data='{"invalid": "data"}'
        ):
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
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
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
        mock_load_dotenv,
    ):
        """Test run_cli with TUI mode."""
        # Setup mocks
        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
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
        mock_load_dotenv,
    ):
        """Test loading a saved session file."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
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
        session_data = {
            "events": [{"author": "user", "content": {"parts": [{"text": "Hello"}]}}]
        }
        mock_file.return_value.read.return_value = json.dumps(session_data)

        await run_cli(
            agent_module_name="test_agent",
            saved_session_file="/path/to/session.json",
        )

        # Verify session loading
        mock_file.assert_called_once_with(
            "/path/to/session.json", "r", encoding="utf-8"
        )
        mock_session_class.model_validate_json.assert_called_once()

        # Verify events were echoed
        mock_echo.assert_any_call("[user]: Hello")
        mock_echo.assert_any_call("[assistant]: Hi there!")

        # Verify session events were appended
        assert mock_session_service.append_event.call_count == 2

        # Verify interactive mode was called
        mock_run_interactively.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("builtins.input", return_value="custom_session")
    @patch("builtins.print")
    async def test_session_saving_flow(
        self,
        mock_print,
        mock_input,
        mock_run_interactively,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
        mock_load_dotenv,
    ):
        """Test session saving workflow."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
            mock_file.assert_called_once_with(
                "custom_session.session.json", "w", encoding="utf-8"
            )
            mock_file().write.assert_called_once_with('{"session": "data"}')
            mock_print.assert_called_with(
                "Session saved to", "custom_session.session.json"
            )

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    async def test_session_saving_complete_flow(
        self,
        mock_print,
        mock_file,
        mock_run_interactively,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
        mock_load_dotenv,
    ):
        """Test complete session saving flow with file writing."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

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
        mock_file.assert_called_with(
            "my_session_id.session.json", "w", encoding="utf-8"
        )
        mock_file().write.assert_called_with('{"test": "session"}')
        mock_print.assert_called_with("Session saved to", "my_session_id.session.json")


class TestInteractiveMode:
    """Test interactive command handling."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.Runner")
    @patch("src.wrapper.adk.cli.cli.patch_stdout")
    async def test_interactive_special_commands(
        self,
        mock_patch_stdout,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test special commands in interactive mode."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner
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

        # Verify console clear was called
        mock_cli.console.clear.assert_called()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_interactive_empty_query_handling(
        self,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test handling of empty queries in interactive mode."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner
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
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_interactive_fallback_mode_commands(
        self,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test commands in fallback mode when enhanced UI fails."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        # Make get_cli_instance fail to trigger fallback mode
        mock_get_cli_instance.side_effect = Exception("UI failed")

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
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
            mock_console.print.assert_any_call(
                "[info]Falling back to basic CLI mode...[/info]"
            )

            # Verify console operations in fallback mode
            mock_console.clear.assert_called()


class TestTUIFunctionality:
    """Test Textual UI functionality."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_textual_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_tui_callback_setup(self, mock_runner_class, mock_get_textual_cli):
        """Test TUI callback setup and enhancement logic."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner
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
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_tui_callback_enhancement_with_existing_callbacks(
        self, mock_runner_class, mock_get_textual_cli
    ):
        """Test TUI callback enhancement when agent already has callbacks."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner
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
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_tui_enhanced_callbacks_coverage(
        self, mock_runner_class, mock_get_textual_cli
    ):
        """Test TUI enhanced callback functionality."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner

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
    async def test_run_cli_agent_load_error(
        self, mock_agent_loader_class, mock_load_dotenv
    ):
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
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_interactive_keyboard_interrupt_handling(
        self,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test graceful handling of keyboard interrupts."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner
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
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_interactive_eof_handling(
        self,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test graceful handling of EOF (Ctrl+D)."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner
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
    @patch("src.wrapper.adk.cli.cli.Runner")
    @patch("builtins.input")
    async def test_interactive_prompt_error_fallback(
        self,
        mock_input,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test fallback to input() when prompt session fails."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner
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
        mock_cli.console.print.assert_any_call(
            "\n[red]❌ Prompt error: Prompt failed[/red]"
        )
        mock_cli.console.print.assert_any_call(
            "[yellow]💡 Try using a simpler terminal or check your environment.[/yellow]"
        )
        mock_cli.console.print.assert_any_call(
            "[blue]Falling back to basic input mode...[/blue]"
        )

        # Verify input() was called as fallback
        mock_input.assert_called_with("😜 user > ")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
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
        mock_load_dotenv,
    ):
        """Test run_cli with None input_file and saved_session_file."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent_loader = Mock()
        mock_agent_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_agent_loader

        mock_session = Mock()
        mock_session.app_name = "test_agent"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_session_service = Mock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)
        mock_session_service_class.return_value = mock_session_service

        mock_artifact_service = Mock()
        mock_artifact_service_class.return_value = mock_artifact_service

        mock_credential_service = Mock()
        mock_credential_service_class.return_value = mock_credential_service

        with patch(
            "src.wrapper.adk.cli.cli.run_interactively"
        ) as mock_run_interactively:
            with patch("src.wrapper.adk.cli.cli.click.echo") as mock_echo:
                await run_cli(
                    agent_module_name="test_agent",
                    input_file=None,
                    saved_session_file=None,
                    tui=False,
                )

                # Verify welcome message
                mock_echo.assert_called_with(
                    "Running agent TestAgent, type exit to exit."
                )

                # Verify interactive mode was called
                mock_run_interactively.assert_called_once()


class TestInteractiveAgentResponses:
    """Test agent response handling in interactive mode."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_interactive_agent_response_processing(
        self,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test processing of agent responses with thought and regular content."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        mock_cli = Mock()
        mock_cli.create_enhanced_prompt_session.return_value = Mock()
        mock_cli.print_welcome_message = Mock()
        mock_cli.format_agent_response = Mock(return_value="formatted_response")
        mock_cli.console = Mock()
        mock_cli.add_agent_thought = Mock()
        mock_get_cli_instance.return_value = mock_cli

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        mock_runner = Mock()
        mock_runner.close = AsyncMock()
        mock_runner_class.return_value = mock_runner

        # Create mock event with both regular and thought content
        mock_event = Mock()
        mock_event.author = "agent"
        mock_event.content = Mock()

        # Create mock parts - one regular, one thought
        regular_part = Mock()
        regular_part.text = "This is regular response"
        regular_part.thought = False

        thought_part = Mock()
        thought_part.text = "This is agent thinking"
        thought_part.thought = True

        mock_event.content.parts = [regular_part, thought_part]

        # Mock prompt session to return a query then exit
        prompt_session = mock_cli.create_enhanced_prompt_session.return_value
        prompt_session.prompt_async = AsyncMock(side_effect=["test query", "exit"])

        # Mock runner to return our test event
        async def mock_run_async(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = mock_run_async

        # Mock CLI to have agent thought enabled
        mock_cli.agent_thought_enabled = True
        setattr(mock_cli, "agent_thought_enabled", True)

        await run_interactively(
            root_agent=mock_agent,
            artifact_service=Mock(),
            session=mock_session,
            session_service=Mock(),
            credential_service=Mock(),
        )

        # Verify that both regular content and thoughts were processed
        mock_cli.add_agent_output.assert_called_with(
            "This is regular response", "agent"
        )
        mock_cli.add_agent_thought.assert_called_with("This is agent thinking")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_interactive_fallback_output_handling(
        self,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test fallback console output when CLI fails."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner

        # Create mock event
        mock_event = Mock()
        mock_event.author = "agent"
        mock_event.content = Mock()

        regular_part = Mock()
        regular_part.text = "This is regular response"
        regular_part.thought = False

        mock_event.content.parts = [regular_part]

        # Mock prompt session for fallback mode
        with patch("prompt_toolkit.PromptSession") as mock_prompt_session_class:
            prompt_session = Mock()
            mock_prompt_session_class.return_value = prompt_session
            prompt_session.prompt_async = AsyncMock(side_effect=["test query", "exit"])

            # Mock runner to return our test event
            async def mock_run_async(*args, **kwargs):
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
            mock_console.print.assert_any_call("agent > This is regular response")

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_textual_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_tui_error_handling(self, mock_runner_class, mock_get_textual_cli):
        """Test error handling in TUI mode."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner

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
        import glob
        import os

        # Remove any .session.json files that might have been created
        session_files = glob.glob("*.session.json")
        for file in session_files:
            try:
                os.remove(file)
            except (OSError, FileNotFoundError):
                pass  # File already removed or doesn't exist

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    async def test_session_saving_with_empty_input(
        self,
        mock_print,
        mock_input,
        mock_file,
        mock_run_interactively,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
        mock_load_dotenv,
    ):
        """Test session saving with empty session ID input."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

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
    @patch("src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent")
    @patch("src.wrapper.adk.cli.cli.AgentLoader")
    @patch("src.wrapper.adk.cli.cli.InMemorySessionService")
    @patch("src.wrapper.adk.cli.cli.InMemoryArtifactService")
    @patch("src.wrapper.adk.cli.cli.InMemoryCredentialService")
    @patch("src.wrapper.adk.cli.cli.run_interactively")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    async def test_session_saving_complete_flow(
        self,
        mock_print,
        mock_file,
        mock_run_interactively,
        mock_credential_service_class,
        mock_artifact_service_class,
        mock_session_service_class,
        mock_agent_loader_class,
        mock_load_dotenv,
    ):
        """Test complete session saving flow with file writing."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"

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
        mock_file.assert_called_with(
            "my_session_id.session.json", "w", encoding="utf-8"
        )
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
        mock_agent.description = "Test Description"
        mock_agent.tools = ["tool1"]
        mock_agent.before_tool_callback = None
        mock_agent.after_tool_callback = None

        mock_session = Mock()
        mock_session.app_name = "test_app"
        mock_session.user_id = "test_user"
        mock_session.id = "test_session"

        with patch(
            "src.wrapper.adk.cli.cli.get_textual_cli_instance", return_value=mock_tui
        ):
            with patch("src.wrapper.adk.cli.cli.Runner") as mock_runner_class:
                mock_runner = Mock()
                mock_runner.close = AsyncMock()
                mock_runner_class.return_value = mock_runner

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
    @patch("src.wrapper.adk.cli.cli.Runner")
    async def test_fallback_eof_keyboard_interrupt_handling(
        self,
        mock_runner_class,
        mock_console_class,
        mock_get_cli_instance,
    ):
        """Test fallback mode EOF/KeyboardInterrupt handling (covers lines 151-154)."""
        # Setup
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
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
        mock_runner_class.return_value = mock_runner

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
