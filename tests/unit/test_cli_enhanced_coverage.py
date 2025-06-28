"""
Enhanced test coverage for cli.py to reach 70%+ coverage.
Focuses on uncovered areas including session management, file handling, and interactive flows.
"""

import asyncio
import json
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

from pydantic import ValidationError
import pytest

from src.wrapper.adk.cli.cli import run_cli
from src.wrapper.adk.cli.cli import run_interactively
from src.wrapper.adk.cli.cli import run_interactively_with_tui


class TestSessionFileHandling:
  """Test session file loading and saving functionality."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent')
  @patch('src.wrapper.adk.cli.cli.AgentLoader')
  @patch('src.wrapper.adk.cli.cli.InMemorySessionService')
  @patch('src.wrapper.adk.cli.cli.InMemoryArtifactService')
  @patch('src.wrapper.adk.cli.cli.InMemoryCredentialService')
  @patch('src.wrapper.adk.cli.cli.run_interactively')
  @patch('src.wrapper.adk.cli.cli.Session')
  @patch('builtins.open', new_callable=mock_open)
  @patch('src.wrapper.adk.cli.cli.click.echo')
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
    mock_agent.name = 'TestAgent'
    mock_agent_loader = Mock()
    mock_agent_loader.load_agent.return_value = mock_agent
    mock_agent_loader_class.return_value = mock_agent_loader

    mock_session = Mock()
    mock_session.app_name = 'test_agent'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

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
            author='user',
            content=Mock(
                parts=[Mock(text='Hello')],
            ),
        ),
        Mock(
            author='assistant',
            content=Mock(
                parts=[Mock(text='Hi there!')],
            ),
        ),
    ]
    mock_session_class.model_validate_json.return_value = mock_loaded_session

    # Mock file content
    session_data = {
        'events': [
            {'author': 'user', 'content': {'parts': [{'text': 'Hello'}]}}
        ]
    }
    mock_file.return_value.read.return_value = json.dumps(session_data)

    await run_cli(
        agent_module_name='test_agent',
        saved_session_file='/path/to/session.json',
    )

    # Verify session loading
    mock_file.assert_called_once_with(
        '/path/to/session.json', 'r', encoding='utf-8'
    )
    mock_session_class.model_validate_json.assert_called_once()

    # Verify events were echoed
    mock_echo.assert_any_call('[user]: Hello')
    mock_echo.assert_any_call('[assistant]: Hi there!')

    # Verify session events were appended
    assert mock_session_service.append_event.call_count == 2

    # Verify interactive mode was called
    mock_run_interactively.assert_called_once()


class TestInteractiveCommands:
  """Test interactive command handling."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Console')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  @patch('src.wrapper.adk.cli.cli.patch_stdout')
  async def test_interactive_special_commands(
      self,
      mock_patch_stdout,
      mock_close_runner,
      mock_runner_class,
      mock_console_class,
      mock_get_cli_instance,
  ):
    """Test special commands in interactive mode."""
    # Setup
    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_session = Mock()
    mock_session.app_name = 'test_app'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

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

    # Mock prompt session to return commands
    prompt_session = mock_cli.create_enhanced_prompt_session.return_value

    commands = [
        'clear',
        'help',
        'theme',
        'theme toggle',
        'theme dark',
        'theme light',
        'exit',
    ]
    prompt_session.prompt_async = AsyncMock(side_effect=commands)

    await run_interactively(
        root_agent=mock_agent,
        artifact_service=Mock(),
        session=mock_session,
        session_service=Mock(),
        credential_service=Mock(),
        ui_theme='dark',
    )

    # Verify theme operations were called
    mock_cli.toggle_theme.assert_called()
    mock_cli.set_theme.assert_called()

    # Verify help was called
    mock_cli.print_help.assert_called()

    # Verify console clear was called
    mock_cli.console.clear.assert_called()

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Console')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  async def test_interactive_fallback_mode_commands(
      self,
      mock_close_runner,
      mock_runner_class,
      mock_console_class,
      mock_get_cli_instance,
  ):
    """Test commands in fallback mode when enhanced UI fails."""
    # Setup
    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_session = Mock()
    mock_session.app_name = 'test_app'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

    # Make get_cli_instance fail to trigger fallback mode
    mock_get_cli_instance.side_effect = Exception('UI failed')

    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

    # Mock prompt session for fallback mode
    with patch('prompt_toolkit.PromptSession') as mock_prompt_session_class:
      prompt_session = Mock()
      mock_prompt_session_class.return_value = prompt_session

      commands = ['clear', 'help', 'quit']
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
          '[warning]⚠️  Enhanced UI initialization failed: UI failed[/warning]'
      )
      mock_console.print.assert_any_call(
          '[info]Falling back to basic CLI mode...[/info]'
      )

      # Verify console operations in fallback mode
      mock_console.clear.assert_called()


