"""Common UI abstraction interface for consistent output handling across CLI modes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Protocol

from .ui_common import UITheme


class UIOutputInterface(Protocol):
    """Protocol for UI output operations."""

    def display_message(self, message: str, style: str = "info") -> None:
        """Display a general message to the user."""
        ...

    def display_agent_response(self, text: str, author: str) -> None:
        """Display agent response text."""
        ...

    def display_agent_thought(self, text: str) -> None:
        """Display agent thought content."""
        ...

    def display_function_content(self, text: str) -> None:
        """Display function/tool execution content."""
        ...

    def display_usage_metadata(self, usage_metadata: Any, model_name: str) -> None:
        """Display token usage metadata."""
        ...

    def display_error(self, message: str) -> None:
        """Display an error message."""
        ...

    def display_warning(self, message: str) -> None:
        """Display a warning message."""
        ...

    def display_info(self, message: str) -> None:
        """Display an info message."""
        ...

    def clear_screen(self) -> None:
        """Clear the screen."""
        ...

    def display_help(self) -> None:
        """Display help information."""
        ...


class UIInputInterface(Protocol):
    """Protocol for UI input operations."""

    async def get_user_input(self, prompt: str) -> str:
        """Get user input asynchronously."""
        ...

    def register_input_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for user input."""
        ...


class UIThemeInterface(Protocol):
    """Protocol for UI theme operations."""

    def get_current_theme(self) -> UITheme:
        """Get the current UI theme."""
        ...

    def set_theme(self, theme: UITheme) -> None:
        """Set the UI theme."""
        ...

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        ...


class UILifecycleInterface(Protocol):
    """Protocol for UI lifecycle operations."""

    def initialize(self) -> None:
        """Initialize the UI."""
        ...

    def start(self) -> None:
        """Start the UI."""
        ...

    def stop(self) -> None:
        """Stop the UI."""
        ...

    def cleanup(self) -> None:
        """Clean up UI resources."""
        ...


class UnifiedUIInterface(
    UIOutputInterface,
    UIInputInterface,
    UIThemeInterface,
    UILifecycleInterface,
    Protocol,
):
    """Unified interface combining all UI operations."""

    @property
    def name(self) -> str:
        """Get the UI implementation name."""
        ...

    @property
    def is_interactive(self) -> bool:
        """Check if the UI supports interactive input."""
        ...

    @property
    def supports_rich_content(self) -> bool:
        """Check if the UI supports rich content rendering."""
        ...


class BaseUIAdapter(ABC):
    """Base adapter class for UI implementations."""

    def __init__(self, ui_theme: Optional[UITheme] = None):
        self.ui_theme = ui_theme or UITheme.DARK
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the UI implementation name."""
        pass

    @property
    @abstractmethod
    def is_interactive(self) -> bool:
        """Check if the UI supports interactive input."""
        pass

    @property
    @abstractmethod
    def supports_rich_content(self) -> bool:
        """Check if the UI supports rich content rendering."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the UI."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Start the UI."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the UI."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up UI resources."""
        pass

    def get_current_theme(self) -> UITheme:
        """Get the current UI theme."""
        return self.ui_theme

    def set_theme(self, theme: UITheme) -> None:
        """Set the UI theme."""
        self.ui_theme = theme

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.ui_theme = UITheme.LIGHT if self.ui_theme == UITheme.DARK else UITheme.DARK


class ConsoleUIAdapter(BaseUIAdapter):
    """UI adapter for console/prompt-toolkit implementations."""

    def __init__(
        self,
        console,
        cli=None,
        fallback_mode: bool = False,
        ui_theme: Optional[UITheme] = None,
    ):
        super().__init__(ui_theme)
        self.console = console
        self.cli = cli
        self.fallback_mode = fallback_mode
        self.input_callbacks = []

    @property
    def name(self) -> str:
        return "Console" if self.fallback_mode else "Enhanced Console"

    @property
    def is_interactive(self) -> bool:
        return True

    @property
    def supports_rich_content(self) -> bool:
        return not self.fallback_mode

    def initialize(self) -> None:
        """Initialize the console UI."""
        self._initialized = True

    def start(self) -> None:
        """Start the console UI."""
        if not self._initialized:
            self.initialize()

    def stop(self) -> None:
        """Stop the console UI."""
        pass

    def cleanup(self) -> None:
        """Clean up console resources."""
        pass

    def display_message(self, message: str, style: str = "info") -> None:
        style_map = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "success": "green",
        }
        color = style_map.get(style, "blue")
        self.console.print(f"[{color}]{message}[/{color}]")

    def display_agent_response(self, text: str, author: str) -> None:
        if not self.fallback_mode and self.cli:
            self.cli.display_agent_response(self.console, text, author)
        else:
            self.console.print(f"🤖 {author} > {text}")

    def display_agent_thought(self, text: str) -> None:
        if not self.fallback_mode and self.cli:
            self.cli.display_agent_thought(self.console, text)

    def display_function_content(self, text: str) -> None:
        self.console.print(f"🔧 Tool: {text}")

    def display_usage_metadata(self, usage_metadata: Any, model_name: str) -> None:
        # Console mode doesn't typically display usage metadata
        pass

    def display_error(self, message: str) -> None:
        self.console.print(f"[red]{message}[/red]")

    def display_warning(self, message: str) -> None:
        self.console.print(f"[yellow]{message}[/yellow]")

    def display_info(self, message: str) -> None:
        self.console.print(f"[green]{message}[/green]")

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

    async def get_user_input(self, prompt: str) -> str:
        """Get user input from console."""
        # This would need to be implemented based on the specific console setup
        raise NotImplementedError(
            "Console input handling needs specific implementation"
        )

    def register_input_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for user input."""
        self.input_callbacks.append(callback)

    def set_theme(self, theme: UITheme) -> None:
        """Set the UI theme."""
        super().set_theme(theme)
        if self.cli:
            self.cli.set_theme(theme)

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        super().toggle_theme()
        if self.cli:
            self.cli.toggle_theme()


