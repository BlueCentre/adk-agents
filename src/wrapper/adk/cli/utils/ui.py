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
            # no_color=False,           # Keep colors but ensure compatibility
            width=None,               # Auto-detect width to avoid fixed sizing issues
            height=None               # Auto-detect height to avoid fixed sizing issues
        )
        
        # Interruptible CLI attributes
        self.markdown_enabled = True  # Enable markdown by default
        self.agent_running = False
        self.current_agent_task: Optional[asyncio.Task] = None
        self.input_callback: Optional[Callable[[str], Awaitable[None]]] = None
        self.interrupt_callback: Optional[Callable[[], Awaitable[None]]] = None
        
        # UI Components for interruptible mode
        self.input_buffer = Buffer(multiline=True)
        self.output_buffer = Buffer()
        self.status_buffer = Buffer()
        self.layout = None  # Will be set when needed
        self.bindings = None  # Will be set when needed
        
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
            # no_color=False,           # Keep colors but ensure compatibility
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
                # no_color=False,           # Keep colors but ensure compatibility
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

    def add_agent_output(self, text: str, author: str = "Agent"):
        """Add agent output with Rich Panel formatting, matching the regular CLI style."""
        panel = self.format_agent_response(text, author)
        self.console.print(panel)

    def _add_to_output(self, text: str, style: str = "", skip_markdown: bool = False):
        """Add text to the output buffer for interruptible CLI mode."""
        if hasattr(self, 'output_buffer') and self.output_buffer:
            # Add text to the output buffer
            current_text = self.output_buffer.text
            if current_text:
                new_text = current_text + "\n" + text
            else:
                new_text = text
            self.output_buffer.text = new_text
        else:
            # Fallback to console print
            self.console.print(text)

    def _update_status(self):
        """Update the status buffer."""
        if hasattr(self, 'status_buffer') and self.status_buffer:
            status_text = f"Agent: {'running' if self.agent_running else 'ready'} | Theme: {self.theme.value}"
            self.status_buffer.text = status_text

    def _clean_input_buffer(self):
        """Clean the input buffer."""
        if hasattr(self, 'input_buffer') and self.input_buffer:
            # Only clear if there's no user input
            if not self.input_buffer.text.strip():
                self.input_buffer.reset()

    def _setup_layout(self):
        """Setup the interruptible CLI layout."""
        if not hasattr(self, 'input_buffer'):
            return
            
        # Input area (bottom pane)
        input_window = Window(
            content=BufferControl(buffer=self.input_buffer),
            height=5,
            wrap_lines=True,
        )
        
        # Output area (top pane)
        output_window = Window(
            content=BufferControl(buffer=self.output_buffer),
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
            title="User Input",
            style="class:frame.input"
        )
        
        # Frame the output area  
        output_frame = Frame(
            body=output_window,
            title="Agent Output",
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

    def _setup_key_bindings(self):
        """Setup key bindings for interruptible mode."""
        self.bindings = KeyBindings()
        
        @self.bindings.add('enter', eager=True)
        def _(event):
            """Submit user input when Enter is pressed."""
            if hasattr(self, 'input_buffer') and self.input_buffer:
                content = self.input_buffer.text.strip()
                if content and self.input_callback:
                    # Create task from the callback
                    asyncio.create_task(self.input_callback(content))
                    self.input_buffer.text = ""

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
        # Initialize layout and bindings if not already done (for interruptible mode)
        if self.layout is None:
            self._setup_layout()
        if self.bindings is None:
            self._setup_key_bindings()
            
        # Update theme styles for the layout
        enhanced_theme_config = {
            **self.theme_config,
            'frame.input': 'bg:#2d4a2d' if self.theme == UITheme.DARK else 'bg:#e8f5e8',
            'frame.output': 'bg:#2d2d4a' if self.theme == UITheme.DARK else 'bg:#e8e8f5',
        }
        
        style = Style.from_dict(enhanced_theme_config)
        
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
        if self.bindings:
            print(f"DEBUG: Key bindings count: {len(self.bindings.bindings)}")
        
        # Set focus to input buffer so user can type
        if hasattr(self, 'input_buffer') and self.input_buffer:
            app.layout.focus(self.input_buffer)
            print(f"DEBUG: Focus set to input buffer: {self.input_buffer}")
        
        # Start periodic cleanup task
        self._start_cleanup_task()
        
        # Initialize status
        self._update_status()
        
        return app

    def display_agent_welcome(self, agent_name: str, agent_description: str = "", tools: Optional[list] = None):
        """Display a comprehensive welcome message with agent information and capabilities."""
        theme_indicator = "🌒" if self.theme == UITheme.DARK else "🌞"
        
        # Welcome ASCII Art Logo
        welcome_msg = f"""
                ▄▀█ █   ▄▀█ █▀▀ █▀▀ █▄█ ▀█▀
                █▀█ █   █▀█ █▄█ █▄▄ █░█ ░█░

🤖 Advanced AI Agent Development Kit - Interruptible CLI

Agent: {agent_name}"""
        
        if agent_description:
            welcome_msg += f"\nDescription: {agent_description[:150]}{'...' if len(agent_description) > 150 else ''}"
        
        welcome_msg += f"""
Theme: {theme_indicator} {self.theme.value.title()}
Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Features:
• Split-pane interface with persistent input
• Type commands while agent is responding
• Press Ctrl+C to interrupt long-running agent operations
• Real-time status updates and themed interface
• Markdown rendering for formatted responses (Ctrl+M to toggle)
"""
        
        # Add comprehensive tools information if available
        if tools:
            # Categorize tools for better organization
            tool_categories = {
                'filesystem': [],
                'shell': [],
                'analysis': [],
                'search': [],
                'rag': [],
                'memory': [],
                'other': []
            }
            
            for tool in tools:
                tool_name = getattr(tool, 'name', 'unknown')
                tool_desc = getattr(tool, 'description', 'No description available')
                
                # Categorize based on tool name patterns
                if any(keyword in tool_name.lower() for keyword in ['file', 'dir', 'read', 'write', 'edit']):
                    tool_categories['filesystem'].append((tool_name, tool_desc))
                elif any(keyword in tool_name.lower() for keyword in ['shell', 'command', 'execute']):
                    tool_categories['shell'].append((tool_name, tool_desc))
                elif any(keyword in tool_name.lower() for keyword in ['analyze', 'analysis', 'code']):
                    tool_categories['analysis'].append((tool_name, tool_desc))
                elif any(keyword in tool_name.lower() for keyword in ['search', 'google', 'grounding']):
                    tool_categories['search'].append((tool_name, tool_desc))
                elif any(keyword in tool_name.lower() for keyword in ['rag', 'index', 'retrieve', 'context']):
                    tool_categories['rag'].append((tool_name, tool_desc))
                elif any(keyword in tool_name.lower() for keyword in ['memory', 'session', 'save', 'load']):
                    tool_categories['memory'].append((tool_name, tool_desc))
                else:
                    tool_categories['other'].append((tool_name, tool_desc))
            
            welcome_msg += f"\n📋 Available Agent Tools ({len(tools)} total):\n"
            
            # Display categorized tools
            category_icons = {
                'filesystem': '📁',
                'shell': '🐚',
                'analysis': '🔍',
                'search': '🔎',
                'rag': '🧠',
                'memory': '💾',
                'other': '🔧'
            }
            
            category_names = {
                'filesystem': 'File System Tools',
                'shell': 'Shell & Command Tools',
                'analysis': 'Code Analysis Tools',
                'search': 'Search & Grounding Tools',
                'rag': 'RAG & Context Tools',
                'memory': 'Memory & Session Tools',
                'other': 'Other Tools'
            }
            
            for category, tool_list in tool_categories.items():
                if tool_list:
                    icon = category_icons.get(category, '🔧')
                    cat_name = category_names.get(category, category.title())
                    welcome_msg += f"\n  {icon} {cat_name} ({len(tool_list)}):\n"
                    
                    for tool_name, tool_desc in tool_list[:5]:  # Show first 5 tools per category
                        # Truncate long descriptions
                        if tool_desc and len(tool_desc) > 80:
                            tool_desc = tool_desc[:77] + "..."
                        welcome_msg += f"    • {tool_name} - {tool_desc}\n"
                    
                    if len(tool_list) > 5:
                        welcome_msg += f"    ... and {len(tool_list) - 5} more {category} tools\n"
        
        # Try to get environment capabilities
        try:
            # Import the tool discovery from devops agent if available
            from agents.devops.tools.dynamic_discovery import tool_discovery
            env_capabilities = tool_discovery.discover_environment_capabilities()
            
            available_tools = [t for t in env_capabilities.tools.values() if t.available]
            if available_tools:
                welcome_msg += f"\n🌐 Environment Tools ({len(available_tools)} available):\n"
                for tool in available_tools[:8]:  # Show first 8 environment tools
                    welcome_msg += f"  ✅ {tool.name} v{tool.version} - {tool.description}\n"
                
                if len(available_tools) > 8:
                    welcome_msg += f"  ... and {len(available_tools) - 8} more available\n"
            
            unavailable_count = len([t for t in env_capabilities.tools.values() if not t.available])
            if unavailable_count > 0:
                welcome_msg += f"\n💡 Note: {unavailable_count} additional environment tools could be installed\n"
        
        except Exception as e:
            # If we can't get environment capabilities, that's okay
            pass
        
        welcome_msg += """\n
🎯 Quick Start:
  • Type your questions or commands naturally
  • Use 'help' to see available commands
  • Press Ctrl+C to interrupt long-running operations
  • Press Ctrl+M to toggle markdown rendering
  • Press Ctrl+T to switch themes

Ready for your DevOps challenges! 🚀
"""
        
        self._add_to_output(welcome_msg, style="welcome")
        self._add_to_output("✅ Interruptible CLI initialized successfully! The agent is ready for your questions.", style="info")
    
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
        """Render markdown using Rich's Markdown directly, without Panel wrapper."""
        if not self.markdown_enabled:
            return text
            
        try:
            from rich.markdown import Markdown
            from rich.console import Console
            from io import StringIO
            
            # Use Rich's Markdown directly (same as regular CLI but without Panel)
            markdown_obj = Markdown(text)
            
            # Render to plain text that works in prompt_toolkit
            string_io = StringIO()
            temp_console = Console(
                file=string_io,
                force_terminal=False,
                # width=200,  # Much wider to prevent truncation
                # no_color=True,  # No ANSI codes for prompt_toolkit compatibility
                legacy_windows=False,
            )
            
            # Print the markdown object directly (no Panel wrapper)
            temp_console.print(markdown_obj, crop=False, overflow="ignore", soft_wrap=False)
            rendered_output = string_io.getvalue()
            
            return rendered_output.rstrip()
            
        except ImportError:
            # Fallback to basic markdown if Rich is not available
            return self._basic_markdown_fallback(text)
        except Exception as e:
            # If Rich markdown fails, fall back to basic rendering
            return self._basic_markdown_fallback(text)

    def _basic_markdown_fallback(self, text: str) -> str:
        """Basic markdown rendering fallback if Rich fails."""
        import re
        
        formatted_text = text
        
        # Headers with better styling
        formatted_text = re.sub(r'^# (.+)$', r'🔷 \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^## (.+)$', r'🔸 \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^### (.+)$', r'▪️ \1', formatted_text, flags=re.MULTILINE)
        
        # Basic bold and italic (simplified)
        formatted_text = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', formatted_text)  # Keep bold markers
        formatted_text = re.sub(r'\*([^*]+)\*', r'*\1*', formatted_text)  # Keep italic markers
        
        # Lists
        formatted_text = re.sub(r'^\* ', '• ', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^\+ ', '• ', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^- ', '• ', formatted_text, flags=re.MULTILINE)
        
        # Blockquotes
        formatted_text = re.sub(r'^> (.+)$', r'┃ \1', formatted_text, flags=re.MULTILINE)
        
        # Code (simplified)
        formatted_text = re.sub(r'`([^`]+)`', r'`\1`', formatted_text)  # Keep code markers
        formatted_text = re.sub(r'^#### (.+)$', r'  • \1', formatted_text, flags=re.MULTILINE)
        
        # Bold and italic - preserve some emphasis
        formatted_text = re.sub(r'\*\*(.+?)\*\*', r'[\1]', formatted_text)  # Bold in brackets
        formatted_text = re.sub(r'__(.+?)__', r'[\1]', formatted_text)
        formatted_text = re.sub(r'\*([^*]+?)\*', r'(\1)', formatted_text)  # Italic in parentheses
        formatted_text = re.sub(r'_([^_]+?)_', r'(\1)', formatted_text)
        
        # Code blocks with language detection
        def format_code_block(match):
            lang = match.group(1) or 'text'
            code = match.group(2).strip()
            return f'💻 {lang.upper()} Code:\n{code}\n'
        
        formatted_text = re.sub(r'```(\w+)?\n(.*?)\n```', format_code_block, formatted_text, flags=re.DOTALL)
        
        # Inline code with backticks
        formatted_text = re.sub(r'`([^`]+?)`', r'`\1`', formatted_text)
        
        # Lists with better bullets
        formatted_text = re.sub(r'^- (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^\* (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^\+ (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
        
        # Numbered lists with emojis
        formatted_text = re.sub(r'^1\. (.+)$', r'1️⃣ \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^2\. (.+)$', r'2️⃣ \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^3\. (.+)$', r'3️⃣ \1', formatted_text, flags=re.MULTILINE)
        formatted_text = re.sub(r'^(\d+)\. (.+)$', r'\1. \2', formatted_text, flags=re.MULTILINE)
        
        # Links - show both text and URL
        formatted_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1 (\2)', formatted_text)
        
        # Blockquotes with better styling
        formatted_text = re.sub(r'^> (.+)$', r'💬 \1', formatted_text, flags=re.MULTILINE)
        
        # Horizontal rules
        formatted_text = re.sub(r'^---+$', r'─' * 50, formatted_text, flags=re.MULTILINE)
        
        # Tables - basic support
        def format_table_row(match):
            cells = [cell.strip() for cell in match.group(0).split('|')[1:-1]]
            return ' │ '.join(cells)
        
        formatted_text = re.sub(r'^\|(.+)\|$', format_table_row, formatted_text, flags=re.MULTILINE)
        
        return formatted_text


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
        
        # UI Components
        self.input_buffer = Buffer(multiline=True)
        self.output_buffer = Buffer()
        self.status_buffer = Buffer()
        
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
        
        @self.bindings.add('enter', eager=True)
        def _(event):
            """Submit user input when Enter is pressed."""
            content = self.input_buffer.text.strip()
            if content:
                self._add_to_output(f"🔄 Processing: {content}", style="info")
                asyncio.create_task(self._handle_user_input(content))
            else:
                self._add_to_output("💡 Type a message and press Enter to send it to the agent", style="info")
        
        @self.bindings.add('c-c')
        def _(event):
            """Interrupt running agent."""
            if self.agent_running:
                asyncio.create_task(self._interrupt_agent())
            else:
                # Standard Ctrl+C behavior when agent not running
                event.app.exit(exception=KeyboardInterrupt)

    async def _handle_user_input(self, content: str):
        """Handle user input by calling the registered callback."""
        if self.input_callback:
            await self.input_callback(content)
        self.input_buffer.text = ""

    async def _interrupt_agent(self):
        """Interrupt the running agent."""
        if self.current_agent_task and not self.current_agent_task.done():
            self.current_agent_task.cancel()
            self._add_to_output("⏹️ Agent interrupted by user", style="warning")
        
        if self.interrupt_callback:
            await self.interrupt_callback()
        
        self.agent_running = False

    def _add_to_output(self, text, style: str = "", skip_markdown: bool = False):
        """Add text to the output buffer."""
        current_text = self.output_buffer.text
        if current_text:
            new_text = current_text + "\n" + text
        else:
            new_text = text
        self.output_buffer.text = new_text

    def _update_status(self):
        """Update the status buffer."""
        status_text = f"Agent: {'running' if self.agent_running else 'ready'} | Theme: {self.theme.value}"
        self.status_buffer.text = status_text

    def add_agent_output(self, text: str, author: str = "Agent"):
        """Add agent output with the same Rich Panel formatting as EnhancedCLI."""
        # Use the same formatting logic as EnhancedCLI for consistency
        markdown_text = Markdown(text)
        
        # Use the same panel style as EnhancedCLI
        if self.theme == UITheme.DARK:
            border_style = "green"
            title_style = "bold green"
        else:
            border_style = "dark_green" 
            title_style = "bold dark_green"
            
        panel = Panel(
            markdown_text,
            title=f"🤖 [{title_style}]{author}[/{title_style}]",
            border_style=border_style,
            expand=True
        )
        
        # Render panel to string format that works with prompt_toolkit
        from io import StringIO
        string_io = StringIO()
        temp_console = Console(
            file=string_io,
            force_terminal=False,
            width=120,  # Wider width for better formatting
            legacy_windows=False,
        )
        
        # Print the panel
        temp_console.print(panel, crop=False, overflow="ignore")
        panel_text = string_io.getvalue()
        
        # Add the formatted panel to output
        self._add_to_output(panel_text.rstrip(), style="agent", skip_markdown=True)

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
        enhanced_theme_config = {
            **self.theme_config,
            'frame.input': 'bg:#2d4a2d' if self.theme == UITheme.DARK else 'bg:#e8f5e8',
            'frame.output': 'bg:#2d2d4a' if self.theme == UITheme.DARK else 'bg:#e8e8f5',
        }
        
        style = Style.from_dict(enhanced_theme_config)
        
        app = Application(
            layout=self.layout,
            key_bindings=self.bindings,
            style=style,
            full_screen=True,
            mouse_support=True,
            editing_mode=EditingMode.EMACS,
        )
        
        app.layout.focus(self.input_buffer)
        self._update_status()
        
        return app

    def display_agent_welcome(self, agent_name: str, agent_description: str = "", tools: Optional[list] = None):
        """Display a comprehensive welcome message with agent information and capabilities."""
        theme_indicator = "🌒" if self.theme == UITheme.DARK else "🌞"
        
        welcome_msg = f"""
                ▄▀█ █   ▄▀█ █▀▀ █▀▀ █▄█ ▀█▀
                █▀█ █   █▀█ █▄█ █▄▄ █░█ ░█░

🤖 Advanced AI Agent Development Kit - Interruptible CLI

Agent: {agent_name}"""
        
        if agent_description:
            welcome_msg += f"\nDescription: {agent_description[:150]}{'...' if len(agent_description) > 150 else ''}"
        
        welcome_msg += f"""
Theme: {theme_indicator} {self.theme.value.title()}
Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Features:
• Split-pane interface with persistent input
• Type commands while agent is responding  
• Press Ctrl+C to interrupt long-running agent operations
• Real-time status updates and themed interface
• Rich formatted agent responses with panels and markdown

Ready for your DevOps challenges! 🚀
"""
        
        self._add_to_output(welcome_msg, style="welcome")
        self._add_to_output("✅ Interruptible CLI initialized successfully! The agent is ready for your questions.", style="info")


def get_interruptible_cli_instance(theme: Optional[str] = None) -> InterruptibleCLI:
    """Factory function to create an InterruptibleCLI instance with enhanced agent response formatting."""
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