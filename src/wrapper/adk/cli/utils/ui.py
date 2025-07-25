from __future__ import annotations

from .ui_common import UITheme
from .ui_prompt_toolkit import EnhancedCLI
from .ui_rich import RichRenderer
from .ui_textual import AgentTUI


def get_cli_instance(theme: str | None = None) -> EnhancedCLI:
    """Factory function to create an EnhancedCLI instance with optional theme."""
    ui_theme = None
    if theme:
        try:
            ui_theme = UITheme(theme.lower())
        except ValueError:
            # Invalid theme, use default
            ui_theme = None

    # Create RichRenderer with the theme
    rich_renderer = RichRenderer(ui_theme) if ui_theme else None

    return EnhancedCLI(theme=ui_theme, rich_renderer=rich_renderer)


def get_textual_cli_instance(theme: str | None = None) -> AgentTUI:
    """Factory function to create an AgentTUI (Textual) instance with optional theme."""
    ui_theme = None
    if theme:
        try:
            ui_theme = UITheme(theme.lower())
        except ValueError:
            # Invalid theme, use default
            ui_theme = None

    # Create RichRenderer with the theme
    rich_renderer = RichRenderer(ui_theme) if ui_theme else None

    return AgentTUI(theme=ui_theme, rich_renderer=rich_renderer)
