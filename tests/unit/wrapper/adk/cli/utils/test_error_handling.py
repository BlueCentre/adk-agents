import asyncio
from unittest.mock import MagicMock, call, patch

import pytest

from src.wrapper.adk.cli.utils.error_handling import (
    ConsoleErrorDisplay,
    ErrorDisplayInterface,
    ErrorHandler,
    TUIErrorDisplay,
)


class MockConsole:
    def print(self, message):
        pass


class MockCli:
    def __init__(self):
        self.console = MagicMock()


class MockTUIApp:
    def add_output(self, message, author, rich_format, style):
        pass


@pytest.fixture
def mock_display_interface():
    return MagicMock(spec=ErrorDisplayInterface)


@pytest.fixture
def error_handler(mock_display_interface):
    return ErrorHandler(mock_display_interface)


@pytest.fixture(autouse=True)
def mock_logger():
    # Mock the logger to capture calls - use the correct module name
    with patch("src.wrapper.adk.cli.utils.error_handling.logger") as mock_log:
        yield mock_log


# --- Test ConsoleErrorDisplay ---


def test_console_error_display_error_normal_mode():
    mock_console = MagicMock(spec=MockConsole)
    mock_cli = MockCli()
    display = ConsoleErrorDisplay(console=mock_console, cli=mock_cli, fallback_mode=False)
    display.display_error("Test Error")
    mock_cli.console.print.assert_called_once_with("[red]Test Error[/red]")


def test_console_error_display_warning_normal_mode():
    mock_console = MagicMock(spec=MockConsole)
    mock_cli = MockCli()
    display = ConsoleErrorDisplay(console=mock_console, cli=mock_cli, fallback_mode=False)
    display.display_warning("Test Warning")
    mock_cli.console.print.assert_called_once_with("[yellow]Test Warning[/yellow]")


def test_console_error_display_info_normal_mode():
    mock_console = MagicMock(spec=MockConsole)
    mock_cli = MockCli()
    display = ConsoleErrorDisplay(console=mock_console, cli=mock_cli, fallback_mode=False)
    display.display_info("Test Info")
    mock_cli.console.print.assert_called_once_with("[green]Test Info[/green]")


def test_console_error_display_error_fallback_mode():
    mock_console = MagicMock(spec=MockConsole)
    display = ConsoleErrorDisplay(console=mock_console, fallback_mode=True)
    display.display_error("Fallback Error")
    mock_console.print.assert_called_once_with("[red]Fallback Error[/red]")


def test_console_error_display_warning_fallback_mode():
    mock_console = MagicMock(spec=MockConsole)
    display = ConsoleErrorDisplay(console=mock_console, fallback_mode=True)
    display.display_warning("Fallback Warning")
    mock_console.print.assert_called_once_with("[yellow]Fallback Warning[/yellow]")


def test_console_error_display_info_fallback_mode():
    mock_console = MagicMock(spec=MockConsole)
    display = ConsoleErrorDisplay(console=mock_console, fallback_mode=True)
    display.display_info("Fallback Info")
    mock_console.print.assert_called_once_with("[blue]Fallback Info[/blue]")


# --- Test TUIErrorDisplay ---


def test_tui_error_display_error():
    mock_tui_app = MagicMock(spec=MockTUIApp)
    display = TUIErrorDisplay(tui_app=mock_tui_app)
    display.display_error("TUI Error")
    mock_tui_app.add_output.assert_called_once_with(
        "TUI Error", author="System", rich_format=True, style="error"
    )


def test_tui_error_display_warning():
    mock_tui_app = MagicMock(spec=MockTUIApp)
    display = TUIErrorDisplay(tui_app=mock_tui_app)
    display.display_warning("TUI Warning")
    mock_tui_app.add_output.assert_called_once_with(
        "TUI Warning", author="System", rich_format=True, style="warning"
    )


def test_tui_error_display_info():
    mock_tui_app = MagicMock(spec=MockTUIApp)
    display = TUIErrorDisplay(tui_app=mock_tui_app)
    display.display_info("TUI Info")
    mock_tui_app.add_output.assert_called_once_with(
        "TUI Info", author="System", rich_format=True, style="info"
    )


# --- Test ErrorHandler.handle_missing_function_error ---


