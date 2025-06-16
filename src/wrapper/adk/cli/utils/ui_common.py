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

from rich.theme import Theme
from rich.console import Console


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

    @staticmethod
    def get_rich_theme(theme: UITheme) -> Theme:
        """Get a Rich Theme based on the UI theme."""
        if theme == UITheme.DARK:
            return Theme(
                {
                    "info": "green",
                    "warning": "yellow",
                    "error": "bold red",
                    "success": "green",
                    "accent": "yellow",
                    "highlight": "cyan",
                    "user": "cyan italic",
                    "agent": "yellow",
                    "welcome": "bold magenta",
                    "agent.border_color": "blue",
                    "thought.border_color": "magenta",
                    "bottom-toolbar": "#cccccc on #004488",
                    "bottom-toolbar.accent": "#FFD700 on #004488",
                    "bottom-toolbar.info": "#ADD8E6 on #004488",
                }
            )
        else: # UITheme.LIGHT
            return Theme(
                {
                    "info": "green",
                    "warning": "yellow",
                    "error": "bold red",
                    "success": "green",
                    "accent": "yellow",
                    "highlight": "blue",
                    "user": "cyan italic",
                    "agent": "red",
                    "welcome": "bold magenta",
                    "agent.border_color": "blue",
                    "thought.border_color": "magenta",
                    "bottom-toolbar": "#111111 on #bbbbbb",
                    "bottom-toolbar.accent": "#CD853F on #bbbbbb",
                    "bottom-toolbar.info": "#4682B4 on #bbbbbb",
                }
            )


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


def get_cli_instance(theme: Optional[str] = None):
    """Factory function to create a CLI instance with the specified theme."""
    from .ui_prompt_toolkit import EnhancedCLI
    from .ui_rich import RichRenderer
    ui_theme: Optional[UITheme] = None
    if theme:
        try:
            ui_theme = UITheme(theme.lower())
        except ValueError:
            pass  # Use auto-detected theme
    
    rich_renderer = RichRenderer(ui_theme)
    return EnhancedCLI(ui_theme, rich_renderer)

def get_interruptible_cli_instance(theme: Optional[str] = None):
    """Factory function to create an InterruptibleCLI instance with enhanced agent response formatting."""
    from .ui_prompt_toolkit import InterruptibleCLI
    from .ui_rich import RichRenderer
    ui_theme: Optional[UITheme] = None
    if theme:
        try:
            ui_theme = UITheme(theme.lower())
        except ValueError:
            pass  # Use auto-detected theme
    
    rich_renderer = RichRenderer(ui_theme)
    return InterruptibleCLI(ui_theme, rich_renderer)
