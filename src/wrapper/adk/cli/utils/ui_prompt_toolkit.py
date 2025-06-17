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

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional, Callable, Any, Awaitable
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from prompt_toolkit import PromptSession, Application
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter, Completer, Completion
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
from prompt_toolkit.layout.menus import CompletionsMenu

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from .ui_common import UITheme, ThemeConfig, StatusBar
from .ui_rich import RichRenderer


class EnhancedCLI:
    """Enhanced CLI with tmux-style interface and theming."""
    
    def __init__(self, theme: Optional[UITheme] = None, rich_renderer: Optional[RichRenderer] = None):
        # Determine theme from environment or default
        self.theme = theme or self._detect_theme()
        self.theme_config = ThemeConfig.get_theme_config(self.theme)
        self.rich_renderer = rich_renderer or RichRenderer(self.theme)
        self.status_bar = StatusBar(self.theme)
        # Configure console to preserve scrollback behavior
        self.console = Console(
            theme=self.rich_renderer.rich_theme,
            force_interactive=False,  # Disable animations that might interfere with scrollback
            legacy_windows=False,     # Use modern terminal features
            soft_wrap=True,           # Enable soft wrapping to prevent cropping
            width=None,               # Auto-detect width to avoid fixed sizing issues
            height=None               # Auto-detect height to avoid fixed sizing issues
        )
        
        # Interruptible CLI attributes
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
                'list all the user applications in the qa- namespaces',
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
        self.rich_renderer.theme = self.theme # Update renderer's theme
        self.rich_renderer.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        self.rich_renderer.console = Console(theme=self.rich_renderer.rich_theme, force_interactive=False, legacy_windows=False, soft_wrap=True, width=None, height=None)
        self.status_bar.theme = self.theme
        self.console = Console(
            theme=self.rich_renderer.rich_theme,
            force_interactive=False,  # Disable animations that might interfere with scrollback
            legacy_windows=False,     # Use modern terminal features
            soft_wrap=True,           # Enable soft wrapping to prevent cropping
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
            self.rich_renderer.theme = self.theme # Update renderer's theme
            self.rich_renderer.rich_theme = ThemeConfig.get_rich_theme(self.theme)
            self.rich_renderer.console = Console(theme=self.rich_renderer.rich_theme, force_interactive=False, legacy_windows=False, soft_wrap=True, width=None, height=None)
            self.status_bar.theme = self.theme
            self.console = Console(
                theme=self.rich_renderer.rich_theme,
                force_interactive=False,  # Disable animations that might interfere with scrollback
                legacy_windows=False,     # Use modern terminal features
                soft_wrap=True,           # Enable soft wrapping to prevent cropping
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
        # This method should now use rich_renderer to format the response
        # and then return a Rich Panel object
        return self.rich_renderer.format_agent_response_panel(text, author)
    
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
        """Add agent output with the same Rich Panel formatting as EnhancedCLI."""
        # Use the rich_renderer to format the response into a Panel
        panel = self.rich_renderer.format_agent_response_panel(text, author)
        
        # Print the panel directly to console
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


    def _render_markdown(self, text: str) -> str:
        """Render markdown using Rich's Markdown directly, without Panel wrapper."""
        return self.rich_renderer._render_markdown(text)

    def _basic_markdown_fallback(self, text: str) -> str:
        """Basic markdown rendering fallback if Rich fails."""
        return self.rich_renderer._basic_markdown_fallback(text)


# class InterruptibleCLI:
#     """CLI with persistent input pane and agent interruption capabilities."""
    
#     def __init__(self, theme: Optional[UITheme] = None, rich_renderer: Optional[RichRenderer] = None):
#         self.theme = theme or UITheme.DARK
#         self.theme_config = ThemeConfig.get_theme_config(self.theme)
#         self.rich_renderer = rich_renderer or RichRenderer(self.theme)
#         self.status_bar = StatusBar(self.theme)
#         self.console = Console(theme=self.rich_renderer.rich_theme, force_interactive=False)
        
#         # State management
#         self.agent_running = False
#         self.current_agent_task: Optional[asyncio.Task] = None
#         self.input_callback: Optional[Callable[[str], Awaitable[None]]] = None
#         self.interrupt_callback: Optional[Callable[[], Awaitable[None]]] = None
        
#         # Session and agent info
#         import uuid
#         self.session_id = str(uuid.uuid4())
#         self.agent_name = "agent"  # Default agent name
        
#         # Markdown rendering toggle
#         self.markdown_enabled = True  # Enable markdown by default
        
#         # Agent thought display toggle
#         self.agent_thought_enabled = True  # Enable agent thought display by default
#         self.agent_thought_buffer = []  # Store agent thoughts
        
#         # UI Components with completion support
#         self.input_buffer = Buffer(
#             multiline=True,
#             completer=self._create_completer(),
#             auto_suggest=AutoSuggestFromHistory(),
#             history=InMemoryHistory(),
#         )
#         self.output_buffer = Buffer()
#         self.status_buffer = Buffer()
#         self.thought_buffer = Buffer()  # Buffer for agent thoughts
        
#         # Manual history tracking for reliable navigation
#         self.command_history = []
#         self.history_index = -1
        
#         self._setup_layout()
#         self._setup_key_bindings()

#     def _create_completer(self):
#         """Create the same categorized completer as regular CLI."""
        
#         # Same categorized commands as regular CLI
#         categorized_commands = {
#             '🔍 Code Analysis': [
#                 'analyze this code', 'review the codebase', 'find security vulnerabilities', 
#                 'optimize performance of', 'refactor this function', 'add error handling to',
#                 'add type hints to', 'add documentation for', 'write unit tests for',
#                 'write integration tests for', 'fix the bug in', 'debug this issue',
#             ],
#             '🚀 Infrastructure & DevOps': [
#                 'create a dockerfile', 'create docker-compose.yml', 'write kubernetes manifests',
#                 'create helm chart for', 'write terraform code for', 'setup CI/CD pipeline',
#                 'configure github actions', 'setup monitoring for', 'add logging to',
#                 'create health checks', 'setup load balancer', 'configure autoscaling',
#                 'list the k8s clusters and indicate the current one',
#                 'list all the user applications in the qa- namespaces on the current k8s cluster',
#             ],
#             '📦 Deployment & Operations': [
#                 'deploy to production', 'deploy to staging', 'rollback deployment',
#                 'check service status', 'troubleshoot deployment', 'scale the service',
#                 'update dependencies', 'backup the database', 'restore from backup',
#             ],
#             '🔧 Development Workflow': [
#                 'create new feature branch', 'merge pull request', 'tag new release',
#                 'update changelog', 'bump version number', 'execute regression tests',
#                 'run security scan', 'run performance tests', 'generate documentation',
#             ],
#             '⚙️ CLI Commands': [
#                 'exit', 'quit', 'bye', 'help', 'clear', 'theme toggle', 'theme dark', 'theme light',
#             ],
#         }
        
#         class CategorizedCompleter(Completer):
#             def __init__(self, categorized_commands):
#                 self.categorized_commands = categorized_commands
#                 # Flatten all commands for matching
#                 self.all_commands = []
#                 for category, commands in categorized_commands.items():
#                     self.all_commands.extend(commands)
            
#             def get_completions(self, document, complete_event):
#                 text = document.get_word_before_cursor()
#                 text_lower = text.lower()
                
#                 # Group completions by category
#                 for category, commands in self.categorized_commands.items():
#                     category_matches = []
#                     for command in commands:
#                         if text_lower in command.lower():
#                             category_matches.append(command)
                    
#                     # If we have matches in this category, yield them with category header
#                     if category_matches:
#                         # Add category separator (only visible in completion menu)
#                         yield Completion(
#                             '',
#                             start_position=0,
#                             display=f'{category}',
#                             style='class:completion-menu.category'
#                         )
                        
#                         # Add the actual completions
#                         for command in category_matches:
#                             start_pos = -len(text) if text else 0
#                             yield Completion(
#                                 command,
#                                 start_position=start_pos,
#                                 display=f'  {command}',
#                                 style='class:completion-menu.completion'
#                             )
        
#         return CategorizedCompleter(categorized_commands)

#     def set_agent_name(self, agent_name: str):
#         """Set the agent name for display in status bar."""
#         self.agent_name = agent_name
#         self._update_status()
        
#     def _get_terminal_width(self) -> int:
#         """Get the current terminal width."""
#         try:
#             import shutil
#             return shutil.get_terminal_size().columns
#         except:
#             return 80  # Fallback to 80 columns if unable to detect
        
#     def _setup_layout(self):
#         """Setup the split-pane layout with floating completion menu."""
        
#         # Input area (bottom pane) with completion support
#         input_window = Window(
#             content=BufferControl(
#                 buffer=self.input_buffer,
#                 input_processors=[]
#             ),
#             height=5,  # Fixed height for input pane
#             wrap_lines=True,
#         )
        
#         # Output area (top pane) - width depends on whether thought pane is enabled
#         if self.agent_thought_enabled:
#             # When thought pane is enabled, constrain output width to 60% of available space
#             output_window = Window(
#                 content=BufferControl(
#                     buffer=self.output_buffer
#                 ),
#                 wrap_lines=True,
#                 width=lambda: max(40, int(self._get_terminal_width() * 0.6))  # 60% of terminal width, minimum 40
#             )
#         else:
#             # When thought pane is disabled, output takes full width
#             output_window = Window(
#                 content=BufferControl(
#                     buffer=self.output_buffer
#                 ),
#                 wrap_lines=True,
#             )
        
#         # Agent thought area (side pane) - conditionally shown
#         thought_window = Window(
#             content=BufferControl(
#                 buffer=self.thought_buffer
#             ),
#             width=lambda: max(30, int(self._get_terminal_width() * 0.35)),  # 35% of terminal width, minimum 30
#             wrap_lines=True,
#         )
        
#         # Status area with FormattedTextControl for proper styling
#         status_window = Window(
#             content=FormattedTextControl(
#                 text=self._get_formatted_status,
#                 focusable=False,
#             ),
#             height=1,
#             style="class:bottom-toolbar"
#         )
        
#         # Frame the input area
#         input_frame = Frame(
#             body=input_window,
#             title=self._get_input_title,
#             style="class:frame.input"
#         )
        
#         # Frame the output area  
#         output_frame = Frame(
#             body=output_window,
#             title=self._get_output_title,
#             style="class:frame.output"
#         )
        
#         # Frame the thought area
#         thought_frame = Frame(
#             body=thought_window,
#             title=self._get_thought_title,
#             style="class:frame.thought"
#         )
        
#         # Create main content area with conditional thought pane
#         if self.agent_thought_enabled:
#             # Three-pane layout: Output + Thought side-by-side
#             content_area = HSplit([
#                 VSplit([
#                     output_frame,  # Left: Agent output (60% width)
#                     thought_frame,  # Right: Agent thought (35% width, 5% for borders/padding)
#                 ]),
#                 input_frame,   # Bottom: User input (fixed height)
#             ])
#         else:
#             # Two-pane layout: Just Output + Input
#             content_area = HSplit([
#                 output_frame,  # Top: Agent output (flexible height)
#                 input_frame,   # Bottom: User input (fixed height)
#             ])
        
#         # Main layout with status bar
#         main_layout = HSplit([
#             content_area,  # Main content area
#             status_window, # Bottom: Status bar (fixed height)
#         ])
        
#         # Wrap in FloatContainer to support floating completion menu
#         self.layout = Layout(
#             FloatContainer(
#                 content=main_layout,
#                 floats=[
#                     Float(
#                         content=CompletionsMenu(
#                             max_height=16,
#                             scroll_offset=1,
#                         ),
#                         transparent=True,
#                     ),
#                 ]
#             )
#         )

#     def _get_input_title(self) -> str:
#         """Dynamic title for input pane."""
#         if self.agent_running:
#             return "💭 User Input (Ctrl+C to interrupt agent)"
#         return "😎 User Input (Enter to send, Alt+Enter for newline)"
        
#     def _get_output_title(self) -> str:
#         """Dynamic title for output pane."""
#         if self.agent_running:
#             return "🤖 Agent Output (thinking...)"
#         return "🤖 Agent Output"
        
#     def _get_thought_title(self) -> str:
#         """Dynamic title for thought pane."""
#         if self.agent_thought_enabled:
#             return "🤖 Agent Thought"
#         return ""
        
#     def _setup_key_bindings(self):
#         """Setup custom key bindings."""
#         self.bindings = KeyBindings()
        
#         @self.bindings.add('enter', eager=True)
#         def _(event):
#             """Submit user input when Enter is pressed."""
#             content = self.input_buffer.text.strip()
#             if content:
#                 self._add_to_output(f"🔄 Processing: {content}", style="info")
#                 asyncio.create_task(self._handle_user_input(content))
#             else:
#                 self._add_to_output("💡 Type a message and press Enter to send it to the agent", style="info")
        
#         # Alt+Enter for newline (multi-line input)
#         @self.bindings.add('escape', 'enter')
#         def _(event):
#             """Insert newline for multi-line input."""
#             event.current_buffer.insert_text('\n')
        
#         # Ctrl+T for theme toggle
#         @self.bindings.add('c-t')
#         def _(event):
#             """Toggle theme with Ctrl+T."""
#             self.toggle_theme()
#             event.app.invalidate()  # Refresh the display
        
#         # Ctrl+Y for agent thought toggle
#         @self.bindings.add('c-y')
#         def _(event):
#             """Toggle agent thought display with Ctrl+Y."""
#             self.toggle_agent_thought()
#             # Recreate layout with new thought display setting
#             self._setup_layout()
#             # Update the application layout
#             event.app.layout = self.layout
#             # Restore focus to the input buffer
#             event.app.layout.focus(self.input_buffer)
#             event.app.invalidate()  # Refresh the display
        
#         # Ctrl+L for clear screen
#         @self.bindings.add('c-l')
#         def _(event):
#             """Clear the output buffer."""
#             self.output_buffer.text = ""
#             self._add_to_output("🧹 Screen cleared", style="info")
        
#         # Ctrl+D for graceful exit
#         @self.bindings.add('c-d')
#         def _(event):
#             """Exit gracefully with Ctrl+D."""
#             event.app.exit()
        
#         # Tab for completion menu
#         @self.bindings.add('tab')
#         def _(event):
#             """Show completion menu with Tab."""
#             buffer = event.current_buffer
#             if buffer.complete_state:
#                 buffer.complete_next()
#             else:
#                 buffer.start_completion(select_first=False)
        
#         # Up arrow for history navigation (only when at first line and no completion menu)
#         @self.bindings.add('up')
#         def _(event):
#             """Navigate to previous command in history or move cursor up."""
#             buffer = event.current_buffer
            
#             # If completion menu is active, let it handle up/down navigation
#             if buffer.complete_state:
#                 buffer.complete_previous()
#                 return
            
#             # Only navigate history if we're at the first line
#             if buffer.document.cursor_position_row == 0:
#                 if self.command_history and self.history_index > 0:
#                     self.history_index -= 1
#                     buffer.text = self.command_history[self.history_index]
#                     buffer.cursor_position = len(buffer.text)
#             else:
#                 # Default behavior: move cursor up
#                 buffer.cursor_up()
        
#         # Down arrow for history navigation (only when at last line and no completion menu)
#         @self.bindings.add('down')
#         def _(event):
#             """Navigate to next command in history or move cursor down."""
#             buffer = event.current_buffer
            
#             # If completion menu is active, let it handle up/down navigation
#             if buffer.complete_state:
#                 buffer.complete_next()
#                 return
            
#             # Only navigate history if we're at the last line
#             if buffer.document.cursor_position_row == buffer.document.line_count - 1:
#                 if self.command_history:
#                     if self.history_index < len(self.command_history) - 1:
#                         self.history_index += 1
#                         buffer.text = self.command_history[self.history_index]
#                         buffer.cursor_position = len(buffer.text)
#                     elif self.history_index == len(self.command_history) - 1:
#                         # Move past last entry to clear buffer
#                         self.history_index = len(self.command_history)
#                         buffer.text = ""
#                         buffer.cursor_position = 0
#             else:
#                 # Default behavior: move cursor down
#                 buffer.cursor_down()
        

#         # Ctrl+P for previous history (alternative to up arrow)
#         @self.bindings.add('c-p')
#         def _(event):
#             """Navigate to previous command in history."""
#             buffer = event.current_buffer
#             if self.command_history and self.history_index > 0:
#                 self.history_index -= 1
#                 buffer.text = self.command_history[self.history_index]
#                 buffer.cursor_position = len(buffer.text)
        
#         # Ctrl+N for next history (alternative to down arrow)
#         @self.bindings.add('c-n')
#         def _(event):
#             """Navigate to next command in history."""
#             buffer = event.current_buffer
#             if self.command_history:
#                 if self.history_index < len(self.command_history) - 1:
#                     self.history_index += 1
#                     buffer.text = self.command_history[self.history_index]
#                     buffer.cursor_position = len(buffer.text)
#                 elif self.history_index == len(self.command_history) - 1:
#                     # Move past last entry to clear buffer
#                     self.history_index = len(self.command_history)
#                     buffer.text = ""
#                     buffer.cursor_position = 0

#         @self.bindings.add('c-c')
#         def _(event):
#             """Interrupt running agent."""
#             if self.agent_running:
#                 asyncio.create_task(self._interrupt_agent())
#             else:
#                 # Standard Ctrl+C behavior when agent not running
#                 event.app.exit(exception=KeyboardInterrupt)

#     async def _handle_user_input(self, content: str):
#         """Handle user input by calling the registered callback."""
#         # Add command to both histories
#         if content.strip():
#             # Add to prompt_toolkit history
#             if self.input_buffer.history:
#                 self.input_buffer.history.append_string(content.strip())
            
#             # Add to our manual history for reliable navigation
#             self.command_history.append(content.strip())
#             self.history_index = len(self.command_history)  # Reset to end
            
#         if self.input_callback:
#             await self.input_callback(content)
#         self.input_buffer.text = ""

#     async def _interrupt_agent(self):
#         """Interrupt the running agent."""
#         if self.current_agent_task and not self.current_agent_task.done():
#             self.current_agent_task.cancel()
#             self._add_to_output("⏹️ Agent interrupted by user", style="warning")
        
#         if self.interrupt_callback:
#             await self.interrupt_callback()
        
#         self.agent_running = False

#     def _add_to_output(self, text, style: str = "", skip_markdown: bool = False):
#         """Add text to the output buffer."""
#         current_text = self.output_buffer.text
#         if current_text:
#             new_text = current_text + "\n" + text
#         else:
#             new_text = text
#         self.output_buffer.text = new_text

#     def _update_status(self):
#         """Update the status buffer with properly styled formatting matching regular CLI."""
        
#         now = datetime.now()
#         uptime = now - self.status_bar.session_start_time
#         uptime_str = f"{uptime.seconds // 3600:02d}:{(uptime.seconds % 3600) // 60:02d}:{uptime.seconds % 60:02d}"
        
#         # Add agent thought status indicator
#         thought_indicator = "🧠ON" if self.agent_thought_enabled else "🧠OFF"
        
#         # Create status segments with proper styling like regular CLI
#         formatted_parts = [
#             ("class:bottom-toolbar.accent", f" 🤖 {self.agent_name} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.info", f" Session: {self.session_id[:8]}... "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.info", f" Uptime: {uptime_str} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.accent", f" {now.strftime('%H:%M:%S')} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.info", f" {thought_indicator} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar", " Enter:send | Alt+Enter:multi-line | Ctrl+D:exit | Ctrl+L:clear | Ctrl+C:interrupt | Ctrl+Y:thought"),
#         ]
        
#         return FormattedText(formatted_parts)

#     def add_agent_output(self, text: str, author: str = "Agent"):
#         """Add agent output with the same Rich Panel formatting as EnhancedCLI."""
#         # Use the rich_renderer to format the response into a string for the text buffer
#         panel_text = self.rich_renderer.format_agent_response(text, author)
        
#         # Add the formatted panel text to output buffer
#         self._add_to_output(panel_text.rstrip(), style="agent", skip_markdown=True)

#     def set_agent_task(self, task: asyncio.Task):
#         """Set the current agent task for interruption."""
#         self.current_agent_task = task
        
#     def register_input_callback(self, callback: Callable[[str], Awaitable[None]]):
#         """Register callback for user input."""
#         self.input_callback = callback
        
#     def register_interrupt_callback(self, callback: Callable[[], Awaitable[None]]):
#         """Register callback for agent interruption."""
#         self.interrupt_callback = callback
        
#     def create_application(self) -> Application:
#         """Create the prompt_toolkit Application."""
#         enhanced_theme_config = {
#             **self.theme_config,
#             'frame.input': 'bg:#2d4a2d' if self.theme == UITheme.DARK else 'bg:#e8f5e8',
#             'frame.output': 'bg:#2d2d4a' if self.theme == UITheme.DARK else 'bg:#e8e8f5',
#         }
        
#         style = Style.from_dict(enhanced_theme_config)
        
#         app = Application(
#             layout=self.layout,
#             key_bindings=self.bindings,
#             style=style,
#             full_screen=True,
#             mouse_support=True,
#             editing_mode=EditingMode.EMACS,
#         )
        
#         app.layout.focus(self.input_buffer)
#         self._update_status()
        
#         return app

#     def display_agent_welcome(self, agent_name: str, agent_description: str = "", tools: Optional[list] = None):
#         """Display a comprehensive welcome message with agent information and capabilities."""
#         theme_indicator = "🌒" if self.theme == UITheme.DARK else "🌞"
        
#         welcome_msg = f"""
#                 ▄▀█ █   ▄▀█ █▀▀ █▀▀ █▄█ ▀█▀
#                 █▀█ █   █▀█ █▄█ █▄▄ █░█ ░█░

# 🤖 Advanced AI Agent Development Kit - Interruptible CLI

# Agent: {agent_name}"""
        
#         if agent_description:
#             welcome_msg += f"\nDescription: {agent_description[:150]}{'...' if len(agent_description) > 150 else ''}"
        
#         welcome_msg += f"""
# Theme: {theme_indicator} {self.theme.value.title()}
# Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 

# Features:
# • Split-pane interface with persistent input
# • Type commands while agent is responding  
# • Press Ctrl+C to interrupt long-running agent operations
# • Real-time status updates and themed interface
# • Rich formatted agent responses with panels and markdown

# Ready for your DevOps challenges! 🚀
# """
        
#         self._add_to_output(welcome_msg, style="welcome")
#         self._add_to_output("✅ Interruptible CLI initialized successfully! The agent is ready for your questions.", style="info")

#     def cleanup(self):
#         """Clean up CLI resources."""
#         pass  # No specific cleanup needed for InterruptibleCLI

#     def _get_formatted_status(self):
#         """Get formatted status for the status bar with proper styling."""
        
#         now = datetime.now()
#         uptime = now - self.status_bar.session_start_time
#         uptime_str = f"{uptime.seconds // 3600:02d}:{(uptime.seconds % 3600) // 60:02d}:{uptime.seconds % 60:02d}"
        
#         # Add agent thought status indicator
#         thought_indicator = "🧠ON" if self.agent_thought_enabled else "🧠OFF"
        
#         # Create status segments with proper styling like regular CLI
#         formatted_parts = [
#             ("class:bottom-toolbar.accent", f" 🤖 {self.agent_name} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.info", f" Session: {self.session_id[:8]}... "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.info", f" Uptime: {uptime_str} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.accent", f" {now.strftime('%H:%M:%S')} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar.info", f" {thought_indicator} "),
#             ("class:bottom-toolbar", " | "),
#             ("class:bottom-toolbar", " Enter:send | Alt+Enter:multi-line | Ctrl+D:exit | Ctrl+L:clear | Ctrl+C:interrupt | Ctrl+Y:thought"),
#         ]
        
#         return FormattedText(formatted_parts)

#     def toggle_theme(self) -> None:
#         """Toggle between light and dark themes."""
#         self.theme = UITheme.LIGHT if self.theme == UITheme.DARK else UITheme.DARK
#         self.theme_config = ThemeConfig.get_theme_config(self.theme)
#         self.rich_renderer.theme = self.theme # Update renderer's theme
#         self.rich_renderer.rich_theme = ThemeConfig.get_rich_theme(self.theme)
#         self.rich_renderer.console = Console(theme=self.rich_renderer.rich_theme, force_interactive=False)
#         self.status_bar.theme = self.theme
#         self.console = Console(theme=self.rich_renderer.rich_theme, force_interactive=False)
        
#         theme_name = "🌒 Dark" if self.theme == UITheme.DARK else "🌞 Light"
#         self._add_to_output(f"🎨 Switched to {theme_name} theme", style="info")
        
#         # Recreate the application with new theme
#         # Note: In a real implementation, you'd want to update the existing app's style
#         # For now, we'll just show the message

#     def toggle_agent_thought(self) -> None:
#         """Toggle agent thought display on/off."""
#         self.agent_thought_enabled = not self.agent_thought_enabled
#         thought_status = "enabled" if self.agent_thought_enabled else "disabled"
#         self._add_to_output(f"🧠 Agent thought display {thought_status}", style="info")
        
#         # Clear thought buffer when disabling
#         if not self.agent_thought_enabled:
#             self.thought_buffer.text = ""

#     def add_agent_thought(self, thought_summaries: list):
#         """Add agent thought summaries to the thought display."""
#         if not self.agent_thought_enabled or not thought_summaries:
#             return
            
#         # Combine multiple thought summaries if present
#         combined_thoughts = "\n\n".join(thought_summaries)
        
#         # Truncate very long thoughts for display
#         max_display_length = 800
#         if len(combined_thoughts) > max_display_length:
#             display_text = combined_thoughts[:max_display_length] + "..."
#         else:
#             display_text = combined_thoughts
        
#         # Add to thought buffer
#         current_thought_text = self.thought_buffer.text
#         if current_thought_text:
#             new_thought_text = current_thought_text + "\n\n" + f"🧠 Agent Thought:\n{display_text}"
#         else:
#             new_thought_text = f"🧠 Agent Thought:\n{display_text}"
        
#         self.thought_buffer.text = new_thought_text
