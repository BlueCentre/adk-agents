from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from .ui_common import ThemeConfig, UITheme


class RichRenderer:
    """Handles rendering of Rich components and markdown."""

    def __init__(self, theme: Optional[UITheme] = None):
        self.theme = theme or UITheme.DARK
        self.rich_theme = ThemeConfig.get_rich_theme(self.theme)
        # self.console = Console(theme=self.rich_theme, force_interactive=True)
        self.console = Console(
            theme=self.rich_theme,
            soft_wrap=True,  # Enable soft wrapping for proper text wrapping
            width=None,  # Auto-detect width
            legacy_windows=False,  # Use modern terminal features
        )
        self.markdown_enabled = True

    def format_message(
        self,
        text: str | Text,
        author: str,
        rich_format: bool = False,
        style: str = "",
        markdown: bool = False,
    ) -> Text:
        """
        Formats a given text message, optionally prepending an author and applying Rich formatting.

        Args:
            text (str | Text): The message content to format. Can be a string or a Rich Text object.
            author (str): The author of the message. If provided, it will be prepended to the message.
            rich_format (bool): If True, the text will be parsed as Rich markup. Defaults to False.
            style (str): The Rich style to apply to the message text. Defaults to an empty string.
            markdown (bool): If True, the text will be parsed as markdown. Defaults to False.

        Returns:
            Text: A Rich Text object representing the formatted message.
        """
        if isinstance(text, Text):
            return text

        if rich_format:
            return Text.from_markup(text)

        # Handle markdown rendering
        if markdown:
            from rich.markdown import Markdown

            # Create markdown object and render it to a Text object
            markdown_obj = Markdown(text, style="agent")

            # Use console's render method to get a Text object with proper formatting
            segments = list(self.console.render(markdown_obj))
            rendered_text = Text()
            for segment in segments:
                rendered_text.append(segment.text, style=segment.style)

            # Create final message with author prefix
            message = Text()
            if author:
                message.append(f"🤖 {author} > ", style="bold green")
            message.append(rendered_text)
            return message

        # Simple text with author prefix
        message = Text()
        if author:
            message.append(f"🤖 {author} > ", style="bold green")
        message.append(text, style=style)
        return message

    def format_agent_response(self, text: str, author: str = "Agent") -> Panel:
        markdown = Markdown(text, style="agent")
        return Panel(
            markdown,
            title=f"[bold {self.rich_theme.styles.get('agent.border_color', 'green')}]🤖 {author} Response[/bold {self.rich_theme.styles.get('agent.border_color', 'green')}]",
            title_align="center",
            border_style=self.rich_theme.styles.get("agent.border_color", "green"),
            expand=True,
            # highlight=True,
            # padding=(0, 1),
        )

    def format_agent_thought(self, text: str) -> Panel:
        markdown = Markdown(text, style="thought")
        return Panel(
            markdown,
            title=f"[bold {self.rich_theme.styles.get('thought.border_color', 'magenta')}]🧠 Agent Thought[/bold {self.rich_theme.styles.get('thought.border_color', 'magenta')}]",
            title_align="center",
            border_style=self.rich_theme.styles.get("thought.border_color", "magenta"),
            expand=True,
            # highlight=True,
            # padding=(0, 0),
        )

    def format_model_usage(self, text: str) -> Panel:
        return Panel(
            Text.from_markup(f"[dim]{text}[/dim]"),
            title="[blue]📊 Model Usage[/blue]",
            title_align="left",
            border_style="blue",
            expand=True,
            padding=(0, 0),
        )

    def format_running_tool(self, tool_name: str, args: Optional[dict]) -> Panel:
        arg_str = (
            f"({', '.join(f'{k}={v}' for k, v in args.items())})" if args else "()"
        )
        content = Text.from_markup(f"[dim]Tool: {tool_name}{arg_str}[/dim]")
        return Panel(
            content,
            title="[cyan]🔧 Running Tool[/cyan]",
            title_align="left",
            border_style="cyan",
            expand=True,
            padding=(0, 0),
        )

    def format_tool_finished(
        self, tool_name: str, result: Any, duration: Optional[float]
    ) -> Panel:
        duration_str = f" in {duration:.2f}s" if duration is not None else ""
        result_str = (
            f"Result: {str(result)[:100]}..."
            if len(str(result)) > 100
            else f"Result: {result}"
        )
        content = Text.from_markup(
            f"[dim]Tool: {tool_name}{duration_str}\n{result_str}[/dim]"
        )
        return Panel(
            content,
            title="[green]✅ Tool Finished[/green]",
            title_align="left",
            border_style="green",
            expand=True,
            padding=(0, 0),
        )

    def format_tool_error(self, tool_name: str, error_message: str) -> Panel:
        content = Text.from_markup(
            f"[dim]Tool: {tool_name}\nError: {error_message}[/dim]"
        )
        return Panel(
            content,
            title="[red]❌ Tool Error[/red]",
            title_align="left",
            border_style="red",
            expand=True,
            padding=(0, 0),
        )
