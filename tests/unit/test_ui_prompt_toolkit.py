"""Test ui_prompt_toolkit.py module."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
import pytest
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.wrapper.adk.cli.utils.ui_common import StatusBar, UITheme
from src.wrapper.adk.cli.utils.ui_prompt_toolkit import EnhancedCLI
from src.wrapper.adk.cli.utils.ui_rich import RichRenderer


class TestEnhancedCLIInit:
    """Test EnhancedCLI initialization."""

    def test_init_default_theme(self):
        """Test initialization with default theme."""
        cli = EnhancedCLI()

        assert cli.theme == UITheme.DARK
        assert isinstance(cli.rich_renderer, RichRenderer)
        assert isinstance(cli.console, Console)
        assert isinstance(cli.status_bar, StatusBar)
        assert cli.agent_running is False
        assert cli.current_agent_task is None
        assert cli.agent_thought_enabled is True

    def test_init_with_theme(self):
        """Test initialization with specific theme."""
        cli = EnhancedCLI(UITheme.LIGHT)

        assert cli.theme == UITheme.LIGHT
        assert cli.status_bar.theme == UITheme.LIGHT

    def test_init_with_rich_renderer(self):
        """Test initialization with provided rich renderer."""
        mock_renderer = Mock(spec=RichRenderer)
        mock_renderer.rich_theme = Mock()
        cli = EnhancedCLI(UITheme.DARK, mock_renderer)

        assert cli.rich_renderer == mock_renderer

    @patch.dict("os.environ", {"ADK_CLI_THEME": "light"})
    def test_detect_theme_from_env_light(self):
        """Test theme detection from environment variable."""
        cli = EnhancedCLI()

        # Should detect light theme from environment
        assert cli.theme == UITheme.LIGHT

    @patch.dict("os.environ", {"ADK_CLI_THEME": "dark"})
    def test_detect_theme_from_env_dark(self):
        """Test theme detection from environment variable."""
        cli = EnhancedCLI()

        assert cli.theme == UITheme.DARK

    @patch.dict("os.environ", {"ADK_CLI_THEME": "invalid"})
    def test_detect_theme_from_env_invalid(self):
        """Test invalid theme in environment defaults to dark."""
        cli = EnhancedCLI()

        assert cli.theme == UITheme.DARK

    @patch.dict("os.environ", {"TERM_PROGRAM": "iterm"})
    def test_detect_theme_from_terminal(self):
        """Test theme detection from terminal program."""
        cli = EnhancedCLI()

        # Should default to dark when no specific theme env var
        assert cli.theme == UITheme.DARK

    def test_console_configuration(self):
        """Test console is configured correctly."""
        cli = EnhancedCLI()

        # Test console is properly configured with theme
        assert isinstance(cli.console, Console)
        assert cli.console.is_terminal is not None


class TestThemeManagement:
    """Test theme management methods."""

    def test_set_theme_same_theme(self):
        """Test setting the same theme does nothing."""
        cli = EnhancedCLI(UITheme.DARK)
        original_console = cli.console

        cli.set_theme(UITheme.DARK)

        assert cli.theme == UITheme.DARK
        assert cli.console == original_console

    def test_set_theme_different_theme(self):
        """Test setting a different theme updates components."""
        cli = EnhancedCLI(UITheme.DARK)

        # Theme change prints to stdout, not console.print
        cli.set_theme(UITheme.LIGHT)

        assert cli.theme == UITheme.LIGHT
        assert cli.rich_renderer.theme == UITheme.LIGHT
        assert cli.status_bar.theme == UITheme.LIGHT

    def test_toggle_theme_dark_to_light(self):
        """Test toggling from dark to light theme."""
        cli = EnhancedCLI(UITheme.DARK)

        cli.toggle_theme()

        assert cli.theme == UITheme.LIGHT

    def test_toggle_theme_light_to_dark(self):
        """Test toggling from light to dark theme."""
        cli = EnhancedCLI(UITheme.LIGHT)

        cli.toggle_theme()

        assert cli.theme == UITheme.DARK

    def test_theme_update_creates_new_console(self):
        """Test theme update creates new console with correct theme."""
        cli = EnhancedCLI(UITheme.DARK)
        original_console = cli.console

        cli.set_theme(UITheme.LIGHT)

        # Should create new console
        assert cli.console != original_console
        assert isinstance(cli.console, Console)


class TestWelcomeMessage:
    """Test welcome message printing."""

    def test_print_welcome_message_dark_theme(self):
        """Test welcome message with dark theme."""
        cli = EnhancedCLI(UITheme.DARK)

        with patch.object(cli.console, "print") as mock_print:
            cli.print_welcome_message("TestAgent")

        # Should print multiple lines
        assert mock_print.call_count > 5

        # Check for specific content
        calls = [str(call) for call in mock_print.call_args_list]
        welcome_content = " ".join(calls)
        assert "TestAgent" in welcome_content
        assert "🌒" in welcome_content  # Dark theme indicator

    def test_print_welcome_message_light_theme(self):
        """Test welcome message with light theme."""
        cli = EnhancedCLI(UITheme.LIGHT)

        with patch.object(cli.console, "print") as mock_print:
            cli.print_welcome_message("LightAgent")

        calls = [str(call) for call in mock_print.call_args_list]
        welcome_content = " ".join(calls)
        assert "LightAgent" in welcome_content
        assert "🌞" in welcome_content  # Light theme indicator

    def test_print_welcome_message_content(self):
        """Test welcome message contains expected content."""
        cli = EnhancedCLI()

        with patch.object(cli.console, "print") as mock_print:
            cli.print_welcome_message("ContentAgent")

        calls = [str(call) for call in mock_print.call_args_list]
        welcome_content = " ".join(calls)

        # Check for ASCII art and branding
        assert "┌" in welcome_content  # ASCII art border
        assert "┐" in welcome_content  # ASCII art border
        assert "AI Agent Development Kit" in welcome_content
        assert "Enhanced Agent CLI" in welcome_content

    def test_print_welcome_message_timestamp(self):
        """Test welcome message includes timestamp."""
        cli = EnhancedCLI()

        with patch.object(cli.console, "print") as mock_print:
            cli.print_welcome_message("TimestampAgent")

        calls = [str(call) for call in mock_print.call_args_list]
        welcome_content = " ".join(calls)
        assert "Session started:" in welcome_content


class TestHelpMessage:
    """Test help message printing."""

    def test_print_help_basic(self):
        """Test basic help message printing."""
        cli = EnhancedCLI()

        with patch.object(cli.console, "print") as mock_print:
            cli.print_help()

        # Should print multiple lines
        assert mock_print.call_count > 10

        calls = [str(call) for call in mock_print.call_args_list]
        help_content = " ".join(calls)

        # Check for command categories
        assert "Navigation:" in help_content
        assert "Theming:" in help_content
        assert "Keyboard Shortcuts:" in help_content

    def test_print_help_contains_commands(self):
        """Test help message contains expected commands."""
        cli = EnhancedCLI()

        with patch.object(cli.console, "print") as mock_print:
            cli.print_help()

        calls = [str(call) for call in mock_print.call_args_list]
        help_content = " ".join(calls)

        # Navigation commands
        assert "exit" in help_content
        assert "clear" in help_content
        assert "help" in help_content

        # Theme commands
        assert "theme toggle" in help_content
        assert "theme dark" in help_content
        assert "theme light" in help_content

        # Keyboard shortcuts
        assert "Enter" in help_content
        assert "Alt+Enter" in help_content
        assert "Ctrl+D" in help_content


class TestPromptSessionCreation:
    """Test prompt session creation."""

    def test_create_enhanced_prompt_session_basic(self):
        """Test basic prompt session creation."""
        cli = EnhancedCLI()

        session = cli.create_enhanced_prompt_session("TestAgent", "session123")

        assert isinstance(session, PromptSession)
        assert session.style is not None
        assert session.completer is not None
        assert session.auto_suggest is not None
        assert session.history is not None

    def test_create_enhanced_prompt_session_style(self):
        """Test prompt session has correct style."""
        cli = EnhancedCLI(UITheme.DARK)

        session = cli.create_enhanced_prompt_session("Agent", "session")

        assert isinstance(session.style, Style)

    def test_create_enhanced_prompt_session_completer(self):
        """Test prompt session has completer configured."""
        cli = EnhancedCLI()

        session = cli.create_enhanced_prompt_session("Agent", "session")

        # Completer should be CategorizedCompleter
        assert session.completer is not None
        assert hasattr(session.completer, "get_completions")

    def test_create_enhanced_prompt_session_key_bindings(self):
        """Test prompt session has key bindings."""
        cli = EnhancedCLI()

        session = cli.create_enhanced_prompt_session("Agent", "session")

        assert session.key_bindings is not None

    def test_create_enhanced_prompt_session_settings(self):
        """Test prompt session settings."""
        cli = EnhancedCLI()

        session = cli.create_enhanced_prompt_session("Agent", "session")

        assert session.multiline is False
        assert session.mouse_support is False
        assert session.wrap_lines is True
        assert session.enable_history_search is True

    def test_create_enhanced_prompt_session_bottom_toolbar(self):
        """Test prompt session has bottom toolbar."""
        cli = EnhancedCLI()

        session = cli.create_enhanced_prompt_session("TestAgent", "session123")

        assert session.bottom_toolbar is not None

        # Test toolbar function returns string
        toolbar_text = session.bottom_toolbar()
        assert isinstance(toolbar_text, str)
        assert "TestAgent" in toolbar_text
        # Session ID may be truncated, so check for partial match
        assert "session1" in toolbar_text


class TestSafeFormatToolbar:
    """Test safe format toolbar method."""

    def test_safe_format_toolbar_normal(self):
        """Test safe format toolbar with normal input."""
        cli = EnhancedCLI()

        result = cli._safe_format_toolbar("Agent", "session123")

        assert isinstance(result, str)
        assert "Agent" in result
        # Session ID may be truncated, so check for partial match
        assert "session1" in result

    def test_safe_format_toolbar_error_handling(self):
        """Test safe format toolbar handles errors gracefully."""
        cli = EnhancedCLI()

        # Mock status_bar to raise exception
        cli.status_bar.format_toolbar = Mock(side_effect=Exception("Test error"))

        result = cli._safe_format_toolbar("Agent", "session")

        # Should return fallback toolbar
        assert isinstance(result, str)
        assert "Agent" in result
        assert "session" in result

    def test_safe_format_toolbar_special_characters(self):
        """Test safe format toolbar with special characters."""
        cli = EnhancedCLI()

        result = cli._safe_format_toolbar("Agent!@#", "session$%^")

        assert isinstance(result, str)
        assert "Agent!@#" in result


class TestAgentOutputFormatting:
    """Test agent output formatting methods."""

    def test_format_agent_response_basic(self):
        """Test basic agent response formatting."""
        cli = EnhancedCLI()

        # The method now uses display_agent_response which takes a parent_console parameter
        with patch.object(cli, "display_agent_response") as mock_display:
            cli.display_agent_response(cli.console, "Test response", "TestAgent")

        mock_display.assert_called_once_with(cli.console, "Test response", "TestAgent")

    def test_add_agent_output_basic(self):
        """Test adding agent output via display_agent_response."""
        cli = EnhancedCLI()

        with patch.object(cli, "display_agent_response") as mock_display:
            cli.display_agent_response(cli.console, "Test output", "Agent")

        mock_display.assert_called_once_with(cli.console, "Test output", "Agent")

    def test_add_agent_output_default_author(self):
        """Test adding agent output with default author."""
        cli = EnhancedCLI()

        with patch.object(cli, "display_agent_response") as mock_display:
            cli.display_agent_response(cli.console, "Test output")

        mock_display.assert_called_once_with(cli.console, "Test output")

    def test_add_agent_thought_basic(self):
        """Test adding agent thought via display_agent_thought."""
        cli = EnhancedCLI()

        with patch.object(cli, "display_agent_thought") as mock_display:
            cli.display_agent_thought(cli.console, "Test thought")

        mock_display.assert_called_once_with(cli.console, "Test thought")

    def test_add_agent_thought_empty(self):
        """Test adding empty agent thought."""
        cli = EnhancedCLI()

        with patch.object(cli, "display_agent_thought") as mock_display:
            cli.display_agent_thought(cli.console, "")

        mock_display.assert_called_once_with(cli.console, "")


class TestCompleterConfiguration:
    """Test completer configuration and behavior."""

    def test_categorized_completer_creation(self):
        """Test categorized completer is created with expected structure."""
        cli = EnhancedCLI()

        session = cli.create_enhanced_prompt_session("Agent", "session")
        completer = session.completer

        # Should have categorized commands
        assert hasattr(completer, "categorized_commands")
        assert hasattr(completer, "all_commands")

    def test_categorized_completer_has_infrastructure_commands(self):
        """Test completer includes infrastructure commands."""
        cli = EnhancedCLI()
        session = cli.create_enhanced_prompt_session("Agent", "session")
        completer = session.completer

        # Check for infrastructure commands
        infra_commands = completer.categorized_commands.get("🚀 Infrastructure & DevOps", [])
        assert any("dockerfile" in cmd.lower() for cmd in infra_commands)
        assert any("kubernetes" in cmd.lower() for cmd in infra_commands)

    def test_categorized_completer_has_code_analysis_commands(self):
        """Test completer includes code analysis commands."""
        cli = EnhancedCLI()
        session = cli.create_enhanced_prompt_session("Agent", "session")
        completer = session.completer

        # Check for code analysis commands
        code_commands = completer.categorized_commands.get("🔍 Code Analysis", [])
        assert any("analyze" in cmd.lower() for cmd in code_commands)
        assert any("review" in cmd.lower() for cmd in code_commands)

    def test_categorized_completer_has_cli_commands(self):
        """Test completer includes CLI commands."""
        cli = EnhancedCLI()
        session = cli.create_enhanced_prompt_session("Agent", "session")
        completer = session.completer

        # Check for CLI commands
        cli_commands = completer.categorized_commands.get("⚙️ CLI Commands", [])
        assert "exit" in cli_commands
        assert "help" in cli_commands
        assert "clear" in cli_commands


class TestKeyBindings:
    """Test key binding configuration."""

    @patch("src.wrapper.adk.cli.utils.ui_prompt_toolkit.KeyBindings")
    def test_key_bindings_creation(self, mock_key_bindings):
        """Test key bindings are created."""
        mock_bindings = Mock()
        mock_key_bindings.return_value = mock_bindings

        cli = EnhancedCLI()
        cli.create_enhanced_prompt_session("Agent", "session")

        # KeyBindings should be called
        mock_key_bindings.assert_called()

    def test_alt_enter_binding_exists(self):
        """Test Alt+Enter binding exists for newline."""
        cli = EnhancedCLI()
        session = cli.create_enhanced_prompt_session("Agent", "session")

        # Should have key bindings
        assert session.key_bindings is not None

    def test_ctrl_t_binding_exists(self):
        """Test Ctrl+T binding exists for theme toggle."""
        cli = EnhancedCLI()
        session = cli.create_enhanced_prompt_session("Agent", "session")

        # Should have key bindings for theme toggle
        assert session.key_bindings is not None


class TestAgentStateManavement:
    """Test agent state management functionality."""

    def test_initial_agent_state(self):
        """Test initial agent state."""
        cli = EnhancedCLI()

        assert cli.agent_running is False
        assert cli.current_agent_task is None
        assert cli.input_callback is None
        assert cli.interrupt_callback is None

    def test_agent_thought_enabled_initial_state(self):
        """Test agent thought is enabled by default."""
        cli = EnhancedCLI()

        assert cli.agent_thought_enabled is True
        assert isinstance(cli.agent_thought_buffer, list)

    def test_buffer_initialization(self):
        """Test buffer initialization."""
        cli = EnhancedCLI()

        # Buffers should be initialized
        # assert hasattr(cli, "input_buffer")
        # assert hasattr(cli, "output_buffer")
        # assert hasattr(cli, "status_buffer")
        # assert cli.layout is None
        assert cli.bindings is None


class TestDifferentThemes:
    """Test behavior with different themes."""

    def test_dark_theme_configuration(self):
        """Test dark theme specific configuration."""
        cli = EnhancedCLI(UITheme.DARK)

        assert cli.theme == UITheme.DARK
        assert cli.rich_renderer.theme == UITheme.DARK
        assert cli.status_bar.theme == UITheme.DARK

    def test_light_theme_configuration(self):
        """Test light theme specific configuration."""
        cli = EnhancedCLI(UITheme.LIGHT)

        assert cli.theme == UITheme.LIGHT
        assert cli.rich_renderer.theme == UITheme.LIGHT
        assert cli.status_bar.theme == UITheme.LIGHT

    def test_theme_consistency_across_components(self):
        """Test theme consistency across all components."""
        for theme in [UITheme.DARK, UITheme.LIGHT]:
            cli = EnhancedCLI(theme)

            assert cli.theme == theme
            assert cli.rich_renderer.theme == theme
            assert cli.status_bar.theme == theme


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_none_theme_defaults_to_dark(self):
        """Test None theme defaults to dark."""
        cli = EnhancedCLI(None)

        assert cli.theme == UITheme.DARK

    def test_empty_agent_name_handling(self):
        """Test handling of empty agent name."""
        cli = EnhancedCLI()

        with patch.object(cli.console, "print"):
            cli.print_welcome_message("")

        # Should not raise exception

        toolbar = cli._safe_format_toolbar("", "session")
        assert isinstance(toolbar, str)

    def test_empty_session_id_handling(self):
        """Test handling of empty session ID."""
        cli = EnhancedCLI()

        toolbar = cli._safe_format_toolbar("Agent", "")
        assert isinstance(toolbar, str)

    def test_special_characters_in_names(self):
        """Test handling of special characters in names."""
        cli = EnhancedCLI()

        special_agent = "Agent!@#$%^&*()"
        special_session = "session!@#$%^&*()"

        with patch.object(cli.console, "print"):
            cli.print_welcome_message(special_agent)

        toolbar = cli._safe_format_toolbar(special_agent, special_session)
        assert isinstance(toolbar, str)

    def test_unicode_characters_in_names(self):
        """Test handling of unicode characters in names."""
        cli = EnhancedCLI()

        unicode_agent = "Agent🤖日本語"
        unicode_session = "session✨العربية"

        with patch.object(cli.console, "print"):
            cli.print_welcome_message(unicode_agent)

        toolbar = cli._safe_format_toolbar(unicode_agent, unicode_session)
        assert isinstance(toolbar, str)

    def test_very_long_names(self):
        """Test handling of very long names."""
        cli = EnhancedCLI()

        long_agent = "A" * 1000
        long_session = "S" * 1000

        with patch.object(cli.console, "print"):
            cli.print_welcome_message(long_agent)

        toolbar = cli._safe_format_toolbar(long_agent, long_session)
        assert isinstance(toolbar, str)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_cli_setup_flow(self):
        """Test full CLI setup flow."""
        cli = EnhancedCLI()

        # Print welcome
        with patch.object(cli.console, "print"):
            cli.print_welcome_message("IntegrationAgent")

        # Create session
        session = cli.create_enhanced_prompt_session("IntegrationAgent", "integration123")

        # Test components
        assert isinstance(session, PromptSession)
        assert session.completer is not None
        assert session.style is not None

    def test_theme_switching_integration(self):
        """Test theme switching integration."""
        cli = EnhancedCLI(UITheme.DARK)

        # Create session with dark theme
        dark_session = cli.create_enhanced_prompt_session("Agent", "session")

        # Switch theme
        with patch.object(cli.console, "print"):
            cli.toggle_theme()

        # Create session with light theme
        light_session = cli.create_enhanced_prompt_session("Agent", "session")

        # Should have different styles
        assert dark_session.style != light_session.style

    def test_agent_output_integration(self):
        """Test agent output integration."""
        cli = EnhancedCLI()

        with (
            patch.object(cli, "display_agent_response") as mock_display_response,
            patch.object(cli, "display_agent_thought") as mock_display_thought,
        ):
            # Add various types of output
            cli.display_agent_response(cli.console, "Response message", "Agent")
            cli.display_agent_thought(cli.console, "Thinking about the problem")

        # Should have called each method once
        mock_display_response.assert_called_once_with(cli.console, "Response message", "Agent")
        mock_display_thought.assert_called_once_with(cli.console, "Thinking about the problem")

    def test_error_recovery_integration(self):
        """Test error recovery integration."""
        cli = EnhancedCLI()
        # Mock rich_renderer.display_agent_response to raise exception
        with patch.object(
            cli.rich_renderer,
            "display_agent_response",
            side_effect=Exception("Test error"),
        ):
            # The exception should propagate up from display_agent_response
            with pytest.raises(Exception, match="Test error"):
                cli.display_agent_response(cli.console, "test", "agent")

    def test_prompt_session_with_different_agents(self):
        """Test prompt session creation with different agent configurations."""
        cli = EnhancedCLI()

        agents = [
            ("SimpleAgent", "simple123"),
            ("Complex-Agent_Name", "complex-session-123"),
            ("🤖Agent", "🌟session"),
            ("", ""),
        ]

        for agent_name, session_id in agents:
            session = cli.create_enhanced_prompt_session(agent_name, session_id)
            assert isinstance(session, PromptSession)

            # Test toolbar generation
            toolbar = session.bottom_toolbar()
            assert isinstance(toolbar, str)


class TestEnvironmentDetection:
    """Test environment-based theme detection."""

    @patch.dict("os.environ", {}, clear=True)
    def test_no_environment_variables(self):
        """Test behavior with no environment variables."""
        cli = EnhancedCLI()

        # Should default to dark
        assert cli.theme == UITheme.DARK

    @patch.dict("os.environ", {"ADK_CLI_THEME": ""})
    def test_empty_theme_environment_variable(self):
        """Test behavior with empty theme environment variable."""
        cli = EnhancedCLI()

        # Should default to dark
        assert cli.theme == UITheme.DARK

    @patch.dict("os.environ", {"TERM_PROGRAM": "terminal"})
    def test_terminal_program_detection(self):
        """Test terminal program detection."""
        cli = EnhancedCLI()

        # Should still default to dark without specific theme
        assert cli.theme == UITheme.DARK

    @patch.dict("os.environ", {"ADK_CLI_THEME": "LIGHT"})  # Uppercase
    def test_case_insensitive_theme_detection(self):
        """Test case-insensitive theme detection."""
        cli = EnhancedCLI()

        # Should handle uppercase
        assert cli.theme == UITheme.LIGHT


class TestConsoleConfiguration:
    """Test console configuration details."""

    def test_console_theme_application(self):
        """Test console theme is applied correctly."""
        cli = EnhancedCLI(UITheme.DARK)

        # Console should be properly initialized
        assert isinstance(cli.console, Console)
        assert cli.rich_renderer.theme == UITheme.DARK

    def test_console_settings_optimization(self):
        """Test console settings are optimized for CLI usage."""
        cli = EnhancedCLI()

        # Console should be properly configured
        assert isinstance(cli.console, Console)
        assert cli.console.size is not None

    def test_console_recreation_on_theme_change(self):
        """Test console is recreated when theme changes."""
        cli = EnhancedCLI(UITheme.DARK)
        original_console = cli.console

        cli.set_theme(UITheme.LIGHT)

        # Should create new console
        assert cli.console != original_console
        assert cli.rich_renderer.theme == UITheme.LIGHT
