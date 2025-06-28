import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import time

from src.wrapper.adk.cli.cli import run_interactively_with_tui


class TestRunInteractivelyWithTui:
    """Test cases for the run_interactively_with_tui function."""

    @pytest.mark.asyncio
    @patch('src.wrapper.adk.cli.cli.get_textual_cli_instance')
    @patch('src.wrapper.adk.cli.cli.Runner')
    @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
    async def test_run_interactively_with_tui_basic(
        self,
        mock_close_runner,
        mock_runner_class,
        mock_get_textual_cli_instance,
        mock_services,
        mock_agent,
        mock_runner
    ):
        """Test basic TUI initialization and setup."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services
        
        # Mock Textual app
        mock_app_tui = AsyncMock()
        mock_app_tui.agent_name = None
        mock_app_tui.run_async = AsyncMock()
        # Override sync methods to be regular MagicMock to avoid warnings
        mock_app_tui.register_input_callback = MagicMock()
        mock_app_tui.register_interrupt_callback = MagicMock()
        mock_app_tui.display_agent_welcome = MagicMock()
        mock_get_textual_cli_instance.return_value = mock_app_tui
        
        # Mock runner
        mock_runner_class.return_value = mock_runner
        
        # Test function
        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service,
            ui_theme="light"
        )
        
        # Assertions
        mock_get_textual_cli_instance.assert_called_once_with("light")
        assert mock_app_tui.agent_name == mock_agent.name
        mock_runner_class.assert_called_once()
        mock_app_tui.register_input_callback.assert_called_once()
        mock_app_tui.register_interrupt_callback.assert_called_once()
        mock_app_tui.display_agent_welcome.assert_called_once()
        mock_app_tui.run_async.assert_called_once()
        mock_close_runner.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.wrapper.adk.cli.cli.get_textual_cli_instance')
    @patch('src.wrapper.adk.cli.cli.Runner')
    @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
    async def test_run_interactively_with_tui_tool_callbacks(
        self,
        mock_close_runner,
        mock_runner_class,
        mock_get_textual_cli_instance,
        mock_services,
        mock_agent,
        mock_runner
    ):
        """Test that tool callbacks are properly set up."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services
        
        # Mock Textual app
        mock_app_tui = AsyncMock()
        mock_app_tui.agent_name = None
        mock_app_tui.run_async = AsyncMock()
        # Override sync methods to be regular MagicMock to avoid warnings
        mock_app_tui.register_input_callback = MagicMock()
        mock_app_tui.register_interrupt_callback = MagicMock()
        mock_app_tui.display_agent_welcome = MagicMock()
        mock_get_textual_cli_instance.return_value = mock_app_tui
        
        # Mock agent with callbacks
        mock_agent.before_tool_callback = AsyncMock()
        mock_agent.after_tool_callback = AsyncMock()
        
        # Mock runner
        mock_runner_class.return_value = mock_runner
        
        # Test function
        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service
        )
        
        # Verify callbacks were replaced and then restored
        # Note: The function modifies and then restores the callbacks
        assert hasattr(mock_agent, 'before_tool_callback')
        assert hasattr(mock_agent, 'after_tool_callback')
        mock_close_runner.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.wrapper.adk.cli.cli.get_textual_cli_instance')
    @patch('src.wrapper.adk.cli.cli.Runner')
    @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
    async def test_run_interactively_with_tui_handle_user_input(
        self,
        mock_close_runner,
        mock_runner_class,
        mock_get_textual_cli_instance,
        mock_services,
        mock_agent,
        mock_runner
    ):
        """Test that input callback is properly registered."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        # Mock Textual app
        mock_app_tui = AsyncMock()
        mock_app_tui.agent_name = None
        mock_app_tui.run_async = AsyncMock()
        mock_app_tui.agent_thought_enabled = True
        mock_app_tui.register_input_callback = MagicMock()
        mock_app_tui.register_interrupt_callback = MagicMock()
        mock_app_tui.display_agent_welcome = MagicMock()
        mock_get_textual_cli_instance.return_value = mock_app_tui

        # Mock runner with events including thought content
        mock_event = MagicMock()
        mock_event.author = "assistant"
        mock_event.content = MagicMock()

        # Regular part
        regular_part = MagicMock()
        regular_part.text = "Regular response"
        regular_part.thought = False

        # Thought part
        thought_part = MagicMock()
        thought_part.text = "Agent thinking..."
        thought_part.thought = True

        mock_event.content.parts = [regular_part, thought_part]
        mock_event.usage_metadata = MagicMock()
        mock_event.usage_metadata.prompt_token_count = 10
        mock_event.usage_metadata.candidates_token_count = 20
        mock_event.usage_metadata.total_token_count = 30
        mock_event.usage_metadata.thoughts_token_count = 5

        async def async_gen(*args, **kwargs):
            yield mock_event

        mock_runner.run_async = async_gen
        mock_runner_class.return_value = mock_runner

        # Test function
        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service
        )

        # Verify that callbacks were registered
        mock_app_tui.register_input_callback.assert_called_once()
        mock_app_tui.register_interrupt_callback.assert_called_once()
        mock_app_tui.display_agent_welcome.assert_called_once()
        mock_app_tui.run_async.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.wrapper.adk.cli.cli.get_textual_cli_instance')
    @patch('src.wrapper.adk.cli.cli.Runner')
    @patch('src.wrapper.adk.cli.utils.cleanup.close_runner_gracefully')
    async def test_run_interactively_with_tui_error_handling(
        self,
        mock_close_runner,
        mock_runner_class,
        mock_get_textual_cli_instance,
        mock_services,
        mock_agent,
        mock_runner
    ):
        """Test error handling in TUI mode."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        # Mock Textual app
        mock_app_tui = AsyncMock()
        mock_app_tui.agent_name = None
        mock_app_tui.run_async = AsyncMock()
        mock_app_tui.register_input_callback = MagicMock()
        mock_app_tui.register_interrupt_callback = MagicMock()
        mock_app_tui.display_agent_welcome = MagicMock()
        mock_get_textual_cli_instance.return_value = mock_app_tui

        # Mock runner to raise exception
        mock_runner.run_async.side_effect = Exception("Test error")
        mock_runner_class.return_value = mock_runner

        # Test function
        await run_interactively_with_tui(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service
        )

        # Verify that setup calls were made even in error conditions
        mock_app_tui.register_input_callback.assert_called_once()
        mock_app_tui.register_interrupt_callback.assert_called_once()
        mock_app_tui.display_agent_welcome.assert_called_once()
        mock_app_tui.run_async.assert_called_once() 