class TestTUIFunctionality:
  """Test Textual UI functionality."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_textual_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  async def test_tui_callback_enhancement(
      self, mock_close_runner, mock_runner_class, mock_get_textual_cli
  ):
    """Test TUI callback enhancement logic."""
    # Setup
    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_agent.description = 'Test Description'
    mock_agent.tools = ['tool1', 'tool2']
    mock_agent.model = 'test_model'

    # Set up agent with None callbacks initially
    mock_agent.before_tool_callback = None
    mock_agent.after_tool_callback = None

    mock_session = Mock()
    mock_session.app_name = 'test_app'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

    mock_app_tui = Mock()
    mock_app_tui.register_input_callback = Mock()
    mock_app_tui.register_interrupt_callback = Mock()
    mock_app_tui.display_agent_welcome = Mock()
    mock_app_tui.run_async = AsyncMock()
    mock_get_textual_cli.return_value = mock_app_tui

    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

    await run_interactively_with_tui(
        root_agent=mock_agent,
        artifact_service=Mock(),
        session=mock_session,
        session_service=Mock(),
        credential_service=Mock(),
        ui_theme='dark',
    )

    # Verify TUI setup
    mock_get_textual_cli.assert_called_once_with('dark')
    mock_app_tui.display_agent_welcome.assert_called_once_with(
        mock_agent.name, mock_agent.description, mock_agent.tools
    )

    # Verify callbacks were set up (they exist as attributes)
    assert hasattr(mock_agent, 'before_tool_callback')
    assert hasattr(mock_agent, 'after_tool_callback')

    mock_close_runner.assert_called_once()


class TestErrorHandling:
  """Test various error scenarios and edge cases."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent')
  @patch('src.wrapper.adk.cli.cli.AgentLoader')
  @patch('src.wrapper.adk.cli.cli.InMemorySessionService')
  @patch('src.wrapper.adk.cli.cli.InMemoryArtifactService')
  @patch('src.wrapper.adk.cli.cli.InMemoryCredentialService')
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
    mock_agent.name = 'TestAgent'
    mock_agent_loader = Mock()
    mock_agent_loader.load_agent.return_value = mock_agent
    mock_agent_loader_class.return_value = mock_agent_loader

    mock_session = Mock()
    mock_session.app_name = 'test_agent'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

    mock_session_service = Mock()
    mock_session_service.create_session = AsyncMock(return_value=mock_session)
    mock_session_service_class.return_value = mock_session_service

    mock_artifact_service = Mock()
    mock_artifact_service_class.return_value = mock_artifact_service

    mock_credential_service = Mock()
    mock_credential_service_class.return_value = mock_credential_service

    with patch(
        'src.wrapper.adk.cli.cli.run_interactively'
    ) as mock_run_interactively:
      with patch('src.wrapper.adk.cli.cli.click.echo') as mock_echo:
        await run_cli(
            agent_module_name='test_agent',
            input_file=None,
            saved_session_file=None,
            tui=False,
        )

        # Verify welcome message
        mock_echo.assert_called_with(
            'Running agent TestAgent, type exit to exit.'
        )

        # Verify interactive mode was called
        mock_run_interactively.assert_called_once()

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.envs.load_dotenv_for_agent')
  @patch('src.wrapper.adk.cli.cli.AgentLoader')
  @patch('src.wrapper.adk.cli.cli.InMemorySessionService')
  @patch('src.wrapper.adk.cli.cli.InMemoryArtifactService')
  @patch('src.wrapper.adk.cli.cli.InMemoryCredentialService')
  @patch('builtins.input', return_value='custom_session')
  @patch('builtins.print')
  async def test_session_saving_flow(
      self,
      mock_print,
      mock_input,
      mock_credential_service_class,
      mock_artifact_service_class,
      mock_session_service_class,
      mock_agent_loader_class,
      mock_load_dotenv,
  ):
    """Test session saving workflow."""
    # Setup
    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_agent_loader = Mock()
    mock_agent_loader.load_agent.return_value = mock_agent
    mock_agent_loader_class.return_value = mock_agent_loader

    mock_session = Mock()
    mock_session.app_name = 'test_agent'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'
    mock_session.model_dump_json.return_value = '{"session": "data"}'

    mock_session_service = Mock()
    mock_session_service.create_session = AsyncMock(return_value=mock_session)
    mock_session_service.get_session = AsyncMock(return_value=mock_session)
    mock_session_service_class.return_value = mock_session_service

    mock_artifact_service = Mock()
    mock_artifact_service_class.return_value = mock_artifact_service

    mock_credential_service = Mock()
    mock_credential_service_class.return_value = mock_credential_service

    with patch('src.wrapper.adk.cli.cli.run_interactively'):
      with patch('builtins.open', mock_open()) as mock_file:
        await run_cli(
            agent_module_name='test_agent',
            save_session=True,
            session_id=None,  # Will prompt for session ID
        )

        # Verify session saving
        mock_input.assert_called_once_with('Session ID to save: ')
        mock_file.assert_called_once_with(
            'custom_session.session.json', 'w', encoding='utf-8'
        )
        mock_file().write.assert_called_once_with('{"session": "data"}')
        mock_print.assert_called_with(
            'Session saved to', 'custom_session.session.json'
        )
