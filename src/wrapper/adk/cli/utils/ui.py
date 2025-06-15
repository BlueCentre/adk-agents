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
import asyncio
import sys
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any, Awaitable
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from prompt_toolkit import PromptSession, Application
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.application import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.output import Output
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.shortcuts import confirm

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
        'completion-menu.category': 'bg:#1e1e1e #87ceeb bold',
        
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
        'completion-menu.category': 'bg:#e0e0e0 #0066cc bold',
        
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
            ("Enter", "submit"),
            ("Alt+Enter", "multi-line"),
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
        # Configure console to preserve scrollback behavior
        self.console = Console(
            theme=self.rich_theme,
            force_interactive=False,  # Disable animations that might interfere with scrollback
            legacy_windows=False,     # Use modern terminal features
            soft_wrap=True,           # Enable soft wrapping to prevent cropping
            no_color=False,           # Keep colors but ensure compatibility
            width=None,               # Auto-detect width to avoid fixed sizing issues
            height=None               # Auto-detect height to avoid fixed sizing issues
        )
        
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

        # https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/key_bindings.html

        # Create custom key bindings
        bindings = KeyBindings()

        # Alt+Enter for newline
        @bindings.add('escape', 'enter')
        def _(event):
            """Insert newline."""
            event.current_buffer.insert_text('\n')

        # Ctrl+T for theme toggle
        @bindings.add('c-t')
        def _(event):
            """Toggle theme with Ctrl+T."""
            self.toggle_theme()
            event.app.invalidate()  # Refresh the display

        # Create style from theme config
        style = Style.from_dict(self.theme_config)
        
        # Categorized agentic workflow commands for completion
        categorized_commands = {
            '🔍 Code Analysis': [
                'analyze this code', 'review the codebase', 'find security vulnerabilities', 
                'optimize performance of', 'refactor this function', 'add error handling to',
                'add type hints to', 'add documentation for', 'write unit tests for',
                'write integration tests for', 'fix the bug in', 'debug this issue',
            ],
            '🚀 Infrastructure & DevOps': [
                'create a dockerfile', 'create docker-compose.yml', 'write kubernetes manifests',
                'create helm chart for', 'write terraform code for', 'setup CI/CD pipeline',
                'configure github actions', 'setup monitoring for', 'add logging to',
                'create health checks', 'setup load balancer', 'configure autoscaling',
                'list the k8s clusters and indicate the current one',
                'list all the user applications in the qa- namespaces on the current k8s cluster',
            ],
            '📦 Deployment & Operations': [
                'deploy to production', 'deploy to staging', 'rollback deployment',
                'check service status', 'troubleshoot deployment', 'scale the service',
                'update dependencies', 'backup the database', 'restore from backup',
            ],
            '🔧 Development Workflow': [
                'create new feature branch', 'merge pull request', 'tag new release',
                'update changelog', 'bump version number', 'execute regression tests',
                'run security scan', 'run performance tests', 'generate documentation',
            ],
            '⚙️ CLI Commands': [
                'exit', 'quit', 'bye', 'help', 'clear', 'theme toggle', 'theme dark', 'theme light',
            ],
        }
        
        # Create a custom completer that shows categories
        from prompt_toolkit.completion import Completer, Completion
        
        class CategorizedCompleter(Completer):
            def __init__(self, categorized_commands):
                self.categorized_commands = categorized_commands
                # Flatten all commands for matching
                self.all_commands = []
                for category, commands in categorized_commands.items():
                    self.all_commands.extend(commands)
            
            def get_completions(self, document, complete_event):
                text = document.get_word_before_cursor(WORD=True)
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
                            '',
                            start_position=0,
                            display=f'{category}',
                            style='class:completion-menu.category'
                        )
                        
                        # Add the actual completions
                        for command in category_matches:
                            start_pos = -len(text) if text else 0
                            yield Completion(
                                command,
                                start_position=start_pos,
                                display=f'  {command}',
                                style='class:completion-menu.completion'
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
            prompt_continuation=lambda width, line_number, is_soft_wrap: "     > " if not is_soft_wrap else "",
            bottom_toolbar=lambda: self._safe_format_toolbar(agent_name, session_id),
            reserve_space_for_menu=4,
            # Preserve terminal scrollback behavior
            refresh_interval=0.1,  # Reduce refresh rate to minimize interference
            input_processors=[],   # Disable input processors that might interfere
        )
    
    def _safe_format_toolbar(self, agent_name: str, session_id: str) -> str:
        """Safely format the toolbar with error handling."""
        try:
            return self.status_bar.format_toolbar(agent_name, session_id)
        except Exception as e:
            # Fallback to simple toolbar if formatting fails
            return f" 🤖 {agent_name} | Session: {session_id[:8]}... | 💡 Alt+Enter:multi-line | 🚪 Ctrl+D:exit"
    
    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.theme = UITheme.LIGHT if self.theme == UITheme.DARK else UITheme.DARK
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        self.status_bar.theme = self.theme
        self.console = Console(
            theme=self.rich_theme,
            force_interactive=False,  # Disable animations that might interfere with scrollback
            legacy_windows=False,     # Use modern terminal features
            soft_wrap=True,           # Enable soft wrapping to prevent cropping
            no_color=False,           # Keep colors but ensure compatibility
            width=None,               # Auto-detect width to avoid fixed sizing issues
            height=None               # Auto-detect height to avoid fixed sizing issues
        )
        
        theme_name = "🌒 Dark" if self.theme == UITheme.DARK else "🌞 Light"
        self.console.print(f"[info]Switched to {theme_name} theme[/info]")
    
    def set_theme(self, theme: UITheme) -> None:
        """Set a specific theme."""
        if self.theme != theme:
            self.theme = theme
            self.theme_config = ThemeConfig.get_theme_config(self.theme)
            self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
            self.status_bar.theme = self.theme
            self.console = Console(
                theme=self.rich_theme,
                force_interactive=False,  # Disable animations that might interfere with scrollback
                legacy_windows=False,     # Use modern terminal features
                soft_wrap=True,           # Enable soft wrapping to prevent cropping
                no_color=False,           # Keep colors but ensure compatibility
                width=None,               # Auto-detect width to avoid fixed sizing issues
                height=None               # Auto-detect height to avoid fixed sizing issues
            )
            
            theme_name = "🌒 Dark" if self.theme == UITheme.DARK else "🌞 Light"
            self.console.print(f"[info]Set theme to {theme_name}[/info]")
    
    def print_welcome_message(self, agent_name: str) -> None:
        """Print a themed welcome message with tmux-style formatting."""
        theme_indicator = "🌒" if self.theme == UITheme.DARK else "🌞"
        
        # Welcome ASCII Art Logo
        self.console.print()
        self.console.print("[agent]                 ▄▀█ █   ▄▀█ █▀▀ █▀▀ █▄█ ▀█▀[/agent]")
        self.console.print("[agent]                 █▀█ █   █▀█ █▄█ █▄▄ █░█ ░█░[/agent]")
        self.console.print()
        self.console.print("[muted]           🤖 Advanced AI Agent Development Kit 🤖[/muted]")
        self.console.print()

        self.console.print("\n[accent]┌─ Enhanced Agent CLI ─────────────────────────────────────┐[/accent]")
        self.console.print(f"[accent]│[/accent] [agent]Agent:[/agent] [highlight]{agent_name}[/highlight]")
        self.console.print(f"[accent]│[/accent] [muted]Theme:[/muted] {theme_indicator} {self.theme.value.title()}")
        self.console.print(f"[accent]│[/accent] [muted]Session started:[/muted] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.console.print("[accent]└──────────────────────────────────────────────────────────┘[/accent]")
        
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
        self.console.print("[accent]│[/accent]   [user]Enter[/user] - Submit input")
        self.console.print("[accent]│[/accent]   [user]Alt+Enter[/user] - Insert new line for multi-line input")
        self.console.print("[accent]│[/accent]   [user]Ctrl+D[/user] - Exit gracefully")
        self.console.print("[accent]│[/accent]   [user]Ctrl+L[/user] - Clear screen")
        self.console.print("[accent]│[/accent]   [user]Ctrl+T[/user] - Toggle theme")
        self.console.print("[accent]│[/accent]   [user]Tab[/user] - Show command suggestions")
        self.console.print("[accent]└──────────────────────────────────────────────────────────┘[/accent]")
        self.console.print()


class InterruptibleCLI:
    """CLI with persistent input pane and agent interruption capabilities."""
    
    def __init__(self, theme: Optional[UITheme] = None):
        self.theme = theme or UITheme.DARK
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        self.status_bar = StatusBar(self.theme)
        self.console = Console(theme=self.rich_theme, force_interactive=False)
        
        # State management
        self.agent_running = False
        self.current_agent_task: Optional[asyncio.Task] = None
        self.agent_output_buffer = []
        self.input_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self.interrupt_callback: Optional[Callable[[], Awaitable[None]]] = None
        
        # Markdown rendering toggle
        self.markdown_enabled = True  # Enable markdown by default
        
        # Content deduplication tracking
        self.last_token_usage = ""
        self.last_agent_thought = ""
        self.seen_content = set()
        self.current_response_id = 0
        
        # UI Components
        self.input_buffer = Buffer(multiline=True)
        self.output_buffer = Buffer()  # Don't make read-only since we need to add agent output
        self.status_buffer = Buffer()  # Don't make read-only since we need to update it
        
        self._setup_layout()
        self._setup_key_bindings()
        
    def _setup_layout(self):
        """Setup the split-pane layout."""
        
        # Input area (bottom pane)
        input_window = Window(
            content=BufferControl(
                buffer=self.input_buffer,
                input_processors=[]
            ),
            height=5,  # Fixed height for input pane
            wrap_lines=True,
        )
        
        # Output area (top pane)
        output_window = Window(
            content=BufferControl(
                buffer=self.output_buffer
            ),
            wrap_lines=True,
        )
        
        # Status area (single line at bottom)
        status_window = Window(
            content=BufferControl(buffer=self.status_buffer),
            height=1,
            style="class:bottom-toolbar"
        )
        
        # Frame the input area
        input_frame = Frame(
            body=input_window,
            title=self._get_input_title,
            style="class:frame.input"
        )
        
        # Frame the output area  
        output_frame = Frame(
            body=output_window,
            title=self._get_output_title,
            style="class:frame.output"
        )
        
        # Main layout with horizontal split
        self.layout = Layout(
            HSplit([
                output_frame,  # Top: Agent output (flexible height)
                input_frame,   # Middle: User input (fixed height)
                status_window, # Bottom: Status bar (fixed height)
            ])
        )
        
    def _get_input_title(self) -> str:
        """Dynamic title for input pane."""
        if self.agent_running:
            return "💭 User Input (Ctrl+C to interrupt agent)"
        return "😎 User Input (Enter to send, Alt+Enter for newline)"
        
    def _get_output_title(self) -> str:
        """Dynamic title for output pane."""
        if self.agent_running:
            return "🤖 Agent Output (thinking...)"
        return "🤖 Agent Output"
        
    def _setup_key_bindings(self):
        """Setup custom key bindings."""
        self.bindings = KeyBindings()
        
        # Enter to submit - use a more specific approach
        @self.bindings.add('enter', eager=True)
        def _(event):
            """Submit user input when Enter is pressed."""
            content = self.input_buffer.text.strip()
            if content:
                self._add_to_output(f"🔄 Processing: {content}", style="info")
                asyncio.create_task(self._handle_user_input(content))
            else:
                self._add_to_output("💡 Type a message and press Enter to send it to the agent", style="info")
        
        # Test key binding - F1 should definitely work
        @self.bindings.add('f1')
        def _(event):
            """Test key binding."""
            print("DEBUG: F1 key pressed! Key bindings are working!")
            self._add_to_output("🔧 F1 pressed - key bindings are working!", style="info")
        
        # Alternative submit with Ctrl+J (which is a valid key binding)
        @self.bindings.add('c-j')
        def _(event):
            """Submit input with Ctrl+J."""
            content = self.input_buffer.text.strip()
            if content:
                self._add_to_output(f"🔄 Processing (Ctrl+J): {content}", style="info")
                asyncio.create_task(self._handle_user_input(content))
            else:
                self._add_to_output("💡 Type a message and press Ctrl+J to send it to the agent", style="info")
        
        # Make sure normal typing works by allowing all printable characters
        # This ensures users can actually type in the input buffer
        @self.bindings.add('c-i')  # Tab key - focus management
        def _(event):
            """Handle tab - keep focus on input."""
            # Keep focus on input buffer
            event.app.layout.focus(self.input_buffer)
            
        # Alt+Enter for multi-line input - use a different key to avoid conflicts
        @self.bindings.add('escape', 'n')
        def _(event):
            """Insert newline with Alt+N."""
            event.current_buffer.insert_text('\n')
            
        # Ctrl+C to interrupt agent
        @self.bindings.add('c-c')
        def _(event):
            """Interrupt running agent."""
            if self.agent_running:
                asyncio.create_task(self._interrupt_agent())
            else:
                # Standard Ctrl+C behavior when agent not running
                event.app.exit(exception=KeyboardInterrupt)
                
        # Ctrl+D to exit
        @self.bindings.add('c-d')
        def _(event):
            """Exit application."""
            event.app.exit()
            
        # Ctrl+L to clear output
        @self.bindings.add('c-l')
        def _(event):
            """Clear output buffer."""
            self.output_buffer.text = ""
            
        # Ctrl+T for theme toggle
        @self.bindings.add('c-t')
        def _(event):
            """Toggle theme."""
            self.toggle_theme()
            self._update_status()
            
        # Ctrl+M to toggle markdown rendering
        @self.bindings.add('c-m')
        def _(event):
            """Toggle markdown rendering."""
            self.markdown_enabled = not self.markdown_enabled
            status = "enabled" if self.markdown_enabled else "disabled"
            self._add_to_output(f"📝 Markdown rendering {status}", style="info")
            self._update_status()
        
    async def _handle_user_input(self, content: str):
        """Handle user input submission."""
        # Clear input buffer
        self.input_buffer.text = ""
        
        # Reset deduplication state for new query
        self._reset_deduplication_state()
        
        # Add user input to output
        self._add_to_output(f"😎 User: {content}", style="user")
        
        # Handle special commands
        if content.lower() in ['exit', 'quit', 'bye']:
            get_app().exit()
            return
        elif content.lower() == 'clear':
            self.output_buffer.text = ""
            return
        elif content.lower() == 'help':
            self._show_help()
            return
        elif content.lower().startswith('theme'):
            self._handle_theme_command(content)
            return
            
        # Call the registered input callback
        if self.input_callback:
            self.agent_running = True
            self._update_status()
            try:
                await self.input_callback(content)
            finally:
                self.agent_running = False
                self._update_status()
        else:
            # No callback registered - this is a problem
            self._add_to_output("❌ No input callback registered! The agent connection may not be working.", style="error")
            self._add_to_output("🔧 Try restarting the CLI or check the agent configuration.", style="info")
                
    async def _interrupt_agent(self):
        """Interrupt the currently running agent."""
        if self.current_agent_task and not self.current_agent_task.done():
            self.current_agent_task.cancel()
            self._add_to_output("⚠️ Agent interrupted by user", style="warning")
            
        if self.interrupt_callback:
            await self.interrupt_callback()
            
        self.agent_running = False
        self._update_status()
        
    def _add_to_output(self, text, style: str = ""):
        """Add text to the output buffer with markdown rendering, deduplication and Rich formatting cleanup."""
        # Convert to string if it's not already
        text = str(text)
        
        # Apply Rich markdown rendering FIRST if enabled
        if self.markdown_enabled:
            try:
                from rich.markdown import Markdown
                from rich.console import Console
                from io import StringIO
                
                # Create a markdown object
                markdown_obj = Markdown(text)
                
                # Render it with Rich to get properly formatted output
                string_io = StringIO()
                temp_console = Console(
                    file=string_io, 
                    force_terminal=True,  # Enable colors and formatting
                    width=100,
                    legacy_windows=False,
                    color_system="auto"
                )
                temp_console.print(markdown_obj)
                rendered_text = string_io.getvalue()
                
                # Use the Rich-rendered markdown
                text = rendered_text
                
            except Exception as e:
                # Fallback to plain text if Rich markdown fails
                pass
        
        # Apply minimal cleanup (but preserve Rich formatting if markdown was applied)
        if self.markdown_enabled:
            # For markdown, do minimal cleanup to preserve Rich formatting
            clean_text = text
        else:
            # For non-markdown, apply full Rich stripping
            clean_text = self._strip_all_rich_formatting(text)
        
        # Skip empty or whitespace-only content
        if not clean_text or not clean_text.strip():
            return
        
        # Apply deduplication logic
        processed_text = self._deduplicate_content(clean_text)
        if not processed_text:
            return  # Content was filtered out as duplicate
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{timestamp}] {processed_text}\n"
        
        current_text = self.output_buffer.text
        self.output_buffer.text = current_text + formatted_text
        
        # Auto-scroll to bottom
        self.output_buffer.cursor_position = len(self.output_buffer.text)
    
    def _deduplicate_content(self, text: str) -> str:
        """Deduplicate and consolidate repetitive content."""
        import re
        
        # Normalize the text for comparison
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        
        # Check for exact duplicates
        if normalized in self.seen_content:
            return ""  # Skip exact duplicates
        
        # Handle Token Usage consolidation - catch various formats
        token_patterns = [
            r'token usage[:\s]*(.+)',
            r'prompt[:\s]*\d+.*?total[:\s]*\d+',
            r'\d+.*?output[:\s]*\d+.*?total[:\s]*\d+'
        ]
        
        for pattern in token_patterns:
            token_match = re.search(pattern, text, re.IGNORECASE)
            if token_match:
                token_info = token_match.group(0).strip()
                # Normalize token info for comparison
                normalized_token = re.sub(r'\s+', ' ', token_info.lower())
                if normalized_token == self.last_token_usage:
                    return ""  # Skip duplicate token usage
                self.last_token_usage = normalized_token
                self.seen_content.add(normalized)
                return f"📊 {token_info}"
        
        # Handle Agent Thought consolidation
        thought_match = re.search(r'agent thought[:\s]*(.+)', text, re.IGNORECASE)
        if thought_match:
            thought_content = thought_match.group(1).strip()
            # Only show substantial thoughts, skip very similar ones
            if len(thought_content) > 20 and thought_content != self.last_agent_thought:
                self.last_agent_thought = thought_content
                self.seen_content.add(normalized)
                return f"🧠 Agent Thought: {thought_content}"
            return ""
        
        # Handle repetitive "thinking" or processing messages
        if any(phrase in normalized for phrase in [
            'thinking through', 'current time acquisition', 'time is at hand',
            'responding to a simple', 'time acquisition process'
        ]):
            # Only show the first occurrence of thinking messages
            thinking_key = 'thinking_message'
            if thinking_key in self.seen_content:
                return ""
            self.seen_content.add(thinking_key)
            return "🤔 Agent is processing your request..."
        
        # Filter out system/server status messages that shouldn't be shown
        system_noise_patterns = [
            r'secure mcp filesystem server',
            r'allowed directories',
            r'knowledge graph mcp server',
            r'running on stdio',
            r'userinput.*enter.*send.*alt.*enter',
            r'theme.*dark.*time.*enter.*send'
        ]
        
        for pattern in system_noise_patterns:
            if re.search(pattern, normalized):
                return ""  # Filter out system noise
        
        # For other content, check for substantial similarity
        words = set(normalized.split())
        for seen in self.seen_content:
            seen_words = set(seen.split())
            # If more than 70% of words overlap, consider it similar
            if len(words & seen_words) / max(len(words), len(seen_words)) > 0.7:
                return ""
        
        # Add to seen content and return
        self.seen_content.add(normalized)
        return text
    
    def _reset_deduplication_state(self):
        """Reset deduplication tracking for a new query."""
        self.seen_content.clear()
        self.last_token_usage = ""
        self.last_agent_thought = ""
        self.current_response_id += 1
    
    def _strip_all_rich_formatting(self, text: str) -> str:
        """Aggressively strip all Rich formatting, panels, boxes, and markup."""
        import re
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from io import StringIO
        
        # Handle Rich objects directly if they're passed in
        if hasattr(text, '__rich__') or hasattr(text, '__rich_console__'):
            try:
                # It's a Rich object, extract plain text
                string_io = StringIO()
                temp_console = Console(file=string_io, force_terminal=False, width=120)
                temp_console.print(text, markup=False, highlight=False)
                text = string_io.getvalue()
            except:
                text = str(text)
        
        # Convert to string if it's not already
        text = str(text)
        
        try:
            # Render with Rich to get clean text output
            string_io = StringIO()
            temp_console = Console(
                file=string_io, 
                force_terminal=False, 
                width=120,
                legacy_windows=False,
                force_jupyter=False,
                _environ={},
                no_color=True,
                color_system=None
            )
            
            # Print without any Rich features
            temp_console.print(text, markup=False, highlight=False, crop=False, overflow="ignore", soft_wrap=True)
            rendered_text = string_io.getvalue()
            
        except Exception:
            rendered_text = text
        
        # Apply aggressive text cleaning
        clean_text = self._aggressive_text_clean(rendered_text)
        
        return clean_text
    
    def _aggressive_text_clean(self, text: str) -> str:
        """Apply aggressive text cleaning to remove all Rich artifacts."""
        import re
        
        # Remove ANSI escape sequences first
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)
        
        # Remove all Unicode box drawing and special characters
        box_chars = r'[┌┐└┘├┤┬┴┼─│╭╮╰╯╠╣╦╩╬═║╔╗╚╝╠╣╦╩╬▀▄█▌▐░▒▓■□▪▫▬▲►▼◄◊○●◦☼♠♣♥♦♪♫☺☻♂♀]'
        text = re.sub(box_chars, '', text)
        
        # Remove Rich panel patterns completely
        panel_removal_patterns = [
            r'╭[─\s]*.*?[─\s]*╮',  # Panel tops
            r'╰[─\s]*.*?[─\s]*╯',  # Panel bottoms
            r'│[^│]*│',             # Panel content lines
            r'┌[─\s]*.*?[─\s]*┐',  # Box tops
            r'└[─\s]*.*?[─\s]*┘',  # Box bottoms
        ]
        
        for pattern in panel_removal_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.MULTILINE)
        
        # Extract meaningful content from known patterns
        meaningful_content = []
        
        # Extract token usage info
        token_matches = re.findall(r'Token Usage[:\s]*([^│\n\r]*(?:Prompt|Thinking|Output|Total)[^│\n\r]*)', text, re.IGNORECASE)
        if token_matches:
            meaningful_content.append(f"Token Usage: {' '.join(token_matches).strip()}")
        
        # Extract agent thoughts/responses
        thought_matches = re.findall(r'(?:Agent Thought|Thinking|Response)[:\s]*([^│\n\r]{20,})', text, re.IGNORECASE | re.DOTALL)
        if thought_matches:
            for thought in thought_matches:
                clean_thought = re.sub(r'[│─┌┐└┘╭╮╰╯]', '', thought).strip()
                if len(clean_thought) > 10:  # Only include substantial content
                    meaningful_content.append(f"Agent Thought: {clean_thought}")
        
        # If we extracted meaningful content, use that
        if meaningful_content:
            return '\n'.join(meaningful_content)
        
        # Otherwise, clean up the original text
        # Remove empty lines and excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        clean_lines = []
        
        for line in lines:
            # Skip lines that are just formatting artifacts
            if re.match(r'^[│─┌┐└┘╭╮╰╯\s]*$', line):
                continue
            # Skip very short lines that are likely artifacts
            if len(line.strip()) < 3:
                continue
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def _remove_rich_patterns(self, text: str) -> str:
        """Remove Rich-specific patterns like panels, boxes, etc."""
        import re
        
        # Remove box drawing characters and panel borders (comprehensive set)
        box_chars = r'[┌┐└┘├┤┬┴┼─│╭╮╰╯╠╣╦╩╬═║╔╗╚╝╠╣╦╩╬▀▄█▌▐░▒▓■□▪▫▬▲►▼◄◊○●◦☼♠♣♥♦♪♫☺☻♂♀♪♫☺☻]'
        text = re.sub(box_chars, '', text)
        
        # Remove panel titles and content patterns
        panel_patterns = [
            r'╭[─]*.*?─*╮',  # Panel tops
            r'╰[─]*.*?─*╯',  # Panel bottoms  
            r'│.*?│',        # Panel sides
            r'┌[─]*.*?─*┐',  # Box tops
            r'└[─]*.*?─*┘',  # Box bottoms
        ]
        
        for pattern in panel_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL)
        
        # Remove Rich markup patterns
        markup_patterns = [
            r'\[/?bold\]',
            r'\[/?italic\]', 
            r'\[/?underline\]',
            r'\[/?dim\]',
            r'\[/?bright\]',
            r'\[/?reverse\]',
            r'\[/?strike\]',
            r'\[/?blink\]',
            r'\[/?conceal\]',
            r'\[/?[a-z_]+\]',  # Any other markup tags
            r'\[/?#[0-9a-fA-F]{6}\]',  # Hex colors
            r'\[/?rgb\(\d+,\d+,\d+\)\]',  # RGB colors
            r'\[/?on [a-z_]+\]',  # Background colors
        ]
        
        for pattern in markup_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Extract just the meaningful content from common Rich patterns
        # Look for "Token Usage:" patterns and extract just the content
        token_usage_match = re.search(r'Token Usage[:\s]*([^│\n]*)', text, re.IGNORECASE)
        if token_usage_match:
            token_info = token_usage_match.group(1).strip()
            # Replace the entire token usage section with just the clean info
            text = re.sub(r'.*Token Usage.*?(?=\n\n|\Z)', f'Token Usage: {token_info}', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Look for agent thought patterns and clean them
        thought_match = re.search(r'\*\*.*?(?:Thinking|Thought|Response).*?\*\*(.*?)(?=\n\*\*|\Z)', text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought_content = thought_match.group(1).strip()
            # Replace with clean thought content
            text = re.sub(r'\*\*.*?(?:Thinking|Thought|Response).*?\*\*.*?(?=\n\n|\Z)', f'Agent Thought: {thought_content}', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove excessive spaces and empty lines
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n\s*\n+', '\n', text)  # Multiple newlines to single
        text = re.sub(r'^\s*\n', '', text)  # Remove leading newlines
        
        return text.strip()
        
    def _update_status(self):
        """Update the status bar and clean input buffer if needed."""
        theme_indicator = "🌒" if self.theme == UITheme.DARK else "🌞"
        agent_status = "🟡 Thinking..." if self.agent_running else "🟢 Ready"
        markdown_status = "📝" if self.markdown_enabled else "📄"
        
        status_text = (
            f" {agent_status} | Theme: {theme_indicator} {self.theme.value.title()} | "
            f"Markdown: {markdown_status} | "
            f"Time: {datetime.now().strftime('%H:%M:%S')} | "
            f"💡 Enter:send Alt+Enter:newline Ctrl+C:interrupt Ctrl+M:markdown Ctrl+D:exit "
        )
        
        # Only update if the status has actually changed
        if self.status_buffer.text != status_text:
            self.status_buffer.text = status_text
            
        # Clean input buffer if it contains MCP noise
        self._clean_input_buffer()
    
    def _clean_input_buffer(self):
        """Clean the input buffer if it contains MCP server noise."""
        if hasattr(self.input_buffer, 'text') and self.input_buffer.text:
            # Check if input buffer contains MCP noise
            if self._is_system_noise(self.input_buffer.text):
                # Clear the contaminated input
                self.input_buffer.text = ""
                self.input_buffer.cursor_position = 0
    
    def _show_help(self):
        """Show help information."""
        help_text = """🤖 Interruptible CLI Help

Keyboard Shortcuts:
• Enter - Send message (when agent is not running)
• Alt+Enter - Insert newline in input
• Ctrl+C - Interrupt running agent
• Ctrl+D - Exit application
• Ctrl+L - Clear output pane
• Ctrl+T - Toggle theme
• Ctrl+M - Toggle markdown rendering

Features:
• Persistent input pane - type while agent is responding
• Agent interruption - Ctrl+C to stop long-running operations
• Split-pane interface - output above, input below
• Real-time status updates
• Markdown rendering for formatted agent responses
        """
        self._add_to_output(help_text.strip(), style="info")
        
    def _handle_theme_command(self, command: str):
        """Handle theme change commands."""
        parts = command.lower().split()
        if len(parts) == 1 or parts[1] == 'toggle':
            self.toggle_theme()
        elif len(parts) == 2 and parts[1] in ['dark', 'light']:
            new_theme = UITheme(parts[1])
            self.set_theme(new_theme)
            
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        new_theme = UITheme.LIGHT if self.theme == UITheme.DARK else UITheme.DARK
        self.set_theme(new_theme)
        
    def set_theme(self, theme: UITheme):
        """Set a specific theme."""
        self.theme = theme
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        self.status_bar.theme = self.theme
        self.console = Console(theme=self.rich_theme, force_interactive=False)
        
        theme_name = "🌒 Dark" if self.theme == UITheme.DARK else "🌞 Light"
        self._add_to_output(f"Switched to {theme_name} theme", style="info")
        
    def add_agent_output(self, text: str, author: str = "Agent"):
        """Add agent output to the display."""
        # Filter out system messages that shouldn't be displayed
        if self._is_system_noise(text):
            return
        self._add_to_output(f"🤖 {author}: {text}", style="agent")
    
    def _is_system_noise(self, text: str) -> bool:
        """Check if text is system noise that shouldn't be displayed."""
        import re
        
        noise_patterns = [
            r'secure mcp filesystem server running on stdio',
            r'allowed directories:.*workspace',
            r'knowledge graph mcp server running on stdio',
            r'userinput.*enter.*send.*alt.*enter.*newline',
            r'theme:.*dark.*time:.*enter:send'
        ]
        
        text_lower = text.lower()
        for pattern in noise_patterns:
            if re.search(pattern, text_lower):
                return True
        return False
        
    def set_agent_task(self, task: asyncio.Task):
        """Set the current agent task for interruption."""
        self.current_agent_task = task
        
    def register_input_callback(self, callback: Callable[[str], Awaitable[None]]):
        """Register callback for user input."""
        self.input_callback = callback
        
    def register_interrupt_callback(self, callback: Callable[[], Awaitable[None]]):
        """Register callback for agent interruption."""
        self.interrupt_callback = callback
        
    def create_application(self) -> Application:
        """Create the prompt_toolkit Application."""
        # Update theme styles for the layout
        enhanced_theme_config = {
            **self.theme_config,
            'frame.input': 'bg:#2d4a2d' if self.theme == UITheme.DARK else 'bg:#e8f5e8',
            'frame.output': 'bg:#2d2d4a' if self.theme == UITheme.DARK else 'bg:#e8e8f5',
        }
        
        style = Style.from_dict(enhanced_theme_config)
        
        # Removed problematic <any> key binding that was interfering
        
        app = Application(
            layout=self.layout,
            key_bindings=self.bindings,
            style=style,
            full_screen=True,
            mouse_support=True,
            editing_mode=EditingMode.EMACS,  # Enable editing mode
        )
        
        # Debug: Print application info
        print(f"DEBUG: Application created successfully")
        print(f"DEBUG: Layout: {self.layout}")
        print(f"DEBUG: Key bindings count: {len(self.bindings.bindings)}")
        
        # Set focus to input buffer so user can type
        app.layout.focus(self.input_buffer)
        print(f"DEBUG: Focus set to input buffer: {self.input_buffer}")
        
        # Start periodic cleanup task
        self._start_cleanup_task()
        
        # Initialize status
        self._update_status()
        
        # Add a test message to verify the UI is working
        self._add_to_output("✅ Interruptible CLI initialized successfully! Type a message and press Enter.", style="info")
        
        # Welcome message
        welcome_msg = """🤖 Advanced AI Agent Development Kit - Interruptible CLI

Features:
• Split-pane interface with persistent input
• Type commands while agent is responding  
• Press Ctrl+C to interrupt long-running agent operations
• Real-time status updates and themed interface
• Markdown rendering for formatted responses (Ctrl+M to toggle)

Type 'help' for commands or start chatting with your agent!

DEBUG: Try typing something and pressing Enter. If you see key debug messages, the app is working."""
        self._add_to_output(welcome_msg, style="welcome")
        
        # Note: Cleanup will be handled by the CLI runner
        
        return app
    
    def _start_cleanup_task(self):
        """Start a periodic task to clean the input buffer."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(0.5)  # Check every 500ms
                self._clean_input_buffer()
                self._update_status()
        
        # Start the cleanup task
        asyncio.create_task(cleanup_loop())
    
    def cleanup(self):
        """Clean up resources."""
        pass  # No cleanup needed since we fixed MCP noise at source

    def _render_markdown(self, text: str) -> str:
        """Convert markdown text to clean, readable formatted text."""
        if not self.markdown_enabled:
            return text
            
        import re
        
        # Convert markdown to clean formatting
        formatted_text = text
        
        # Headers - simple and clean
        formatted_text = re.sub(r'^# (.+)$', r'🔷 \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^## (.+)$', r'🔸 \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^### (.+)$', r'▪️ \1', formatted_text, flags=re.MULTILINE)
        
        # Bold text - just add emphasis without clutter
        formatted_text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', formatted_text)
        formatted_text = re.sub(r'__(.+?)__', r'*\1*', formatted_text)
        
        # Italic text - keep simple
        formatted_text = re.sub(r'\*([^*]+?)\*', r'_\1_', formatted_text)
        formatted_text = re.sub(r'_([^_]+?)_', r'_\1_', formatted_text)
        
        # Code blocks - clean format
        formatted_text = re.sub(r'```(\w+)?\n(.*?)\n```', r'💻 \2', formatted_text, flags=re.DOTALL)
        
        # Inline code - minimal formatting
        formatted_text = re.sub(r'`([^`]+?)`', r'\1', formatted_text)
        
        # Lists - clean bullets
        formatted_text = re.sub(r'^- (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^\* (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^\+ (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
        
        # Numbered lists
        formatted_text = re.sub(r'^(\d+)\. (.+)$', r'\1. \2', formatted_text, flags=re.MULTILINE)
        
        # Links - show just the text, keep URLs subtle
        formatted_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1', formatted_text)
        
        # Blockquotes - simple format
        formatted_text = re.sub(r'^> (.+)$', r'💬 \1', formatted_text, flags=re.MULTILINE)
        
        # Horizontal rules - simple line
        formatted_text = re.sub(r'^---+$', r'─' * 40, formatted_text, flags=re.MULTILINE)
        
        return formatted_text


def get_interruptible_cli_instance(theme: Optional[str] = None) -> InterruptibleCLI:
    """Factory function to create an InterruptibleCLI instance."""
    ui_theme: Optional[UITheme] = None
    if theme:
        try:
            ui_theme = UITheme(theme.lower())
        except ValueError:
            pass  # Use auto-detected theme
    
    return InterruptibleCLI(ui_theme)

def get_cli_instance(theme: Optional[str] = None) -> EnhancedCLI:
    """Factory function to create a CLI instance with the specified theme."""
    ui_theme: Optional[UITheme] = None
    if theme:
        try:
            ui_theme = UITheme(theme.lower())
        except ValueError:
            pass  # Use auto-detected theme
    
    return EnhancedCLI(ui_theme) 