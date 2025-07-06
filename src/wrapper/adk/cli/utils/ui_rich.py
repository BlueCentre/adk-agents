from __future__ import annotations

# import shutil
# from io import StringIO
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
        self.console = Console(theme=self.rich_theme)
        self.markdown_enabled = True

    def format_message(self, text: str | Text, author: str, rich_format: bool = False, style: str = "") -> Text:
        if isinstance(text, Text):
            return text

        if rich_format:
            return Text.from_markup(text)

        # Simple text with author prefix
        message = Text()
        if author:
            message.append(f"{author}: ", style="bold")
        message.append(text, style=style)
        return message

    def format_agent_response(self, text: str, author: str = "Agent") -> Panel:
        markdown = Markdown(text, style="agent")
        return Panel(
            markdown,
            title=f"[bold {self.rich_theme.styles.get('agent.border_color', 'green')}]🤖 {author} Response[/bold {self.rich_theme.styles.get('agent.border_color', 'green')}]",
            title_align="left",
            border_style=self.rich_theme.styles.get("agent.border_color", "green"),
            expand=True,
            # highlight=True,
            # padding=(0, 0),
        )

    def format_agent_thought(self, text: str) -> Panel:
        markdown = Markdown(text, style="thought")
        return Panel(
            markdown,
            title=f"[bold {self.rich_theme.styles.get('thought.border_color', 'magenta')}]🧠 Agent Thought[/bold {self.rich_theme.styles.get('thought.border_color', 'magenta')}]",
            title_align="left",
            border_style=self.rich_theme.styles.get("thought.border_color", "magenta"),
            expand=True,
            highlight=True,
            padding=(0, 0),
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
        arg_str = f"({', '.join(f'{k}={v}' for k, v in args.items())})" if args else "()"
        content = Text.from_markup(
            f"[dim]Tool: {tool_name}{arg_str}[/dim]"
        )
        return Panel(
            content,
            title="[cyan]🔧 Running Tool[/cyan]",
            title_align="left",
            border_style="cyan",
            expand=True,
            padding=(0, 0),
        )

    def format_tool_finished(self, tool_name: str, result: Any, duration: Optional[float]) -> Panel:
        duration_str = f" in {duration:.2f}s" if duration is not None else ""
        result_str = f"Result: {str(result)[:100]}..." if len(str(result)) > 100 else f"Result: {result}"
        content = Text.from_markup(
            f"[dim]Tool: {tool_name}{duration_str}\n"
            f"{result_str}[/dim]"
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
            f"[dim]Tool: {tool_name}\n"
            f"Error: {error_message}[/dim]"
        )
        return Panel(
            content,
            title="[red]❌ Tool Error[/red]",
            title_align="left",
            border_style="red",
            expand=True,
            padding=(0, 0),
        )

    # def format_agent_response_panel(self, text: str, author: str) -> Panel:
    #     """Format agent response with themed panel and return Panel object."""
    #     markdown_text = Markdown(text)

    #     if self.theme == UITheme.DARK:
    #         border_style = "green"
    #         title_style = "bold green"
    #     else:
    #         border_style = "dark_green"
    #         title_style = "bold dark_green"

    #     return Panel(
    #         markdown_text,
    #         title=f"🤖 [{title_style}]{author}[/{title_style}]",
    #         border_style=border_style,
    #         expand=False,  # Don't expand to avoid extra width issues
    #         padding=(0, 1)  # Minimal padding to prevent over-indentation
    #     )

    # def format_agent_response_str(self, text: str, author: str) -> str:
    #     """Format agent response with themed panel and render to string."""
    #     panel = self.format_agent_response_panel(text, author)

    #     # Get terminal size and calculate appropriate width for the pane
    #     try:
    #         terminal_width = shutil.get_terminal_size().columns
    #         # Account for frame borders and padding - leave some margin
    #         # panel_width = max(80, terminal_width - 6)  # Minimum 80, subtract for borders/padding
    #         panel_width = max(80, terminal_width)  # Minimum 80, subtract for borders/padding
    #     except:
    #         panel_width = 120  # Fallback width

    #     # Render panel to string format that works with prompt_toolkit
    #     string_io = StringIO()
    #     temp_console = Console(
    #         file=string_io,
    #         force_terminal=False,
    #         width=panel_width,  # Use calculated width to fit the pane
    #         legacy_windows=False,
    #     )

    #     # Print the panel
    #     temp_console.print(panel, crop=False, overflow="ignore")
    #     panel_text = string_io.getvalue()

    #     return panel_text.rstrip()

    # def print_markdown(self, markdown_text: str, style: Optional[str] = None):
    #     self.console.print(Markdown(markdown_text, style=style))

    # def print_panel(self, content: Any, title: Optional[str] = None, border_style: Optional[str] = None):
    #     self.console.print(Panel(content, title=title, border_style=border_style))

    # def print_text(self, text: str, style: Optional[str] = None):
    #     self.console.print(Text(text, style=style))

    # def _render_markdown(self, text: str) -> str:
    #     """Render markdown using Rich's Markdown directly, without Panel wrapper."""
    #     if not self.markdown_enabled:
    #         return text
            
    #     try:
    #         markdown_obj = Markdown(text)
            
    #         # Render to plain text that works in prompt_toolkit
    #         string_io = StringIO()
    #         temp_console = Console(
    #             file=string_io,
    #             force_terminal=False,
    #             width=None,  # Much wider to prevent truncation
    #             legacy_windows=False,
    #         )
            
    #         # Print the markdown object directly (with Panel wrapper)
    #         temp_console.print(markdown_obj, crop=False, overflow="ignore", soft_wrap=True)
    #         rendered_output = string_io.getvalue()
            
    #         return rendered_output.rstrip()
            
    #     except ImportError:
    #         # Fallback to basic markdown if Rich is not available
    #         return self._basic_markdown_fallback(text)
    #     except Exception as e:
    #         # If Rich markdown fails, fall back to basic rendering
    #         return self._basic_markdown_fallback(text)

    # def _basic_markdown_fallback(self, text: str) -> str:
    #     """Basic markdown rendering fallback if Rich fails."""
    #     import re
        
    #     formatted_text = text
        
    #     # Headers with better styling
    #     formatted_text = re.sub(r'^# (.+)$', r'🔷 \1', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^## (.+)$', r'🔸 \1', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^### (.+)$', r'▪️ \1', formatted_text, flags=re.MULTILINE)
        
    #     # Basic bold and italic (simplified)
    #     formatted_text = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', formatted_text)  # Keep bold markers
    #     formatted_text = re.sub(r'\*([^*]+)\*', r'*\1*', formatted_text)  # Keep italic markers
        
    #     # Lists
    #     formatted_text = re.sub(r'^\* ', '• ', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^\+ ', '• ', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^\- ', '• ', formatted_text, flags=re.MULTILINE)
        
    #     # Blockquotes
    #     formatted_text = re.sub(r'^> (.+)$', r'┃ \1', formatted_text, flags=re.MULTILINE)
        
    #     # Code (simplified)
    #     formatted_text = re.sub(r'`([^`]+)`', r'`\1`', formatted_text)  # Keep code markers
    #     formatted_text = re.sub(r'^#### (.+)$', r'  • \1', formatted_text, flags=re.MULTILINE)
        
    #     # Bold and italic - preserve some emphasis
    #     formatted_text = re.sub(r'\*\*(.+?)\*\*', r'[\1]', formatted_text)  # Bold in brackets
    #     formatted_text = re.sub(r'__(.+?)__', r'[\1]', formatted_text)
    #     formatted_text = re.sub(r'\*([^*]+?)\*', r'(\1)', formatted_text)  # Italic in parentheses
    #     formatted_text = re.sub(r'_([^_]+?)_', r'(\1)', formatted_text)
        
    #     # Code blocks with language detection
    #     def format_code_block(match):
    #         lang = match.group(1) or 'text'
    #         code = match.group(2).strip()
    #         return f'💻 {lang.upper()} Code:\n{code}\n'
        
    #     formatted_text = re.sub(r'```(\w+)?\n(.*?)\n```', format_code_block, formatted_text, flags=re.DOTALL)
        
    #     # Inline code with backticks
    #     formatted_text = re.sub(r'`([^`]+?)`', r'`\1`', formatted_text)
        
    #     # Lists with better bullets
    #     formatted_text = re.sub(r'^\- (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^\* (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^\+ (.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
        
    #     # Numbered lists with emojis
    #     formatted_text = re.sub(r'^1\. (.+)$', r'1️⃣ \1', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^2\. (.+)$', r'2️⃣ \1', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^3\. (.+)$', r'3️⃣ \1', formatted_text, flags=re.MULTILINE)
    #     formatted_text = re.sub(r'^(\d+)\. (.+)$', r'\1. \2', formatted_text, flags=re.MULTILINE)
        
    #     # Links - show both text and URL
    #     formatted_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1 (\2)', formatted_text)
        
    #     # Blockquotes with better styling
    #     formatted_text = re.sub(r'^> (.+)$', r'💬 \1', formatted_text, flags=re.MULTILINE)
        
    #     # Horizontal rules
    #     formatted_text = re.sub(r'^---+$', r'─' * 50, formatted_text, flags=re.MULTILINE)
        
    #     # Tables - basic support
    #     def format_table_row(match):
    #         cells = [cell.strip() for cell in match.group(0).split('|')[1:-1]]
    #         return ' │ '.join(cells)
        
    #     formatted_text = re.sub(r'^\|(.+)\|$', format_table_row, formatted_text, flags=re.MULTILINE)
        
    #     return formatted_text
