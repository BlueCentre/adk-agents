"""Shared command handling utilities for CLI modes."""

from __future__ import annotations

from enum import Enum
from typing import Optional, Protocol

from .ui_common import UITheme


class CommandResult(Enum):
    """Result of command processing."""

    HANDLED = "handled"
    NOT_HANDLED = "not_handled"
    EXIT_REQUESTED = "exit_requested"


class CommandDisplayInterface(Protocol):
    """Interface for displaying command results in different UI modes."""

    def display_message(self, message: str, style: str = "info") -> None:
        """Display a message to the user."""
        ...

    def clear_screen(self) -> None:
        """Clear the screen."""
        ...

    def display_help(self) -> None:
        """Display help information."""
        ...

    def exit_application(self) -> None:
        """Exit the application."""
        ...


class ThemeHandler(Protocol):
    """Interface for handling theme operations."""

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        ...

    def set_theme(self, theme: UITheme) -> None:
        """Set a specific theme."""
        ...

    def get_current_theme(self) -> UITheme:
        """Get the current theme."""
        ...


class CommandHandler:
    """Shared utilities for processing built-in commands across different CLI modes."""

    def __init__(
        self,
        display_interface: CommandDisplayInterface,
        theme_handler: ThemeHandler | None = None,
    ):
        self.display_interface = display_interface
        self.theme_handler = theme_handler

    def process_command(self, command: str) -> CommandResult:
        """
        Process a user command and return the result.

        Args:
            command: The command string to process

        Returns:
            CommandResult indicating how the command was handled
        """
        command = command.strip().lower()

        if not command:
            return CommandResult.NOT_HANDLED

        # Handle exit commands
        if command in ["exit", "quit", "bye"]:
            self.display_interface.display_message("👋 Goodbye!", "warning")
            self.display_interface.exit_application()
            return CommandResult.EXIT_REQUESTED

        # Handle clear command
        if command == "clear":
            self.display_interface.clear_screen()
            return CommandResult.HANDLED

        # Handle help command
        if command == "help":
            self.display_interface.display_help()
            return CommandResult.HANDLED

        # Handle theme commands
        if command.startswith("theme") and self.theme_handler:
            return self._handle_theme_command(command)

        # Handle toggle command (multiline input toggle for TUI)
        if command == "toggle":
            # This is TUI-specific - delegate to display interface if it supports it
            if hasattr(self.display_interface, "toggle_multiline_input"):
                self.display_interface.toggle_multiline_input()
                return CommandResult.HANDLED
            return CommandResult.NOT_HANDLED

        return CommandResult.NOT_HANDLED

    def _handle_theme_command(self, command: str) -> CommandResult:
        """Handle theme-related commands."""
        if not self.theme_handler:
            return CommandResult.NOT_HANDLED

        parts = command.split()

        if len(parts) == 1 or (len(parts) == 2 and parts[1] == "toggle"):
            # "theme" or "theme toggle"
            self.theme_handler.toggle_theme()
            current_theme = self.theme_handler.get_current_theme()
            theme_name = "dark" if current_theme == UITheme.DARK else "light"
            icon = "🌒" if current_theme == UITheme.DARK else "🌞"
            self.display_interface.display_message(f"{icon} Switched to {theme_name} theme")
            return CommandResult.HANDLED

        if len(parts) == 2 and parts[1] in ["dark", "light"]:
            # "theme dark" or "theme light"
            theme = UITheme.DARK if parts[1] == "dark" else UITheme.LIGHT
            self.theme_handler.set_theme(theme)
            theme_name = parts[1]
            icon = "🌒" if theme == UITheme.DARK else "🌞"
            self.display_interface.display_message(f"{icon} Switched to {theme_name} theme")
            return CommandResult.HANDLED

        return CommandResult.NOT_HANDLED


class ConsoleCommandDisplay:
    """Command display implementation for console/prompt-toolkit UI."""

    def __init__(self, console, cli=None, fallback_mode: bool = False):
        self.console = console
        self.cli = cli
        self.fallback_mode = fallback_mode

    def display_message(self, message: str, style: str = "info") -> None:
        style_map = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "success": "green",
        }
        color = style_map.get(style, "blue")
        self.console.print(f"[{color}]{message}[/{color}]")

    def clear_screen(self) -> None:
        self.console.clear()

    def display_help(self) -> None:
        if not self.fallback_mode and self.cli:
            self.cli.print_help()
        else:
            self.console.print("[blue]Available Commands:[/blue]")
            self.console.print("  • exit, quit, bye - Exit the CLI")
            self.console.print("  • clear - Clear the screen")
            self.console.print("  • help - Show this help message")
            if self.cli:
                self.console.print("  • theme [dark|light|toggle] - Switch UI theme")

    def exit_application(self) -> None:
        # Exit handling is managed by the calling context
        pass


class TUICommandDisplay:
    """Command display implementation for Textual UI."""

    def __init__(self, tui_app):
        self.tui_app = tui_app

    def display_message(self, message: str, style: str = "info") -> None:
        self.tui_app.add_output(message, rich_format=True, style=style)

    def clear_screen(self) -> None:
        self.tui_app.action_clear_output()

    def display_help(self) -> None:
        self.tui_app.display_user_help()

    def exit_application(self) -> None:
        self.tui_app.exit()

    def toggle_multiline_input(self) -> None:
        """Toggle multiline input mode in TUI."""
        self.tui_app.action_toggle_user_multiline_input()


class ConsoleThemeHandler:
    """Theme handler for console/prompt-toolkit UI."""

    def __init__(self, cli, prompt_session_factory):
        self.cli = cli
        self.prompt_session_factory = prompt_session_factory

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        if self.cli:
            self.cli.toggle_theme()
            # Recreate prompt session with new theme
            self.prompt_session_factory()

    def set_theme(self, theme: UITheme) -> None:
        """Set a specific theme."""
        if self.cli:
            self.cli.set_theme(theme)
            # Recreate prompt session with new theme
            self.prompt_session_factory()

    def get_current_theme(self) -> UITheme:
        """Get the current theme."""
        if self.cli:
            return self.cli.theme
        return UITheme.DARK


class TUIThemeHandler:
    """Theme handler for Textual UI."""

    def __init__(self, tui_app):
        self.tui_app = tui_app

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.tui_app.action_toggle_theme()

    def set_theme(self, theme: UITheme) -> None:
        """Set a specific theme."""
        self.tui_app._current_ui_theme = theme
        if theme == UITheme.DARK:
            self.tui_app.add_class("dark", "theme-mode")
            self.tui_app.remove_class("light", "theme-mode")
        else:
            self.tui_app.add_class("light", "theme-mode")
            self.tui_app.remove_class("dark", "theme-mode")

    def get_current_theme(self) -> UITheme:
        """Get the current theme."""
        return getattr(self.tui_app, "_current_ui_theme", UITheme.DARK)
