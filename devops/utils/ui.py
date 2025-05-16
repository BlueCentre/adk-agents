# Agents/devops/ui_utils.py
import logging
from typing import Optional, Any

from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.text import Text
from rich.markup import escape

logger = logging.getLogger(__name__)

# --- Status Spinner Management ---
def start_status_spinner(console: Console, message: str) -> Status:
    """Starts and returns a Rich status spinner."""
    status_indicator = console.status(message)
    status_indicator.start()
    return status_indicator

def stop_status_spinner(status_indicator: Optional[Status]):
    """Stops a Rich status spinner if it exists."""
    if status_indicator:
        status_indicator.stop()

# --- Panel Displays ---
def display_model_usage(console: Console, prompt_tokens: Any, completion_tokens: Any, total_tokens: Any):
    """Displays model token usage in a Rich panel."""
    try:
        content = Text.from_markup(
            f"[dim][b]Token Usage:[/b] Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}[/dim]"
        )
        panel = Panel(
            content,
            title="[blue]📊 Model Usage[/blue]",
            border_style="blue",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying model usage: {e}")

def display_tool_execution_start(console: Console, tool_name: str, args: dict):
    """Displays the start of a tool execution in a Rich panel."""
    try:
        tool_args_display = ", ".join([f"{k}={v}" for k, v in args.items()])
        if len(tool_args_display) > 100:
            tool_args_display = tool_args_display[:97] + "..."
        
        content = Text.from_markup(f"[dim][b]Tool:[/b] {escape(tool_name)}\n[b]Args:[/b] {escape(tool_args_display)}[/dim]")
        panel = Panel(
            content,
            title="[cyan]🔧 Running Tool[/cyan]",
            border_style="cyan",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying tool execution start: {e}")

def display_tool_finished(console: Console, tool_name: str, result: Any, duration: float):
    """Displays the result of a tool execution in a Rich panel."""
    try:
        result_summary = escape(str(result)[:300])
        content = Text.from_markup(
            f"[dim][b]Tool:[/b] {escape(tool_name)}\n"
            f"[b]Result:[/b] {result_summary}{'...' if len(str(result)) > 300 else ''}\n"
            f"[b]Duration:[/b] {duration:.4f} seconds[/dim]"
        )
        panel = Panel(
            content,
            title="[green]✅ Tool Finished[/green]",
            border_style="green",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying tool finished: {e}")

def display_unhandled_error(console: Console, error_type: str, error_message: str, mcp_hint: str):
    """Displays an unhandled agent error in a Rich panel."""
    try:
        rich_error_message_display = f"Type: {escape(error_type)}\nMessage: {escape(error_message)}\n{escape(mcp_hint) if mcp_hint else ''}"
        panel = Panel(
            Text.from_markup(f"""[bold red]💥 Unhandled Agent Error[/bold red]\n{rich_error_message_display}"""
            ),
            title="[red]Critical Error[/red]",
            border_style="red"
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying unhandled error panel: {e}")

# --- Simple Text Messages (can be expanded) ---
def print_message(console: Console, message: str, style: str = ""):
    """Prints a simple message to the console, optionally styled."""
    try:
        if style:
            console.print(f"[{style}]{escape(message)}[/{style}]")
        else:
            console.print(escape(message))
    except Exception as e:
        logger.error(f"Error printing message: {e}")

