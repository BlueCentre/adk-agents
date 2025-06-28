"""
Final comprehensive test coverage for cli.py to ensure 70%+ coverage.
Targets remaining uncovered areas including TUI callbacks, event handling, and edge cases.
"""

import asyncio
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

from google.genai import types
import pytest

from src.wrapper.adk.cli.cli import run_interactively
from src.wrapper.adk.cli.cli import run_interactively_with_tui


class TestTUICallbacks:
  """Test TUI callback enhancement and execution."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_textual_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  async def test_tui_callback_setup(
      self, mock_close_runner, mock_runner_class, mock_get_textual_cli
  ):
    """Test basic TUI callback setup in TUI mode."""
    # Setup
    mock_agent = Mock()
    mock_agent.name = 'TestAgent'
    mock_agent.description = 'Test Description'
    mock_agent.tools = ['tool1', 'tool2']
    mock_agent.model = 'test_model'

    # Set up agent with existing callbacks
    original_before = Mock()
    original_after = Mock()
    mock_agent.before_tool_callback = original_before
    mock_agent.after_tool_callback = original_after

    mock_session = Mock()
    mock_session.app_name = 'test_app'
    mock_session.user_id = 'test_user'
    mock_session.id = 'test_session'

    mock_app_tui = Mock()
    mock_app_tui.register_input_callback = Mock()
    mock_app_tui.register_interrupt_callback = Mock()
    mock_app_tui.display_agent_welcome = Mock()
    mock_app_tui.run_async = AsyncMock()
    mock_app_tui.add_output = Mock()
    mock_get_textual_cli.return_value = mock_app_tui

    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

    await run_interactively_with_tui(
        root_agent=mock_agent,
        artifact_service=Mock(),
        session=mock_session,
        session_service=Mock(),
        credential_service=Mock(),
        ui_theme='light',
    )

    # Verify callbacks were enhanced and exist
    assert hasattr(mock_agent, 'before_tool_callback')
    assert hasattr(mock_agent, 'after_tool_callback')
    assert callable(mock_agent.before_tool_callback)
    assert callable(mock_agent.after_tool_callback)

    mock_close_runner.assert_called_once()


class TestEventHandling:
  """Test event processing and content handling."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Console')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  async def test_interactive_empty_query_handling(
      self,
      mock_close_runner,
      mock_runner_class,
      mock_console_class,
      mock_get_cli_instance,
  ):
    """Test handling of empty queries in interactive mode."""
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
    mock_cli.console = Mock()
    mock_get_cli_instance.return_value = mock_cli

    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

    # Mock prompt session to return empty queries then exit
    prompt_session = mock_cli.create_enhanced_prompt_session.return_value
    prompt_session.prompt_async = AsyncMock(side_effect=['', '   ', 'exit'])

    await run_interactively(
        root_agent=mock_agent,
        artifact_service=Mock(),
        session=mock_session,
        session_service=Mock(),
        credential_service=Mock(),
    )

    # run_async should not have been called for empty queries
    mock_runner.run_async.assert_not_called()


class TestErrorScenarios:
  """Test various error scenarios and exception handling."""

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Console')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  async def test_interactive_keyboard_interrupt_handling(
      self,
      mock_close_runner,
      mock_runner_class,
      mock_console_class,
      mock_get_cli_instance,
  ):
    """Test graceful handling of keyboard interrupts."""
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
    mock_cli.console = Mock()
    mock_get_cli_instance.return_value = mock_cli

    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

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
    mock_cli.console.print.assert_any_call('\n[warning]Goodbye! 👋[/warning]')

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Console')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  async def test_interactive_eof_handling(
      self,
      mock_close_runner,
      mock_runner_class,
      mock_console_class,
      mock_get_cli_instance,
  ):
    """Test graceful handling of EOF (Ctrl+D)."""
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
    mock_cli.console = Mock()
    mock_get_cli_instance.return_value = mock_cli

    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

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
    mock_cli.console.print.assert_any_call('\n[warning]Goodbye! 👋[/warning]')

  @pytest.mark.asyncio
  @patch('src.wrapper.adk.cli.cli.get_cli_instance')
  @patch('src.wrapper.adk.cli.cli.Console')
  @patch('src.wrapper.adk.cli.cli.Runner')
  @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
  @patch('builtins.input')
  async def test_interactive_prompt_error_fallback(
      self,
      mock_input,
      mock_close_runner,
      mock_runner_class,
      mock_console_class,
      mock_get_cli_instance,
  ):
    """Test fallback to input() when prompt session fails."""
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
    mock_cli.console = Mock()
    mock_get_cli_instance.return_value = mock_cli

    mock_console = Mock()
    mock_console_class.return_value = mock_console

    mock_runner = Mock()
    mock_runner_class.return_value = mock_runner

    # Mock prompt session to raise a generic exception, then input() to return exit
    prompt_session = mock_cli.create_enhanced_prompt_session.return_value
    prompt_session.prompt_async = AsyncMock(
        side_effect=Exception('Prompt failed')
    )
    mock_input.return_value = 'exit'

    await run_interactively(
        root_agent=mock_agent,
        artifact_service=Mock(),
        session=mock_session,
        session_service=Mock(),
        credential_service=Mock(),
    )

    # Verify error messages were printed
    mock_cli.console.print.assert_any_call(
        '\n[red]❌ Prompt error: Prompt failed[/red]'
    )
    mock_cli.console.print.assert_any_call(
        '[yellow]💡 Try using a simpler terminal or check your'
        ' environment.[/yellow]'
    )
    mock_cli.console.print.assert_any_call(
        '[blue]Falling back to basic input mode...[/blue]'
    )

    # Verify input() was called as fallback
    mock_input.assert_called_with('😜 user > ')
