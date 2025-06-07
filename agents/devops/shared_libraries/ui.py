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

def display_model_usage_with_thinking(console: Console, prompt_tokens: Any, completion_tokens: Any, thinking_tokens: Any, total_tokens: Any):
    """Displays model token usage including thinking tokens in a Rich panel."""
    try:
        content = Text.from_markup(
            f"[dim][b]Token Usage:[/b] Prompt: {prompt_tokens}, "
            f"[cyan]Thinking: {thinking_tokens}[/cyan], "
            f"Output: {completion_tokens}, Total: {total_tokens}[/dim]"
        )
        panel = Panel(
            content,
            title="[blue]🧠 Model Usage (with Thinking)[/blue]",
            border_style="blue",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying model usage with thinking: {e}")

def display_agent_thought(console: Console, thought_summaries: list):
    """Displays agent thought summaries in a Rich panel."""
    try:
        logger.info(f"display_agent_thought called with {len(thought_summaries) if thought_summaries else 0} summaries")
        if not thought_summaries:
            logger.info("No thought summaries to display, returning early")
            return
            
        # Combine multiple thought summaries if present
        combined_thoughts = "\n\n".join(thought_summaries)
        
        # Truncate very long thoughts for display
        max_display_length = 800
        if len(combined_thoughts) > max_display_length:
            display_text = combined_thoughts[:max_display_length] + "..."
        else:
            display_text = combined_thoughts
        
        content = Text.from_markup(f"[dim]{escape(display_text)}[/dim]")
        panel = Panel(
            content,
            title="[magenta]🧠 Agent Thought[/magenta]",
            border_style="magenta",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying agent thought: {e}")

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

def display_tool_error(console: Console, tool_name: str, error_response: dict, duration: float):
    """Displays a tool error in a Rich panel."""
    try:
        error_message = error_response.get("message", "Unknown error")
        error_summary = escape(error_message[:500])
        content = Text.from_markup(
            f"[dim][b]Tool:[/b] {escape(tool_name)}\n"
            f"[b]Error:[/b] {error_summary}{'...' if len(error_message) > 500 else ''}\n"
            f"[b]Duration:[/b] {duration:.4f} seconds[/dim]"
        )
        panel = Panel(
            content,
            title="[red]❌ Tool Error[/red]",
            border_style="red",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying tool error: {e}")

def display_tool_error_with_suggestions(console: Console, tool_name: str, error_response: dict, duration: float):
    """Displays a tool error with suggestions in a Rich panel."""
    try:
        error_message = error_response.get("message", "Unknown error")
        suggestions = error_response.get("suggestions", [])
        alternatives_tried = error_response.get("alternatives_tried", [])
        
        # Split message at the suggestion marker if present
        if "💡" in error_message:
            base_error, suggestion_text = error_message.split("💡", 1)
            base_error = base_error.strip()
            suggestion_text = "💡" + suggestion_text
        else:
            base_error = error_message
            suggestion_text = ""
        
        content_parts = [
            f"[dim][b]Tool:[/b] {escape(tool_name)}[/dim]",
            f"[red][b]Error:[/b] {escape(base_error[:300])}{'...' if len(base_error) > 300 else ''}[/red]"
        ]
        
        if suggestion_text:
            content_parts.append(f"[yellow]{escape(suggestion_text)}[/yellow]")
        
        if alternatives_tried:
            content_parts.append(f"[dim][b]Alternatives Tried:[/b] {len(alternatives_tried)}[/dim]")
        
        if suggestions:
            content_parts.append(f"[blue][b]Additional Suggestions:[/b] {len(suggestions)} available[/blue]")
        
        content_parts.append(f"[dim][b]Duration:[/b] {duration:.4f} seconds[/dim]")
        
        content = Text.from_markup("\n".join(content_parts))
        panel = Panel(
            content,
            title="[red]❌ Tool Error with Recovery Options[/red]",
            border_style="red",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying tool error with suggestions: {e}")

def display_retry_suggestions(console: Console, command: str, suggestions: list):
    """Displays command retry suggestions in a Rich panel."""
    try:
        content_parts = [
            f"[b]Original Command:[/b] {escape(command[:100])}{'...' if len(command) > 100 else ''}",
            "[b]Suggested Alternatives:[/b]"
        ]
        
        for i, suggestion in enumerate(suggestions[:5], 1):  # Show max 5 suggestions
            if suggestion.startswith("#"):
                content_parts.append(f"  [dim]{escape(suggestion)}[/dim]")
            else:
                content_parts.append(f"  {i}. [cyan]{escape(suggestion)}[/cyan]")
        
        if len(suggestions) > 5:
            content_parts.append(f"  [dim]... and {len(suggestions) - 5} more suggestions[/dim]")
        
        content = Text.from_markup("\n".join(content_parts))
        panel = Panel(
            content,
            title="[yellow]💡 Command Retry Suggestions[/yellow]",
            border_style="yellow",
            expand=False
        )
        console.print(panel)
    except Exception as e:
        logger.error(f"Error displaying retry suggestions: {e}")

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