def test_handle_missing_function_error_valid_match(
    error_handler, mock_display_interface, mock_logger
):
    error = ValueError("Function my_func is not found in the tools_dict")
    result = error_handler.handle_missing_function_error(error)

    assert result is True
    mock_display_interface.display_warning.assert_called_once_with(
        "⚠️  The agent tried to call a function 'my_func' that doesn't exist."
    )
    mock_display_interface.display_info.assert_has_calls(
        [
            call(
                "💡 This is likely a hallucination. The agent can answer your question without "
                "this function."
            ),
            call(
                "✅ You can rephrase your question or ask the agent to use available tools instead."
            ),
        ]
    )
    mock_logger.warning.assert_called_once_with("Agent attempted to call missing function: my_func")
    mock_logger.debug.assert_called_once_with(f"Full error: {error}")


def test_handle_missing_function_error_no_match(error_handler, mock_display_interface, mock_logger):
    error = ValueError("Some other unrelated error happened.")
    result = error_handler.handle_missing_function_error(error)

    assert result is False
    mock_display_interface.display_warning.assert_not_called()
    mock_display_interface.display_info.assert_not_called()
    mock_logger.warning.assert_not_called()
    mock_logger.debug.assert_not_called()


def test_handle_missing_function_error_partial_match_unknown_function(
    error_handler, mock_display_interface, mock_logger
):
    error = ValueError("Function is not found in the tools_dict")
    result = error_handler.handle_missing_function_error(error)

    assert result is True
    mock_display_interface.display_warning.assert_called_once_with(
        "⚠️  The agent tried to call a function 'unknown function' that doesn't exist."
    )
    mock_display_interface.display_info.assert_has_calls(
        [
            call(
                "💡 This is likely a hallucination. The agent can answer your question without "
                "this function."
            ),
            call(
                "✅ You can rephrase your question or ask the agent to use available tools instead."
            ),
        ]
    )
    mock_logger.warning.assert_called_once_with(
        "Agent attempted to call missing function: unknown function"
    )
    mock_logger.debug.assert_called_once_with(f"Full error: {error}")


# --- Test ErrorHandler.handle_general_error ---


def test_handle_general_error(error_handler, mock_display_interface, mock_logger):
    error = RuntimeError("A general unexpected problem.")
    error_handler.handle_general_error(error)

    mock_display_interface.display_error.assert_called_once_with(
        "❌ An unexpected error occurred: A general unexpected problem."
    )
    mock_display_interface.display_info.assert_called_once_with(
        "💡 You can try rephrasing your question or continue with a new request."
    )
    mock_logger.error.assert_called_once_with(
        f"Unexpected error during agent execution: {error}", exc_info=True
    )


def test_handle_general_error_type_error(error_handler, mock_display_interface, mock_logger):
    error = TypeError("Invalid operation.")
    error_handler.handle_general_error(error)

    mock_display_interface.display_error.assert_called_once_with(
        "❌ An unexpected error occurred: Invalid operation."
    )
    mock_display_interface.display_info.assert_called_once_with(
        "💡 You can try rephrasing your question or continue with a new request."
    )
    mock_logger.error.assert_called_once_with(
        f"Unexpected error during agent execution: {error}", exc_info=True
    )


# --- Test ErrorHandler.handle_mcp_cleanup_error ---


@pytest.mark.parametrize(
    "error_message, exception_type",
    [
        ("Attempted to exit cancel scope in a different task", Exception),
        ("Error in stdio_client communication", Exception),
        ("MCP session cleanup failed", Exception),
        ("Some other error with CancelledError in message", Exception),
        ("CancelledError: Operation cancelled", asyncio.CancelledError),
        ("Custom CancelledError", type("CustomCancelledError", (asyncio.CancelledError,), {})),
        ("Error with cancel scope keyword", Exception),
    ],
)
def test_handle_mcp_cleanup_error_matches(error_message, exception_type, mock_logger):
    error = exception_type(error_message)
    result = ErrorHandler.handle_mcp_cleanup_error(error)

    assert result is True
    mock_logger.warning.assert_called_once_with(
        f"MCP cleanup completed with expected async context warnings: {error_message}"
    )


def test_handle_mcp_cleanup_error_no_match(mock_logger):
    error = ValueError("A completely unrelated error.")
    result = ErrorHandler.handle_mcp_cleanup_error(error)

    assert result is False
    mock_logger.warning.assert_not_called()
