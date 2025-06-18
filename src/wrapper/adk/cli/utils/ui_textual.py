from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional, Callable, Any, Awaitable, Union

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Input, RichLog, Label, Static, OptionList
from textual.widgets.option_list import Option
from textual.binding import Binding
from textual.events import Key
from textual.reactive import reactive
from textual import work
from textual.screen import ModalScreen

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .ui_common import UITheme, ThemeConfig
from .ui_rich import RichRenderer


class AgentTUI(App):
    """
    A Textual application that serves as the main User Interface (UI) for the ADK Agent.

    This class extends Textual's `App` and provides a rich interactive command-line
    experience with multiple panes (output, thought, input), real-time status updates,
    and intelligent command completion.

    Key Features:
    - Multi-pane layout: Displays agent output, agent thoughts, and user input areas.
    - Reactive state management: Tracks agent's running/thinking status, token usage,
      and tool usage in real-time.
    - Theming: Supports toggling between light and dark themes.
    - Command History and Tab Completion: Enhances user input with history navigation
      and categorized command suggestions.
    - Interruptible Agent Operations: Allows users to interrupt long-running agent tasks.
    - Dynamic Status Bar: Provides a clear overview of the agent's status, session ID,
      token metrics, and last used tool.

    The UI is designed to provide comprehensive feedback on the agent's operations,
    making it easier to monitor and interact with the agent.
    """

    CSS_PATH = "ui_textual.tcss"

    BINDINGS = [
        Binding("alt+enter", "insert_newline", "New Line", show=False),
        Binding("ctrl+t", "toggle_theme", "Toggle Theme", show=False),
        Binding("ctrl+y", "toggle_agent_thought", "Toggle Thought", show=False),
        Binding("ctrl+l", "clear_output", "Clear Screen", show=False),
        Binding("ctrl+d", "quit", "Quit", show=False),
        Binding("ctrl+c", "interrupt_agent", "Interrupt Agent", show=False),
        # Removed tab binding - handled by CategorizedInput widget directly
        Binding("up", "history_previous", "Previous Command", show=False),
        Binding("down", "history_next", "Next Command", show=False),
        Binding("ctrl+p", "history_previous", "Previous Command", show=False),
        Binding("ctrl+n", "history_next", "Next Command", show=False),
    ]

    agent_running: reactive[bool] = reactive(False)
    agent_thinking: reactive[bool] = reactive(False)
    agent_thought_enabled: reactive[bool] = reactive(True)
    agent_name: reactive[str] = reactive("Agent")
    session_id: reactive[str] = reactive("")
    _uptime: reactive[str] = reactive("00:00:00")
    _current_time: reactive[str] = reactive(datetime.now().strftime('%H:%M:%S'))
    _thinking_animation_index: reactive[int] = reactive(0)
    
    # Token usage tracking
    _prompt_tokens: reactive[int] = reactive(0)
    _thinking_tokens: reactive[int] = reactive(0)
    _output_tokens: reactive[int] = reactive(0)
    _total_tokens: reactive[int] = reactive(0)
    _model_name: reactive[str] = reactive("Unknown")
    
    # Tool usage tracking
    _tools_used: reactive[int] = reactive(0)
    _last_tool: reactive[str] = reactive("")

    def __init__(self, theme: Optional[UITheme] = None, rich_renderer: Optional[RichRenderer] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_ui_theme = theme or UITheme.DARK
        self.theme_config = ThemeConfig.get_theme_config(self._current_ui_theme)
        self.rich_renderer = rich_renderer or RichRenderer(self._current_ui_theme)
        # self.status_bar = StatusBar(self._current_ui_theme)
        self.console = Console(theme=self.rich_renderer.rich_theme, force_interactive=True)
        self.current_agent_task: Optional[asyncio.Task] = None
        self.input_callback: Optional[Callable[[str], Awaitable[Any]]] = None
        self.interrupt_callback: Optional[Callable[[], Awaitable[Any]]] = None
        self.command_history: list[str] = []
        self.history_index: int = -1
        
        # Thinking animation frames
        self._thinking_frames = ["🤔", "💭", "🧠", "⚡"]
        self._thinking_timer = None

        # Define categorized commands for the completer
        self.categorized_commands = {
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


    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Vertical():
            with Horizontal(id="main-content"):
                yield RichLog(id="output-log", classes="output-pane")
                if self.agent_thought_enabled:
                    yield RichLog(id="thought-log", classes="thought-pane")

            yield CategorizedInput(
                self.categorized_commands,
                id="input-area",
                classes="input-pane",
            )
            yield Static("", id="status-bar")

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.set_interval(5.0, self._update_status)  # Reduced from 1.0 to 5.0 seconds to prevent mouse flickering
        self.query_one("#input-area", CategorizedInput).focus()
        import uuid
        self.session_id = str(uuid.uuid4())[:8]

        self.add_class(self._current_ui_theme.value, "theme-mode")
        
        # Display welcome message if agent info is available
        if hasattr(self, '_pending_welcome_info'):
            self.display_agent_welcome(*self._pending_welcome_info)
            delattr(self, '_pending_welcome_info')
            
        # Schedule footer update after mount is complete
        self.call_after_refresh(self._update_status)

    def _update_status(self) -> None:
        """Update the status bar."""
        # Only update if the app is mounted and screen is available
        if not self.is_mounted:
            return

        # now = datetime.now()
        # uptime = now - self.status_bar.session_start_time
        # self._uptime = f"{uptime.seconds // 3600:02d}:{(uptime.seconds % 3600) // 60:02d}:{uptime.seconds % 60:02d}"
        # self._current_time = now.strftime('%H:%M:%S')

        try:
            # Determine status with thinking animation
            if self.agent_thinking:
                thinking_icon = self._thinking_frames[self._thinking_animation_index % len(self._thinking_frames)]
                status = f"{thinking_icon} Thinking"
            elif self.agent_running:
                status = "🟢 Running"
            else:
                status = "🟢 Ready"
            
            thought_indicator = "🧠 ON" if self.agent_thought_enabled else "🧠 OFF"
            
            # Build comprehensive status like basic CLI
            status_parts = [
                f"🤖 {self.agent_name}",
                f"🧑 Session: {self.session_id}",
                # f"Uptime: {self._uptime}",
                # f"{self._current_time}",
                f"{status}",
                f"{thought_indicator}",
            ]
            
            # Add token usage if available
            if self._total_tokens > 0:
                token_parts = []
                if self._prompt_tokens > 0:
                    token_parts.append(f"P:{self._prompt_tokens}")
                if self._thinking_tokens > 0:
                    token_parts.append(f"T:{self._thinking_tokens}")
                if self._output_tokens > 0:
                    token_parts.append(f"O:{self._output_tokens}")
                token_parts.append(f"Total:{self._total_tokens}")
                status_parts.append(f"Tokens: {', '.join(token_parts)}")
            
            # Add tool usage if available
            if self._tools_used > 0:
                tool_status = f"Tools: {self._tools_used}"
                if self._last_tool:
                    tool_status += f", Last: {self._last_tool}"
                status_parts.append(tool_status)
            
            # Add model info if available
            if self._model_name != "Unknown":
                status_parts.append(f"Model: {self._model_name}")
            
            status_text = " | ".join(status_parts)
            
            # Update the custom status bar
            status_bar_widget = self.query_one("#status-bar", Static)
            status_bar_widget.update(status_text)
            
        except Exception as e:
            # Silently fail footer updates to avoid disrupting the UI
            pass

    def action_insert_newline(self) -> None:
        """Action to insert a newline in the input area."""
        # Input widget doesn't support multiline, so this action is not applicable
        pass

    def action_toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.remove_class(self._current_ui_theme.value)
        self._current_ui_theme = UITheme.LIGHT if self._current_ui_theme == UITheme.DARK else UITheme.DARK
        self.add_class(self._current_ui_theme.value)
        self.theme_config = ThemeConfig.get_theme_config(self._current_ui_theme)
        self.rich_renderer.theme = self._current_ui_theme
        self.rich_renderer.rich_theme = ThemeConfig.get_rich_theme(self._current_ui_theme)
        self.rich_renderer.console = Console(theme=self.rich_renderer.rich_theme, force_interactive=True)
        theme_name = "🌒 Dark" if self._current_ui_theme == UITheme.DARK else "🌞 Light"
        self.add_output(f"[info]Switched to {theme_name} theme[/info]", rich_format=True)

    def action_toggle_agent_thought(self) -> None:
        """Toggle agent thought display."""
        self.agent_thought_enabled = not self.agent_thought_enabled
        
        # Check if thought log already exists
        try:
            thought_log = self.query_one("#thought-log", RichLog)
            if self.agent_thought_enabled:
                # Show the thought log if it's hidden
                thought_log.display = True
            else:
                # Hide the thought log
                thought_log.display = False
        except:
            # Thought log doesn't exist, create it if needed
            if self.agent_thought_enabled:
                main_content = self.query_one("#main-content")
                main_content.mount(RichLog(id="thought-log", classes="thought-pane"))
        
        self.add_output(f"[info]Agent thought display: {'ON' if self.agent_thought_enabled else 'OFF'}[/info]", rich_format=True)

    def start_thinking(self) -> None:
        """Start the thinking animation."""
        self.agent_thinking = True
        if self._thinking_timer is None:
            self._thinking_timer = self.set_interval(0.5, self._animate_thinking)

    def stop_thinking(self) -> None:
        """Stop the thinking animation."""
        self.agent_thinking = False
        if self._thinking_timer is not None:
            self._thinking_timer.stop()
            self._thinking_timer = None
        self._thinking_animation_index = 0

    def _animate_thinking(self) -> None:
        """Animate the thinking indicator."""
        if self.agent_thinking:
            self._thinking_animation_index = (self._thinking_animation_index + 1) % len(self._thinking_frames)

    def action_clear_output(self) -> None:
        """Clear the output log."""
        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        self.add_output("🧹 Screen cleared", rich_format=True)

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    @work
    async def action_interrupt_agent(self) -> None:
        """Interrupt the running agent."""
        if self.agent_running and self.current_agent_task and not self.current_agent_task.done():
            self.current_agent_task.cancel()
            self.add_output("⏹️ Agent interrupted by user", rich_format=True)

        if self.interrupt_callback:
            await self.interrupt_callback()

        self.stop_thinking()
        self.agent_running = False

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submitted from the input area."""
        content = event.value.strip()
        input_widget = self.query_one("#input-area", CategorizedInput)
        input_widget.clear()

        if content:
            # Handle built-in commands
            if content.lower() in ['exit', 'quit', 'bye']:
                self.add_output("👋 Goodbye!", rich_format=True, style="info")
                self.exit()
                return
            elif content.lower() == 'clear':
                self.action_clear_output()
                return
            elif content.lower() == 'help':
                self._show_help()
                return
            elif content.lower().startswith('theme'):
                parts = content.lower().split()
                if len(parts) == 1 or parts[1] == 'toggle':
                    self.action_toggle_theme()
                elif parts[1] == 'dark':
                    self._current_ui_theme = UITheme.DARK
                    self.add_class("dark", "theme-mode")
                    self.remove_class("light", "theme-mode")
                    self.add_output("🌒 Switched to dark theme", rich_format=True, style="info")
                elif parts[1] == 'light':
                    self._current_ui_theme = UITheme.LIGHT
                    self.add_class("light", "theme-mode")
                    self.remove_class("dark", "theme-mode")
                    self.add_output("🌞 Switched to light theme", rich_format=True, style="info")
                return
            
            # Add to history (both app and input widget)
            self.command_history.append(content)
            self.history_index = len(self.command_history)
            input_widget.add_to_history(content)

            # Process user input through callback
            if self.input_callback:
                self.agent_running = True
                self.start_thinking()
                try:
                    # Create task properly for async callback
                    await self.input_callback(content)
                except Exception as e:
                    self.add_output(f"❌ Error processing input: {str(e)}", rich_format=True, style="error")
                finally:
                    self.stop_thinking()
                    self.agent_running = False
        else:
            self.add_output("💡 Type a message and press Enter to send it to the agent", rich_format=True, style="info")

    def _show_help(self):
        """Display help information."""
        help_text = Text.from_markup("""
[bold cyan]🔧 Available Commands:[/bold cyan]

[bold]Built-in Commands:[/bold]
• [yellow]clear[/yellow] - Clear the output screen
• [yellow]help[/yellow] - Show this help message
• [yellow]theme[/yellow] - Toggle between light/dark themes
• [yellow]theme dark[/yellow] - Switch to dark theme
• [yellow]theme light[/yellow] - Switch to light theme
• [yellow]exit/quit/bye[/yellow] - Exit the application

[bold]Keyboard Shortcuts:[/bold]
• [yellow]Ctrl+T[/yellow] - Toggle theme
• [yellow]Ctrl+Y[/yellow] - Toggle agent thought display
• [yellow]Ctrl+L[/yellow] - Clear screen
• [yellow]Ctrl+C[/yellow] - Interrupt running agent
• [yellow]Ctrl+D[/yellow] - Quit application
• [yellow]Up/Down[/yellow] or [yellow]Ctrl+P/Ctrl+N[/yellow] - Navigate command history
• [yellow]Tab[/yellow] - Trigger command completion (cycle through suggestions)
• [yellow]Escape[/yellow] - Cancel current completion

[bold]Tab Completion Examples:[/bold]
• Type [yellow]create a[/yellow] + Tab → "create a dockerfile", "create docker-compose.yml"
• Type [yellow]setup mon[/yellow] + Tab → "setup monitoring for"
• Type [yellow]deploy to[/yellow] + Tab → "deploy to production", "deploy to staging"
• Type [yellow]analyze[/yellow] + Tab → "analyze this code"

[bold]Agent Features:[/bold]
• Type any message to interact with the agent
• Agent responses appear in the main output pane
• Agent thoughts (if enabled) appear in the right pane
• Token usage and tool usage are tracked in real-time
• Use Ctrl+C to interrupt long-running agent operations

[bold green]💡 Tip:[/bold green] This is an advanced multi-pane interface with persistent input, real-time agent interaction, and DevOps-optimized completions!
""")
        self.add_output(help_text, rich_format=True)

    def add_output(self, text: Union[str, Text, Panel], author: str = "User", rich_format: bool = False, style: str = ""):
        """Add text to the output log."""
        output_log = self.query_one("#output-log", RichLog)
        if rich_format:
            if isinstance(text, Panel) or isinstance(text, Text):
                output_log.write(text)
            elif author in ["Agent", "agent"] or "Agent" in author:  # More flexible agent detection
                panel_text = self.rich_renderer.format_agent_response(text, author)
                output_log.write(panel_text)
            else:
                output_log.write(Text(text, style=style))
        else:
            output_log.write(text)

    def add_agent_output(self, text: str, author: str = "Agent"):
        """Add agent output with proper markdown rendering."""
        output_log = self.query_one("#output-log", RichLog)
        panel_text = self.rich_renderer.format_agent_response(text, author)
        output_log.write(panel_text)

    def add_thought(self, text: str):
        """Add text to the agent thought log."""
        if self.agent_thought_enabled:
            thought_log = self.query_one("#thought-log", RichLog)
            thought_log.write(self.rich_renderer.format_agent_thought(text))

    def display_agent_welcome(self, agent_name: str, agent_description: str = "", tools: Optional[list] = None):
        """Display a comprehensive welcome message."""
        # If the app is not yet mounted, store the info for later
        try:
            self.query_one("#output-log", RichLog)
        except:
            self._pending_welcome_info = (agent_name, agent_description, tools)
            return
            
        self.agent_name = agent_name
        theme_indicator = "🌒" if self._current_ui_theme == UITheme.DARK else "🌞"
        thought_status = "ON" if self.agent_thought_enabled else "OFF"

        welcome_msg_rich = Text.from_markup(f"""
[agent]▄▀█ █   ▄▀█ █▀▀ █▀▀ █▄█ ▀█▀[/agent]
[agent]█▀█ █   █▀█ █▄█ █▄▄ █░█ ░█░[/agent]

[bold cyan]🤖 Welcome to {agent_name}![/bold cyan]

[bold]Description:[/bold] {agent_description or "AI Assistant"}
[bold]Tools Available:[/bold] {len(tools) if tools else 0} tools loaded
[bold]Session ID:[/bold] {self.session_id}
[bold]Agent Thoughts:[/bold] {thought_status} (Ctrl+Y to toggle)
[bold]Theme:[/bold] {theme_indicator} {self._current_ui_theme.value.title()}

[bold green]🚀 Ready to assist! Type your message below and press Enter.[/bold green]
[dim]💡 Use 'help' command or Ctrl+T (theme), Ctrl+Y (thoughts), Ctrl+L (clear), Ctrl+D (quit)[/dim]
""")

#         welcome_msg_rich.append(f"""
# [bold]Theme:[/bold] {theme_indicator} {self._current_ui_theme.value.title()}
# [bold]Session started:[/bold] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# [bold green]🚀 Ready to assist! Type your message below and press Enter.[/bold green]
# [dim]💡 Use 'help' command or Ctrl+T (theme), Ctrl+Y (thoughts), Ctrl+L (clear), Ctrl+D (quit)[/dim]
# """)

        self.add_output(welcome_msg_rich, rich_format=True)
        
        # Update footer after setting agent name
        self._update_status()

    def set_agent_task(self, task: asyncio.Task):
        """Set the current agent task for interruption."""
        self.current_agent_task = task
        self.agent_running = True

    def register_input_callback(self, callback: Callable[[str], Awaitable[Any]]):
        """Register a callback function to handle user input."""
        self.input_callback = callback

    def register_interrupt_callback(self, callback: Callable[[], Awaitable[Any]]):
        """Register a callback function to interrupt the agent."""
        self.interrupt_callback = callback

    def watch_agent_running(self, running: bool) -> None:
        """Update footer when agent running status changes."""
        if self.is_mounted:
            self._update_status()

    def watch_agent_thinking(self, thinking: bool) -> None:
        """Update footer when agent thinking status changes."""
        if self.is_mounted:
            self._update_status()

    def watch_agent_name(self, name: str) -> None:
        """Update footer when agent name changes."""
        if self.is_mounted:
            self._update_status()

    def watch__current_time(self, time: str) -> None:
        """Update footer when time changes."""
        if self.is_mounted:
            self._update_status()

    def update_token_usage(self, prompt_tokens: int = 0, thinking_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0, model_name: str = ""):
        """Update token usage information."""
        self._prompt_tokens = prompt_tokens
        self._thinking_tokens = thinking_tokens
        self._output_tokens = output_tokens
        self._total_tokens = total_tokens
        if model_name:
            self._model_name = model_name
        
        # Display token usage in output pane
        if total_tokens > 0:
            if thinking_tokens > 0:
                token_text = Text.from_markup(f"[dim]📊 Token Usage: Prompt: {prompt_tokens:,}, Thinking: {thinking_tokens:,}, Output: {output_tokens:,}, Total: {total_tokens:,}[/dim]")
            else:
                token_text = Text.from_markup(f"[dim]📊 Token Usage: Prompt: {prompt_tokens:,}, Output: {output_tokens:,}, Total: {total_tokens:,}[/dim]")
            
            self.add_output(token_text, rich_format=True)

    def update_tool_usage(self, tool_name: str):
        """Update tool usage information."""
        self._tools_used += 1
        self._last_tool = tool_name
        
        # Display tool usage in thought pane
        if self.agent_thought_enabled:
            tool_text = f"🔧 Tool Used: {tool_name} (Total: {self._tools_used})"
            self.add_thought(tool_text)

    def display_model_usage(self, prompt_tokens: int = 0, completion_tokens: int = 0, 
                           total_tokens: int = 0, thinking_tokens: int = 0, model_name: str = "Unknown"):
        """Display model usage information in the thought pane."""
        # Update internal tracking
        self._prompt_tokens = prompt_tokens
        self._output_tokens = completion_tokens
        self._total_tokens = total_tokens
        self._thinking_tokens = thinking_tokens
        self._model_name = model_name
        
        # Display in thought pane if enabled
        if self.agent_thought_enabled:
            try:
                thought_log = self.query_one("#thought-log", RichLog)
                
                # Create token usage display
                token_parts = []
                if prompt_tokens > 0:
                    token_parts.append(f"Prompt: {prompt_tokens:,}")
                if thinking_tokens > 0:
                    token_parts.append(f"Thinking: {thinking_tokens:,}")
                if completion_tokens > 0:
                    token_parts.append(f"Output: {completion_tokens:,}")
                if total_tokens > 0:
                    token_parts.append(f"Total: {total_tokens:,}")
                
                token_display = ", ".join(token_parts)
                
                token_info_str = f"Tokens: {', '.join(token_parts)}"
                model_info_str = f"Model: {self._model_name}" if self._model_name else ""

                # Use the centralized rich renderer for model usage panel
                content_panel = self.rich_renderer.format_model_usage(f"{token_info_str}\n{model_info_str}")
                thought_log.write(content_panel)
                
            except Exception as e:
                self.add_output(f"📊 Model Usage: {total_tokens} tokens", style="info")
        else:
            # If thoughts are disabled, show in main output as before
            token_parts = []
            if prompt_tokens > 0:
                token_parts.append(f"Prompt: {prompt_tokens:,}")
            if thinking_tokens > 0:
                token_parts.append(f"Thinking: {thinking_tokens:,}")
            if completion_tokens > 0:
                token_parts.append(f"Output: {completion_tokens:,}")
            if total_tokens > 0:
                token_parts.append(f"Total: {total_tokens:,}")
            
            token_display = ", ".join(token_parts)
            self.add_output(f"📊 Model Usage: {total_tokens} tokens", style="info")

    # Removed action_trigger_completion - tab completion is now handled directly by CategorizedInput widget

    def action_history_previous(self) -> None:
        """Navigate to previous command in history."""
        if not self.command_history:
            return
        
        input_widget = self.query_one("#input-area", CategorizedInput)
        
        if self.history_index > 0:
            self.history_index -= 1
            input_widget.value = self.command_history[self.history_index]
        elif self.history_index == 0:
            pass  # Already at first item
        else:
            # Initialize to last item
            self.history_index = len(self.command_history) - 1
            input_widget.value = self.command_history[self.history_index]

    def action_history_next(self) -> None:
        """Navigate to next command in history."""
        if not self.command_history:
            return
            
        input_widget = self.query_one("#input-area", CategorizedInput)
        
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            input_widget.value = self.command_history[self.history_index]
        else:
            # Clear input when going past last item
            self.history_index = len(self.command_history)
            input_widget.value = ""

    def add_tool_event(self, tool_name: str, event_type: str, args: Optional[dict] = None, result: Any = None, duration: Optional[float] = None):
        """Add a tool execution event to the thought pane."""
        if not self.agent_thought_enabled:
            return
            
        try:
            thought_log = self.query_one("#thought-log", RichLog)
            
            if event_type == "start":
                # Tool execution start
                content_panel = self.rich_renderer.format_running_tool(tool_name, args)
                thought_log.write(content_panel)
                
                # Update tool usage tracking
                self._tools_used += 1
                self._last_tool_used = tool_name
                
            elif event_type == "finish":
                # Tool execution finish
                content_panel = self.rich_renderer.format_tool_finished(tool_name, result, duration)
                thought_log.write(content_panel)
                
            elif event_type == "error":
                # Tool execution error
                error_msg = str(result) if result else "Unknown error"
                content_panel = self.rich_renderer.format_tool_error(tool_name, error_msg)
                thought_log.write(content_panel)
                
        except Exception as e:
            # Fallback to regular output if thought pane fails
            self.add_output(f"Tool {event_type}: {tool_name}", style="info")

    def add_agent_thought(self, thought_text: str):
        """Add agent thought to the thought pane."""
        if not self.agent_thought_enabled:
            return
            
        try:
            thought_log = self.query_one("#thought-log", RichLog)
            
            # Format the thought with proper styling using the rich_renderer
            content_panel = self.rich_renderer.format_agent_thought(thought_text)
            thought_log.write(content_panel)
            
        except Exception as e:
            # Fallback to regular output if thought pane fails
            self.add_output(f"💭 {thought_text}", style="info")

    def register_tool_callbacks(self, before_tool_callback, after_tool_callback):
        """Register callbacks for tool execution events."""
        self._before_tool_callback = before_tool_callback
        self._after_tool_callback = after_tool_callback

    def register_thought_callback(self, thought_callback):
        """Register callback for agent thoughts."""
        self._thought_callback = thought_callback

    def set_thinking_state(self, thinking: bool) -> None:
        """Manually control the thinking state (useful for external integrations)."""
        if thinking:
            self.start_thinking()
        else:
            self.stop_thinking()

    def is_thinking(self) -> bool:
        """Check if the agent is currently in thinking state."""
        return self.agent_thinking

class CategorizedInput(Input):
    """
    A custom Input widget that provides tab completion for categorized commands
    and supports navigation through command history.

    This class enhances the standard Textual Input widget by adding features
    useful for a command-line interface, such as:
    - Tab completion: Suggests commands based on user input, categorized for clarity.
    - Command history: Allows users to navigate through previously entered commands
      using the up and down arrow keys.

    Args:
        categorized_commands (dict[str, list[str]]): A dictionary where keys are
            category names (e.g., "File Commands") and values are lists of
            commands belonging to that category.
        *args: Variable length argument list to pass to the parent Input class.
        **kwargs: Arbitrary keyword arguments to pass to the parent Input class.
    """
    def __init__(self, categorized_commands: dict[str, list[str]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categorized_commands = categorized_commands
        self.all_commands = [cmd for cmds in categorized_commands.values() for cmd in cmds]
        # History navigation support
        self.command_history = []
        self.history_index = -1

    def on_key(self, event: Key) -> None:
        """Handle key events for tab completion and history navigation."""
        if event.key == "tab":
            self._handle_tab_completion()
            event.prevent_default()
        elif event.key == "up":
            self._navigate_history(-1)
            event.prevent_default()
        elif event.key == "down":
            self._navigate_history(1)
            event.prevent_default()
        # Let other keys be handled normally

    def _handle_tab_completion(self):
        """Handle tab completion logic."""
        current_text = self.value
        completions = self._get_completions(current_text)
        show_all = not current_text.strip()  # Show all if no text entered
        
        if completions:
            # Show completion dialog
            self.app.push_screen(
                CompletionWidget(completions, self.categorized_commands, show_all),
                self._on_completion_selected
            )
    
    def _on_completion_selected(self, selected_command: str | None) -> None:
        """Handle completion selection from dialog."""
        if selected_command:
            self.value = selected_command

    def _get_completions(self, text: str) -> list[str]:
        """Get completion suggestions for the given text."""
        if not text.strip():
            # Return all commands if no text is entered
            return sorted(self.all_commands)
        
        text_lower = text.lower()
        completions = []
        
        # Find matching commands
        for command in self.all_commands:
            if text_lower in command.lower():
                completions.append(command)
        
        return sorted(completions)

    def _navigate_history(self, direction: int) -> None:
        """Navigate command history."""
        if not self.command_history:
            return

        if direction == -1:  # Up arrow - previous command
            if self.history_index > 0:
                self.history_index -= 1
                self.value = self.command_history[self.history_index]
            elif self.history_index == 0:
                pass  # Already at first item
            else:
                # Initialize to last item
                self.history_index = len(self.command_history) - 1
                self.value = self.command_history[self.history_index]
        elif direction == 1:  # Down arrow - next command
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.value = self.command_history[self.history_index]
            else:
                # Clear input when going past last item
                self.history_index = len(self.command_history)
                self.value = ""

    def add_to_history(self, command: str):
        """Add a command to the history."""
        if command.strip():
            self.command_history.append(command.strip())
            self.history_index = len(self.command_history)

class CompletionWidget(ModalScreen[str]):
    """
    A modal screen widget for displaying and selecting tab completion options.

    This widget appears as a floating dialog when the user requests tab completion
    (e.g., by pressing Tab in the `CategorizedInput` field). It presents a list
    of command suggestions, optionally grouped by categories, allowing the user
    to select a command to insert into the input field.

    Args:
        completions (list[str]): A list of string suggestions for completion.
        categorized_commands (dict[str, list[str]]): A dictionary used to group
            the completions into categories for better organization and display.
        show_all (bool): If True, indicates that all available commands should be
            shown, regardless of the current input. Defaults to False.
        *args: Variable length argument list to pass to the parent ModalScreen class.
        **kwargs: Arbitrary keyword arguments to pass to the parent ModalScreen class.
    """
    
    def __init__(self, completions: list[str], categorized_commands: dict[str, list[str]], show_all: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.completions = completions
        self.categorized_commands = categorized_commands
        self.show_all = show_all

        
    def compose(self) -> ComposeResult:
        """Create the completion widget."""
        # Group completions by category
        options = []
        
        for category, commands in self.categorized_commands.items():
            category_matches = [cmd for cmd in commands if cmd in self.completions]
            if category_matches:
                # Add category header
                options.append(Option(f"{category}", disabled=True))
                # Add commands in this category
                for cmd in category_matches:
                    options.append(Option(f"  {cmd}", id=cmd))
        
        # Add any completions that don't fit in categories
        uncategorized = [cmd for cmd in self.completions if not any(cmd in commands for commands in self.categorized_commands.values())]
        if uncategorized:
            if options:  # Only add separator if there are categorized items
                options.append(Option("─" * 40, disabled=True))
            for cmd in uncategorized:
                options.append(Option(cmd, id=cmd))
        
        # Use different styling based on whether we're showing all options
        dialog_class = "completion-dialog-full" if self.show_all else "completion-dialog"
        title_text = "All Available Commands:" if self.show_all else "Tab Completion - Select an option:"
        
        with Container(id="completion-dialog", classes=dialog_class):
            yield Label(title_text, id="completion-title")
            yield OptionList(*options, id="completion-list")
            yield Label("Press Enter to select, Escape to cancel", id="completion-help")
    
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        if hasattr(event.option, 'id') and event.option.id:  # Skip disabled options
            self.dismiss(event.option.id)
    
    def on_key(self, event: Key) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.dismiss(None)
