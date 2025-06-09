# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme


class UITheme(Enum):
    """Available UI themes."""
    DARK = "dark"
    LIGHT = "light"


class ThemeConfig:
    """Theme configuration for the CLI interface."""
    
    DARK_THEME = {
        # Prompt styles
        'prompt': '#87ceeb bold',  # sky blue
        'user-input': '#ffffff',  # white
        'agent-output': '#008000',  # green
        
        # Completion menu
        'completion-menu': 'bg:#2d2d2d #ffffff',
        'completion-menu.completion': 'bg:#2d2d2d #ffffff',
        'completion-menu.completion.current': 'bg:#4a4a4a #ffffff bold',
        
        # Auto-suggestion
        'auto-suggestion': '#666666 italic',
        
        # Bottom toolbar (tmux-style)
        # 'bottom-toolbar': 'bg:#1e1e1e #cccccc',
        'bottom-toolbar': 'bg:#cccccc #1e1e1e',
        'bottom-toolbar.accent': 'bg:#87ceeb #000000 bold',
        'bottom-toolbar.info': 'bg:#404040 #ffffff',
        'bottom-toolbar.success': 'bg:#32cd32 #000000 bold',
        'bottom-toolbar.warning': 'bg:#ffa500 #000000 bold',
        'bottom-toolbar.error': 'bg:#ff6b6b #ffffff bold',
        
        # Status indicators
        'status.active': '#32cd32 bold',  # lime green
        'status.inactive': '#666666',  # gray
        'status.time': '#87ceeb',  # sky blue
        'status.session': '#dda0dd',  # plum
        'status.agent': '#ffa500',  # orange
    }
    
    LIGHT_THEME = {
        # Prompt styles
        'prompt': '#0066cc bold',  # blue
        'user-input': '#000000',  # black
        'agent-output': '#008000',  # green
        
        # Completion menu
        'completion-menu': 'bg:#f0f0f0 #000000',
        'completion-menu.completion': 'bg:#f0f0f0 #000000',
        'completion-menu.completion.current': 'bg:#d0d0d0 #000000 bold',
        
        # Auto-suggestion
        'auto-suggestion': '#999999 italic',
        
        # Bottom toolbar (tmux-style)
        'bottom-toolbar': 'bg:#e6e6e6 #0066cc',
        'bottom-toolbar.accent': 'bg:#0066cc #ffffff bold',
        'bottom-toolbar.info': 'bg:#d0d0d0 #000000',
        'bottom-toolbar.success': 'bg:#28a745 #ffffff bold',
        'bottom-toolbar.warning': 'bg:#ffc107 #000000 bold',
        'bottom-toolbar.error': 'bg:#dc3545 #ffffff bold',
        
        # Status indicators
        'status.active': '#28a745 bold',  # green
        'status.inactive': '#999999',  # gray
        'status.time': '#0066cc',  # blue
        'status.session': '#6f42c1',  # purple
        'status.agent': '#fd7e14',  # orange
    }

    @classmethod
    def get_theme_config(cls, theme: UITheme) -> dict[str, str]:
        """Get theme configuration for the specified theme."""
        if theme == UITheme.DARK:
            return cls.DARK_THEME
        else:
            return cls.LIGHT_THEME

    @classmethod
    def get_rich_theme(cls, theme: UITheme) -> Theme:
        """Get Rich theme configuration."""
        if theme == UITheme.DARK:
            return Theme({
                "user": "bold cyan",
                "agent": "bold green",
                "system": "bold yellow",
                "error": "bold red",
                "success": "bold green",
                "info": "bold blue",
                "warning": "bold yellow",
                "muted": "dim white",
                "highlight": "bold magenta",
                "accent": "bold cyan",
            })
        else:
            return Theme({
                "user": "bold blue",
                "agent": "bold dark_green",
                "system": "bold orange3",
                "error": "bold red",
                "success": "bold green",
                "info": "bold blue",
                "warning": "bold yellow",
                "muted": "dim black",
                "highlight": "bold purple",
                "accent": "bold blue",
            })


