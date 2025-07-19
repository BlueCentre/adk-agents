"""Shared error handling utilities for CLI modes."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Protocol

logger = logging.getLogger(__name__)


class ErrorDisplayInterface(Protocol):
    """Interface for displaying error messages in different UI modes."""

    def display_error(self, message: str, style: str = "error") -> None:
        """Display an error message."""
        ...

    def display_warning(self, message: str, style: str = "warning") -> None:
        """Display a warning message."""
        ...

    def display_info(self, message: str, style: str = "info") -> None:
        """Display an info message."""
        ...


class ErrorHandler:
    """Shared error handling utilities for CLI modes."""

    def __init__(self, display_interface: ErrorDisplayInterface):
        self.display_interface = display_interface

    def handle_missing_function_error(self, error: ValueError) -> bool:
        """
        Handle missing function errors gracefully.

        Args:
            error: The ValueError exception to handle

        Returns:
            True if this was a missing function error that was handled, False otherwise
        """
        error_msg = str(error)
        if "Function" in error_msg and "is not found in the tools_dict" in error_msg:
            # Extract function name from error message
            match = re.search(r"Function (\w+) is not found in the tools_dict", error_msg)
            missing_function = match.group(1) if match else "unknown function"

            # Display user-friendly error messages
            self.display_interface.display_warning(
                f"⚠️  The agent tried to call a function '{missing_function}' that doesn't exist."
            )
            self.display_interface.display_info(
                "💡 This is likely a hallucination. The agent can answer your question without this function."
            )
            self.display_interface.display_info(
                "✅ You can rephrase your question or ask the agent to use available tools instead."
            )

            # Log the error for debugging
            logger.warning(f"Agent attempted to call missing function: {missing_function}")
            logger.debug(f"Full error: {error_msg}")

            return True

        return False

    def handle_general_error(self, error: Exception) -> None:
        """
        Handle general unexpected errors.

        Args:
            error: The exception to handle
        """
        error_msg = str(error)
        self.display_interface.display_error(f"❌ An unexpected error occurred: {error_msg}")
        self.display_interface.display_info(
            "💡 You can try rephrasing your question or continue with a new request."
        )

        # Log the error for debugging
        logger.error(f"Unexpected error during agent execution: {error}", exc_info=True)

    @staticmethod
    def handle_mcp_cleanup_error(error: Exception) -> bool:
        """
        Handle MCP client library cleanup errors gracefully.

        Args:
            error: The exception to check and handle

        Returns:
            True if this was a handled MCP cleanup error, False if it should be re-raised
        """
        error_msg = str(error)
        exception_str = str(type(error).__name__)

        # Check if this is a known MCP cleanup error
        is_mcp_cleanup_error = any(
            [
                "Attempted to exit cancel scope in a different task" in error_msg,
                "stdio_client" in error_msg,
                "MCP session cleanup" in error_msg,
                "CancelledError" in error_msg,
                "CancelledError" in exception_str,
                "cancel scope" in error_msg.lower(),
                isinstance(error, asyncio.CancelledError),
            ]
        )

        if is_mcp_cleanup_error:
            logger.warning(
                f"MCP cleanup completed with expected async context warnings: {error_msg}"
            )
            return True

        return False


class ConsoleErrorDisplay:
    """Error display implementation for console/prompt-toolkit UI."""

    def __init__(self, console, fallback_mode: bool = False, cli=None):
        # Determine the appropriate console to use
        if fallback_mode:
            self.console = console
        else:
            self.console = cli.console if cli else console
        self.fallback_mode = fallback_mode

    def display_error(self, message: str, style: str = "error") -> None:
        if self.fallback_mode:
            self.console.print(f"[red]{message}[/red]")
        else:
            self.console.print(f"[red]{message}[/red]")

    def display_warning(self, message: str, style: str = "warning") -> None:
        if self.fallback_mode:
            self.console.print(f"[yellow]{message}[/yellow]")
        else:
            self.console.print(f"[yellow]{message}[/yellow]")

    def display_info(self, message: str, style: str = "info") -> None:
        if self.fallback_mode:
            self.console.print(f"[blue]{message}[/blue]")
        else:
            self.console.print(f"[green]{message}[/green]")


class TUIErrorDisplay:
    """Error display implementation for Textual UI."""

    def __init__(self, tui_app):
        self.tui_app = tui_app

    def display_error(self, message: str, style: str = "error") -> None:
        self.tui_app.add_output(message, author="System", rich_format=True, style="error")

    def display_warning(self, message: str, style: str = "warning") -> None:
        self.tui_app.add_output(message, author="System", rich_format=True, style="warning")

    def display_info(self, message: str, style: str = "info") -> None:
        self.tui_app.add_output(message, author="System", rich_format=True, style="info")