class TUIAdapter(BaseUIAdapter):
    """UI adapter for Textual TUI implementations."""

    def __init__(self, tui_app, ui_theme: Optional[UITheme] = None):
        super().__init__(ui_theme)
        self.tui_app = tui_app
        self.input_callbacks = []

    @property
    def name(self) -> str:
        return "Textual TUI"

    @property
    def is_interactive(self) -> bool:
        return True

    @property
    def supports_rich_content(self) -> bool:
        return True

    def initialize(self) -> None:
        """Initialize the TUI."""
        self._initialized = True

    def start(self) -> None:
        """Start the TUI."""
        if not self._initialized:
            self.initialize()

    def stop(self) -> None:
        """Stop the TUI."""
        self.tui_app.exit()

    def cleanup(self) -> None:
        """Clean up TUI resources."""
        pass

    def display_message(self, message: str, style: str = "info") -> None:
        self.tui_app.add_output(message, rich_format=True, style=style)

    def display_agent_response(self, text: str, author: str) -> None:
        self.tui_app.add_agent_output(text, author)

    def display_agent_thought(self, text: str) -> None:
        self.tui_app.add_agent_thought(text)

    def display_function_content(self, text: str) -> None:
        self.tui_app.add_output(text, author="Tool", rich_format=True, style="accent")

    def display_usage_metadata(self, usage_metadata: Any, model_name: str) -> None:
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0)
        completion_tokens = getattr(usage_metadata, "candidates_token_count", 0)
        total_tokens = getattr(usage_metadata, "total_token_count", 0)
        thinking_tokens = getattr(usage_metadata, "thoughts_token_count", 0) or 0

        self.tui_app.display_model_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            thinking_tokens=thinking_tokens,
            model_name=model_name,
        )

    def display_error(self, message: str) -> None:
        self.tui_app.add_output(
            message, author="System", rich_format=True, style="error"
        )

    def display_warning(self, message: str) -> None:
        self.tui_app.add_output(
            message, author="System", rich_format=True, style="warning"
        )

    def display_info(self, message: str) -> None:
        self.tui_app.add_output(
            message, author="System", rich_format=True, style="info"
        )

    def clear_screen(self) -> None:
        self.tui_app.action_clear_output()

    def display_help(self) -> None:
        self.tui_app.display_user_help()

    async def get_user_input(self, prompt: str) -> str:
        """Get user input from TUI."""
        # This would be handled through the TUI's input system
        raise NotImplementedError("TUI input handling is managed through callbacks")

    def register_input_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for user input."""
        self.input_callbacks.append(callback)
        self.tui_app.register_input_callback(callback)

    def set_theme(self, theme: UITheme) -> None:
        """Set the UI theme."""
        super().set_theme(theme)
        self.tui_app._current_ui_theme = theme
        if theme == UITheme.DARK:
            self.tui_app.add_class("dark", "theme-mode")
            self.tui_app.remove_class("light", "theme-mode")
        else:
            self.tui_app.add_class("light", "theme-mode")
            self.tui_app.remove_class("dark", "theme-mode")

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        super().toggle_theme()
        self.tui_app.action_toggle_theme()


class UIAdapterFactory:
    """Factory for creating UI adapters."""

    @staticmethod
    def create_console_adapter(
        console,
        cli=None,
        fallback_mode: bool = False,
        ui_theme: Optional[UITheme] = None,
    ) -> ConsoleUIAdapter:
        """Create a console UI adapter."""
        return ConsoleUIAdapter(console, cli, fallback_mode, ui_theme)

    @staticmethod
    def create_tui_adapter(tui_app, ui_theme: Optional[UITheme] = None) -> TUIAdapter:
        """Create a TUI adapter."""
        return TUIAdapter(tui_app, ui_theme)

    @staticmethod
    def create_adapter(ui_type: str, **kwargs) -> BaseUIAdapter:
        """Create a UI adapter of the specified type."""
        if ui_type.lower() == "console":
            return UIAdapterFactory.create_console_adapter(**kwargs)
        elif ui_type.lower() == "tui":
            return UIAdapterFactory.create_tui_adapter(**kwargs)
        else:
            raise ValueError(f"Unknown UI type: {ui_type}")