class StatusBar:
    """Tmux-style status bar for the CLI."""
    
    def __init__(self, theme: UITheme = UITheme.DARK):
        self.theme = theme
        self.session_start_time = datetime.now()
        
    def get_status_segments(self, agent_name: str, session_id: str) -> list[tuple[str, str]]:
        """Get status bar segments as (content, style) tuples."""
        now = datetime.now()
        uptime = now - self.session_start_time
        uptime_str = f"{uptime.seconds // 3600:02d}:{(uptime.seconds % 3600) // 60:02d}:{uptime.seconds % 60:02d}"
        
        segments = [
            (f" 🤖 {agent_name} ", "bottom-toolbar.accent"),
            (f" Session: {session_id[:8]}... ", "bottom-toolbar.info"),
            (f" Uptime: {uptime_str} ", "bottom-toolbar.info"),
            (f" {now.strftime('%H:%M:%S')} ", "bottom-toolbar.accent"),
        ]
        
        return segments
    
    def format_toolbar(self, agent_name: str, session_id: str) -> str:
        """Format the bottom toolbar with tmux-style segments."""
        segments = self.get_status_segments(agent_name, session_id)
        
        # Build simple text with separators
        toolbar_parts = []
        for i, (content, style) in enumerate(segments):
            if i > 0:
                toolbar_parts.append(" | ")  # Simple separator
            toolbar_parts.append(content)
        
        # Add keyboard shortcuts on the right
        shortcuts = [
            ("Alt+Enter", "submit"),
            ("Ctrl+D", "exit"), 
            ("Ctrl+L", "clear"),
            ("Tab", "complete"),
        ]
        
        shortcuts_text = " | ".join([f"{key}:{action}" for key, action in shortcuts])
        toolbar_parts.append(f" | 💡 {shortcuts_text}")
        
        return ''.join(toolbar_parts)


