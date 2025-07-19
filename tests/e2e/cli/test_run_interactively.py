from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.wrapper.adk.cli.cli import run_interactively


class TestRunInteractively:
    """Test cases for the run_interactively function."""

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_run_interactively_basic_flow(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
        mock_services,
        mock_agent,
        mock_runner,
    ):
        """Test basic interactive flow with enhanced UI."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        # Mock CLI instance
        mock_cli = MagicMock()
        mock_cli.create_enhanced_prompt_session.return_value = AsyncMock()
        mock_cli.console = MagicMock()
        mock_get_cli_instance.return_value = mock_cli

        # Mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock runner - use a simple async generator function
        async def mock_run_async(*_, **__):
            mock_event = MagicMock()
            mock_event.author = "assistant"
            mock_event.content = MagicMock()
            mock_event.content.parts = [MagicMock()]
            mock_event.content.parts[0].text = "Test response"
            mock_event.content.parts[0].thought = False
            mock_event.usage_metadata = None
            yield mock_event

        mock_runner.run_async = mock_run_async
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session to simulate single query then exit
        mock_prompt_session = AsyncMock()

        async def prompt_side_effect(*_, **__):
            # First call returns a query, second raises KeyboardInterrupt to exit
            if not hasattr(prompt_side_effect, "call_count"):
                prompt_side_effect.call_count = 0
            prompt_side_effect.call_count += 1

            if prompt_side_effect.call_count == 1:
                return "test query"
            raise KeyboardInterrupt()

        mock_prompt_session.prompt_async.side_effect = prompt_side_effect
        mock_cli.create_enhanced_prompt_session.return_value = mock_prompt_session

        # Test function
        await run_interactively(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service,
            ui_theme="dark",
        )

        # Assertions
        mock_get_cli_instance.assert_called_once_with("dark")
        mock_cli.create_enhanced_prompt_session.assert_called()
        mock_cli.print_welcome_message.assert_called_once_with(mock_agent.name)
        mock_runner_factory.create_runner.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    @patch("prompt_toolkit.PromptSession")
    async def test_run_interactively_fallback_mode(
        self,
        mock_prompt_session_class,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
        mock_services,
        mock_agent,
        mock_runner,
    ):
        """Test fallback mode when enhanced UI fails."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        # Mock CLI instance to raise exception
        mock_get_cli_instance.side_effect = Exception("UI failed")

        # Mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock runner
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session for fallback
        mock_prompt_session = AsyncMock()
        mock_prompt_session.prompt_async.side_effect = [KeyboardInterrupt()]
        mock_prompt_session_class.return_value = mock_prompt_session

        # Test function
        await run_interactively(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service,
        )

        # Assertions
        mock_get_cli_instance.assert_called_once_with(None)
        mock_console.print.assert_any_call(
            "[warning]⚠️ Enhanced UI initialization failed: UI failed[/warning]"
        )
        mock_console.print.assert_any_call("[info]Falling back to basic CLI mode...[/info]")
        mock_runner_factory.create_runner.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_run_interactively_special_commands(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
        mock_services,
        mock_agent,
        mock_runner,
    ):
        """Test special commands (help, clear, theme) in enhanced mode."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        # Mock CLI instance
        mock_cli = MagicMock()
        mock_cli.create_enhanced_prompt_session.return_value = AsyncMock()
        mock_cli.console = MagicMock()
        mock_get_cli_instance.return_value = mock_cli

        # Mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock runner
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session to test special commands
        mock_prompt_session = AsyncMock()
        command_sequence = ["help", "clear", "theme dark", "exit"]
        mock_prompt_session.prompt_async.side_effect = command_sequence
        mock_cli.create_enhanced_prompt_session.return_value = mock_prompt_session

        # Test function
        await run_interactively(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service,
        )

        # Assertions
        mock_cli.print_help.assert_called_once()
        mock_console.clear.assert_called_once()  # Now handled by ConsoleCommandDisplay
        mock_cli.set_theme.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.wrapper.adk.cli.cli.get_cli_instance")
    @patch("src.wrapper.adk.cli.cli.Console")
    @patch("src.wrapper.adk.cli.cli.RunnerFactory")
    async def test_run_interactively_with_thought_content(
        self,
        mock_runner_factory,
        mock_console_class,
        mock_get_cli_instance,
        mock_services,
        mock_agent,
        mock_runner,
    ):
        """Test handling of thought content in enhanced mode."""
        # Setup mocks
        artifact_service, session_service, credential_service, mock_session = mock_services

        # Mock CLI instance
        mock_cli = MagicMock()
        mock_cli.create_enhanced_prompt_session.return_value = AsyncMock()
        mock_cli.console = MagicMock()
        mock_cli.agent_thought_enabled = True
        mock_cli.display_agent_response = MagicMock()
        mock_cli.display_agent_thought = MagicMock()
        mock_get_cli_instance.return_value = mock_cli

        # Mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock runner with thought content
        mock_event_with_thought = MagicMock()
        mock_event_with_thought.author = "assistant"
        mock_event_with_thought.content = MagicMock()

        # Create regular and thought parts
        regular_part = MagicMock()
        regular_part.text = "Regular response"
        regular_part.thought = False
        regular_part.function_call = False

        thought_part = MagicMock()
        thought_part.text = "Agent thinking..."
        thought_part.thought = True
        thought_part.function_call = False

        mock_event_with_thought.content.parts = [regular_part, thought_part]

        async def async_gen_with_thought(*_, **__):
            yield mock_event_with_thought

        mock_runner.run_async = async_gen_with_thought
        mock_runner_factory.create_runner.return_value = mock_runner
        mock_runner.close = AsyncMock()
        # Mock prompt session
        mock_prompt_session = AsyncMock()
        mock_prompt_session.prompt_async.side_effect = ["test query", "exit"]
        mock_cli.create_enhanced_prompt_session.return_value = mock_prompt_session

        # Test function
        await run_interactively(
            root_agent=mock_agent,
            artifact_service=artifact_service,
            session=mock_session,
            session_service=session_service,
            credential_service=credential_service,
        )

        # Assertions
        # mock_cli.add_agent_output.assert_called_once_with(
        #     "Regular response", "assistant"
        # )
        # mock_cli.add_agent_thought.assert_called_once_with("Agent thinking...")
        mock_cli.display_agent_response.assert_called_once_with(
            mock_console, "Regular response", "assistant"
        )
        mock_cli.display_agent_thought.assert_called_once_with(mock_console, "Agent thinking...")
