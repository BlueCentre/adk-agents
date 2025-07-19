from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Awaitable, Callable, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console

from .ui_common import StatusBar, ThemeConfig, UITheme
from .ui_rich import RichRenderer


class EnhancedCLI:
    """Enhanced CLI with tmux-style interface and theming."""

    def __init__(
        self,
        theme: Optional[UITheme] = None,
        rich_renderer: Optional[RichRenderer] = None,
    ):
        # Determine theme from environment or default
        self.theme = theme or self._detect_theme()
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_renderer = rich_renderer or RichRenderer(self.theme)
        # Configure console to preserve scrollback behavior
        self.console = Console(
            theme=self.rich_renderer.rich_theme,
            force_interactive=False,  # Disable animations that might interfere with scrollback
            legacy_windows=False,  # Use modern terminal features
            soft_wrap=True,  # Enable soft wrapping to prevent cropping
            width=None,  # Auto-detect width to avoid fixed sizing issues
            # height=None,  # Auto-detect height to avoid fixed sizing issues
        )
        self.status_bar = StatusBar(self.theme)

        # Interruptible CLI attributes
        self.agent_running = False
        self.current_agent_task: Optional[asyncio.Task] = None
        self.input_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self.interrupt_callback: Optional[Callable[[], Awaitable[None]]] = None

        # Agent thought display
        self.agent_thought_enabled = True
        self.agent_thought_buffer = []

        # UI Components for interruptible mode
        # self.input_buffer = Buffer(multiline=True)
        # self.output_buffer = Buffer()
        # self.status_buffer = Buffer()
        # self.layout = None  # Will be set when needed
        self.bindings = None  # Will be set when needed

    def _detect_theme(self) -> UITheme:
        """Auto-detect theme from environment variables."""
        # Check various environment variables for theme preference
        theme_env = os.getenv("ADK_CLI_THEME", "").lower()
        if theme_env in ["light", "dark"]:
            return UITheme(theme_env)

        # Check terminal background detection
        term_program = os.getenv("TERM_PROGRAM", "").lower()
        if "iterm" in term_program or "terminal" in term_program:
            # Could add more sophisticated detection here
            pass

        # Default to dark theme
        return UITheme.DARK

    def _safe_format_toolbar(self, agent_name: str, session_id: str) -> str:
        """Safely format the toolbar with error handling."""
        try:
            return self.status_bar.format_toolbar(agent_name, session_id)
        except Exception:
            # Fallback to simple toolbar if formatting fails
            return f" 🤖 {agent_name} | Session: {session_id[:8]}... | 💡 Alt+Enter:multi-line | 🚪 Ctrl+D:exit"

    # BEGIN: Used from cli.py

    def create_enhanced_prompt_session(
        self, agent_name: str = "Agent", session_id: str = "unknown"
    ) -> PromptSession:
        """Create an enhanced PromptSession with tmux-style theming."""

        # https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/key_bindings.html

        # Create custom key bindings
        bindings = KeyBindings()

        # Alt+Enter for newline
        @bindings.add("escape", "enter")
        def _(event):
            """Insert newline."""
            event.current_buffer.insert_text("\n")

        # Ctrl+T for theme toggle
        @bindings.add("c-t")
        def _(event):
            """Toggle theme with Ctrl+T."""
            self.toggle_theme()
            event.app.invalidate()  # Refresh the display

        # Create style from theme config
        style = Style.from_dict(self.theme_config)

        # Categorized agentic workflow commands for completion
        categorized_commands = {
            "🚀 Infrastructure & DevOps": [
                "create a dockerfile",
                "create docker-compose.yml",
                "write kubernetes manifests",
                "create helm chart for",
                "write terraform code for",
                "setup CI/CD pipeline",
                "configure github actions",
                "setup monitoring for",
                "add logging to",
                "create health checks",
                "setup load balancer",
                "configure autoscaling",
                "list the k8s clusters and indicate the current one",
                "list all the user applications in the qa- namespaces",
            ],
            "🔍 Code Analysis": [
                "analyze this code",
                "review the codebase",
                "find security vulnerabilities",
                "optimize performance of",
                "refactor this function",
                "add error handling to",
                "add type hints to",
                "add documentation for",
                "write unit tests for",
                "write integration tests for",
                "fix the bug in",
                "debug this issue",
            ],
            "📦 Deployment & Operations": [
                "deploy to production",
                "deploy to staging",
                "rollback deployment",
                "check service status",
                "troubleshoot deployment",
                "scale the service",
                "update dependencies",
                "backup the database",
                "restore from backup",
            ],
            "🔧 Development Workflow": [
                "create new feature branch",
                "merge pull request",
                "tag new release",
                "update changelog",
                "bump version number",
                "execute regression tests",
                "run security scan",
                "run performance tests",
                "generate documentation",
                "summarize git status & diff using https://www.conventionalcommits.org/en/v1.0.0/#specification, commit, push changes to feature branch, and create a pull request",
                "push changes",
            ],
            "⚙️ CLI Commands": [
                "exit",
                "quit",
                "bye",
                "help",
                "clear",
                "theme toggle",
                "theme dark",
                "theme light",
            ],
        }

        # Create a custom completer that shows categories

        class CategorizedCompleter(Completer):
            def __init__(self, categorized_commands):
                self.categorized_commands = categorized_commands
                # Flatten all commands for matching
                self.all_commands = []
                for category, commands in categorized_commands.items():
                    self.all_commands.extend(commands)

            def get_completions(self, document, complete_event):
                text = document.get_word_before_cursor()
                text_lower = text.lower()

                # Group completions by category
                for category, commands in self.categorized_commands.items():
                    category_matches = []
                    for command in commands:
                        if text_lower in command.lower():
                            category_matches.append(command)

                    # If we have matches in this category, yield them with category header
                    if category_matches:
                        # Add category separator (only visible in completion menu)
                        yield Completion(
                            "",
                            start_position=0,
                            display=f"{category}",
                            style="class:completion-menu.category",
                        )

                        # Add the actual completions
                        for command in category_matches:
                            start_pos = -len(text) if text else 0
                            yield Completion(
                                command,
                                start_position=start_pos,
                                display=f"  {command}",
                                style="class:completion-menu.completion",
                            )

        completer = CategorizedCompleter(categorized_commands)
        history = InMemoryHistory()

        return PromptSession(
            key_bindings=bindings,
            style=style,
            completer=completer,
            auto_suggest=AutoSuggestFromHistory(),
            history=history,
            multiline=False,
            mouse_support=False,
            wrap_lines=True,
            enable_history_search=True,
            prompt_continuation=lambda width, line_number, is_soft_wrap: "     > "
            if not is_soft_wrap
            else "",
            bottom_toolbar=lambda: self._safe_format_toolbar(agent_name, session_id),
            reserve_space_for_menu=4,
            # Preserve terminal scrollback behavior
            refresh_interval=0.1,  # Reduce refresh rate to minimize interference
            input_processors=[],  # Disable input processors that might interfere
        )

    def set_theme(self, theme: UITheme) -> None:
        """Set a specific theme."""
        if self.theme != theme:
            self.theme = theme
            self.theme_config = ThemeConfig.get_theme_config(self.theme)
            self.rich_renderer.theme = self.theme  # Update renderer's theme
            self.rich_renderer.rich_theme = ThemeConfig.get_rich_theme(self.theme)
            self.rich_renderer.console = Console(
                theme=self.rich_renderer.rich_theme,
                force_interactive=False,
                legacy_windows=False,
                soft_wrap=True,
                width=None,
                height=None,
            )
            self.status_bar.theme = self.theme
            self.console = Console(
                theme=self.rich_renderer.rich_theme,
                force_interactive=False,  # Disable animations that might interfere with scrollback
                legacy_windows=False,  # Use modern terminal features
                soft_wrap=True,  # Enable soft wrapping to prevent cropping
                width=None,  # Auto-detect width to avoid fixed sizing issues
                height=None,  # Auto-detect height to avoid fixed sizing issues
            )

            theme_name = "🌒 Dark" if self.theme == UITheme.DARK else "🌞 Light"
            self.console.print(f"[info]Set theme to {theme_name}[/info]")

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.theme = UITheme.LIGHT if self.theme == UITheme.DARK else UITheme.DARK
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_renderer.theme = self.theme  # Update renderer's theme
        self.rich_renderer.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        self.rich_renderer.console = Console(
            theme=self.rich_renderer.rich_theme,
            force_interactive=False,
            legacy_windows=False,
            soft_wrap=True,
            width=None,
            height=None,
        )
        self.status_bar.theme = self.theme
        self.console = Console(
            theme=self.rich_renderer.rich_theme,
            force_interactive=False,  # Disable animations that might interfere with scrollback
            legacy_windows=False,  # Use modern terminal features
            soft_wrap=True,  # Enable soft wrapping to prevent cropping
            width=None,  # Auto-detect width to avoid fixed sizing issues
            height=None,  # Auto-detect height to avoid fixed sizing issues
        )

        theme_name = "🌒 Dark" if self.theme == UITheme.DARK else "🌞 Light"
        self.console.print(f"[info]Switched to {theme_name} theme[/info]")

    def print_welcome_message(self, agent_name: str) -> None:
        """Print a themed welcome message with tmux-style formatting."""
        theme_indicator = "🌒" if self.theme == UITheme.DARK else "🌞"

        # Welcome ASCII Art Logo
        self.console.print()
        self.console.print(
"""
  .'|=|`.     .'|                                                         
.'  | |  `. .'  |                                                         
|   |=|   | |   |                                                         
|   | |   | |   |                                                         
|___| |___| |___|                                                         
                                                                          
                   ___         ___        ___   ___  ___   ___  ___   ___ 
  .'|=|`.     .'|=|_.'    .'|=|_.'   .'| |   | `._|=|   |=|_.' |   |=|_.' 
.'  | |  `. .'  |___    .'  |  ___ .'  |\|   |      |   |      `.  |      
|   |=|   | |   |`._|=. |   |=|_.' |   | |   |      |   |        `.|=|`.  
|   | |   | `.  |  __|| |   |  ___ |   | |  .'      `.  |       ___  |  `.
|___| |___|   `.|=|_.'' |___|=|_.' |___| |.'          `.|       `._|=|___|
"""
        )
        self.console.print()
        self.console.print(
            "[muted]           🤖 Advanced AI Agent Development Kit 🤖[/muted]"
        )
        self.console.print()

        self.console.print(
            "[accent]┌─ Enhanced Agent CLI ─────────────────────────────────────┐[/accent]"
        )
        self.console.print(
            f"[accent]│[/accent] [agent]Agent:[/agent] [highlight]{agent_name}[/highlight]"
        )
        self.console.print(
            f"[accent]│[/accent] [muted]Theme:[/muted] {theme_indicator} {self.theme.value.title()}"
        )
        self.console.print(
            f"[accent]│[/accent] [muted]Session started:[/muted] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.console.print(
            "[accent]└──────────────────────────────────────────────────────────┘[/accent]"
        )

    def print_help(self) -> None:
        """Print themed help message."""
        self.console.print(
            "\n[accent]┌─ Available Commands ─────────────────────────────────────┐[/accent]"
        )
        self.console.print("[accent]│[/accent] [highlight]Navigation:[/highlight]")
        self.console.print(
            "[accent]│[/accent]   [user]exit, quit, bye[/user] - Exit the CLI"
        )
        self.console.print("[accent]│[/accent]   [user]clear[/user] - Clear the screen")
        self.console.print(
            "[accent]│[/accent]   [user]help[/user] - Show this help message"
        )
        self.console.print("[accent]│[/accent]")
        self.console.print("[accent]│[/accent] [highlight]Theming:[/highlight]")
        self.console.print(
            "[accent]│[/accent]   [user]theme toggle[/user] - Toggle between light/dark"
        )
        self.console.print(
            "[accent]│[/accent]   [user]theme dark[/user] - Switch to dark theme"
        )
        self.console.print(
            "[accent]│[/accent]   [user]theme light[/user] - Switch to light theme"
        )
        self.console.print("[accent]│[/accent]")
        self.console.print(
            "[accent]│[/accent] [highlight]Keyboard Shortcuts:[/highlight]"
        )
        self.console.print("[accent]│[/accent]   [user]Enter[/user] - Submit input")
        self.console.print(
            "[accent]│[/accent]   [user]Alt+Enter[/user] - Insert new line for multi-line input"
        )
        self.console.print("[accent]│[/accent]   [user]Ctrl+D[/user] - Exit gracefully")
        self.console.print("[accent]│[/accent]   [user]Ctrl+L[/user] - Clear screen")
        self.console.print("[accent]│[/accent]   [user]Ctrl+T[/user] - Toggle theme")
        self.console.print(
            "[accent]│[/accent]   [user]Tab[/user] - Show command suggestions"
        )
        self.console.print(
            "[accent]└──────────────────────────────────────────────────────────┘[/accent]"
        )
        self.console.print()

    # def add_agent_output(self, text: str, author: str = "Agent"):
    #     """Add agent output with markdown rendering and proper wrapping."""
    #     # Use format_message with markdown support enabled
    #     formatted_message = self.rich_renderer.format_message(text, author, markdown=True)
    #     self.console.print(formatted_message, soft_wrap=True, overflow="fold")

    # def add_agent_thought(self, text: str):
    #     """Add agent thought summaries to the thought display."""
    #     panel = self.rich_renderer.format_agent_thought(text)
    #     self.console.print(panel, soft_wrap=True, overflow="fold")

    def display_agent_response(self, parent_console: Console, response_summary: str, author: str = "Agent"):
        """Displays agent response summary in a Rich panel."""
        self.rich_renderer.display_agent_response(parent_console, response_summary, author)

    def display_agent_thought(self, parent_console: Console, thought_summary: str):
        """Displays agent thought summary in a Rich panel."""
        self.rich_renderer.display_agent_thought(parent_console, thought_summary)

    # END: Used from cli.py