class EnhancedCLI:
    """Enhanced CLI with tmux-style interface and theming."""
    
    def __init__(self, theme: Optional[UITheme] = None):
        # Determine theme from environment or default
        self.theme = theme or self._detect_theme()
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        self.status_bar = StatusBar(self.theme)
        self.console = Console(theme=self.rich_theme)
        
    def _detect_theme(self) -> UITheme:
        """Auto-detect theme from environment variables."""
        # Check various environment variables for theme preference
        theme_env = os.getenv('ADK_CLI_THEME', '').lower()
        if theme_env in ['light', 'dark']:
            return UITheme(theme_env)
            
        # Check terminal background detection
        term_program = os.getenv('TERM_PROGRAM', '').lower()
        if 'iterm' in term_program or 'terminal' in term_program:
            # Could add more sophisticated detection here
            pass
            
        # Default to dark theme
        return UITheme.DARK
    
    def create_enhanced_prompt_session(self, agent_name: str = "Agent", session_id: str = "unknown") -> PromptSession:
        """Create an enhanced PromptSession with tmux-style theming."""

        # # Create custom key bindings
        # bindings = KeyBindings()

        # # Alt+Enter for multi-line input submission
        # @bindings.add('escape', 'enter')
        # def _(event):
        #     """Submit multi-line input with Alt+Enter."""
        #     event.app.exit(result=event.app.current_buffer.text)

        # # Ctrl+D for graceful exit
        # @bindings.add('c-d')
        # def _(event):
        #     """Exit gracefully with Ctrl+D."""
        #     if not event.app.current_buffer.text:
        #         event.app.exit(result='exit')
        #     else:
        #         event.app.current_buffer.delete_before_cursor()

        # # Ctrl+C for cancel current input
        # @bindings.add('c-c')
        # def _(event):
        #     """Cancel current input with Ctrl+C."""
        #     event.app.current_buffer.reset()

        # # Ctrl+L for clear screen
        # @bindings.add('c-l')
        # def _(event):
        #     """Clear screen with Ctrl+L."""
        #     event.app.renderer.clear()

        # # Ctrl+T for theme toggle
        # @bindings.add('c-t')
        # def _(event):
        #     """Toggle theme with Ctrl+T."""
        #     self.toggle_theme()
        #     event.app.invalidate()  # Refresh the display

        # Create style from theme config
        style = Style.from_dict(self.theme_config)
        
        # Common agentic workflow commands for completion
        common_commands = [
            # Code analysis and improvement
            'analyze this code', 'review the codebase', 'find security vulnerabilities', 
            'optimize performance of', 'refactor this function', 'add error handling to',
            'add type hints to', 'add documentation for', 'write unit tests for',
            'write integration tests for', 'fix the bug in', 'debug this issue',
            
            # Infrastructure and DevOps
            'create a dockerfile', 'create docker-compose.yml', 'write kubernetes manifests',
            'create helm chart for', 'write terraform code for', 'setup CI/CD pipeline',
            'configure github actions', 'setup monitoring for', 'add logging to',
            'create health checks', 'setup load balancer', 'configure autoscaling',
            
            # Deployment and operations
            'deploy to production', 'deploy to staging', 'rollback deployment',
            'check service status', 'troubleshoot deployment', 'scale the service',
            'update dependencies', 'backup the database', 'restore from backup',
            
            # Development workflow
            'create new feature branch', 'merge pull request', 'tag new release',
            'update changelog', 'bump version number', 'run security scan',
            'run performance tests', 'generate documentation',
            
            # CLI commands
            'exit', 'quit', 'bye', 'help', 'clear', 'theme toggle', 'theme dark', 'theme light',
        ]
        
        completer = WordCompleter(common_commands, ignore_case=True)
        history = InMemoryHistory()
        
        return PromptSession(
            # key_bindings=bindings,
            style=style,
            completer=completer,
            auto_suggest=AutoSuggestFromHistory(),
            history=history,
            multiline=True,
            mouse_support=True,
            wrap_lines=True,
            enable_history_search=True,
            prompt_continuation=lambda width, line_number, is_soft_wrap: "     > " if not is_soft_wrap else "",
            bottom_toolbar=lambda: self._safe_format_toolbar(agent_name, session_id),
            reserve_space_for_menu=4,
        )
    
    def _safe_format_toolbar(self, agent_name: str, session_id: str) -> str:
        """Safely format the toolbar with error handling."""
        try:
            return self.status_bar.format_toolbar(agent_name, session_id)
        except Exception as e:
            # Fallback to simple toolbar if formatting fails
            return f" 🤖 {agent_name} | Session: {session_id[:8]}... | 💡 Alt+Enter:submit | Ctrl+D:exit"
    
    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.theme = UITheme.LIGHT if self.theme == UITheme.DARK else UITheme.DARK
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        self.status_bar.theme = self.theme
        self.console = Console(theme=self.rich_theme)
        
        theme_name = "🌒 Dark" if self.theme == UITheme.DARK else "🌞 Light"
        self.console.print(f"[info]Switched to {theme_name} theme[/info]")
    
    def set_theme(self, theme: UITheme) -> None:
        """Set a specific theme."""
        if self.theme != theme:
            self.theme = theme
            self.theme_config = ThemeConfig.get_theme_config(self.theme)
            self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
            self.status_bar.theme = self.theme
            self.console = Console(theme=self.rich_theme)
            
            theme_name = "🌙 Dark" if self.theme == UITheme.DARK else "☀️ Light"
            self.console.print(f"[info]Set theme to {theme_name}[/info]")
    
    def print_welcome_message(self, agent_name: str) -> None:
        """Print a themed welcome message with tmux-style formatting."""
        theme_indicator = "🌙" if self.theme == UITheme.DARK else "☀️"
        
        self.console.print("\n[accent]┌─ Enhanced Agent CLI ─────────────────────────────────────┐[/accent]")
        self.console.print(f"[accent]│[/accent] [agent]🤖 Agent:[/agent] [highlight]{agent_name}[/highlight]")
        self.console.print(f"[accent]│[/accent] [muted]Theme:[/muted] {theme_indicator} {self.theme.value.title()}")
        self.console.print(f"[accent]│[/accent] [muted]Session started:[/muted] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.console.print("[accent]└──────────────────────────────────────────────────────────┘[/accent]")
        
        self.console.print("\n[muted]Enhanced Features:[/muted]")
        self.console.print("[muted]  • Multi-line input support (Alt+Enter to submit)[/muted]")
        self.console.print("[muted]  • Mouse support for selection and cursor positioning[/muted]") 
        self.console.print("[muted]  • Command history with auto-suggestions[/muted]")
        self.console.print("[muted]  • Tab completion for common DevOps commands[/muted]")
        self.console.print("[muted]  • Tmux-style status bar with session info[/muted]")
        self.console.print("[muted]  • Theme switching (Ctrl+T or 'theme toggle')[/muted]")
        self.console.print()
    
    def format_agent_response(self, text: str, author: str) -> Panel:
        """Format agent response with themed panel."""
        markdown_text = Markdown(text)
        
        if self.theme == UITheme.DARK:
            border_style = "green"
            title_style = "bold green"
        else:
            border_style = "dark_green" 
            title_style = "bold dark_green"
            
        return Panel(
            markdown_text,
            title=f"🤖 [{title_style}]{author}[/{title_style}]",
            border_style=border_style,
            expand=True
        )
    
    def print_help(self) -> None:
        """Print themed help message."""
        self.console.print("\n[accent]┌─ Available Commands ─────────────────────────────────────┐[/accent]")
        self.console.print("[accent]│[/accent] [highlight]Navigation:[/highlight]")
        self.console.print("[accent]│[/accent]   [user]exit, quit, bye[/user] - Exit the CLI")
        self.console.print("[accent]│[/accent]   [user]clear[/user] - Clear the screen")
        self.console.print("[accent]│[/accent]   [user]help[/user] - Show this help message")
        self.console.print("[accent]│[/accent]")
        self.console.print("[accent]│[/accent] [highlight]Theming:[/highlight]")
        self.console.print("[accent]│[/accent]   [user]theme toggle[/user] - Toggle between light/dark")
        self.console.print("[accent]│[/accent]   [user]theme dark[/user] - Switch to dark theme")
        self.console.print("[accent]│[/accent]   [user]theme light[/user] - Switch to light theme")
        self.console.print("[accent]│[/accent]")
        self.console.print("[accent]│[/accent] [highlight]Keyboard Shortcuts:[/highlight]")
        self.console.print("[accent]│[/accent]   [user]Alt+Enter[/user] - Submit multi-line input")
        self.console.print("[accent]│[/accent]   [user]Ctrl+D[/user] - Exit gracefully")
        self.console.print("[accent]│[/accent]   [user]Ctrl+L[/user] - Clear screen")
        self.console.print("[accent]│[/accent]   [user]Ctrl+T[/user] - Toggle theme")
        self.console.print("[accent]│[/accent]   [user]Tab[/user] - Show command suggestions")
        self.console.print("[accent]└──────────────────────────────────────────────────────────┘[/accent]")
        self.console.print()


def get_cli_instance(theme: Optional[str] = None) -> EnhancedCLI:
    """Factory function to create a CLI instance with the specified theme."""
    ui_theme: Optional[UITheme] = None
    if theme:
        try:
            ui_theme = UITheme(theme.lower())
        except ValueError:
            pass  # Use auto-detected theme
    
    return EnhancedCLI(ui_theme) 