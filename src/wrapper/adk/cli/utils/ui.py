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

from typing import Optional

from .ui_common import UITheme
from .ui_rich import RichRenderer
# from .ui_prompt_toolkit import EnhancedCLI, InterruptibleCLI
from .ui_prompt_toolkit import EnhancedCLI
from .ui_textual import AgentTUI


def get_cli_instance(theme: Optional[str] = None) -> EnhancedCLI:
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


def get_interruptible_cli_instance(theme: Optional[str] = None) -> AgentTUI:
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
    
    # return InterruptibleCLI(theme=ui_theme, rich_renderer=rich_renderer)
    return AgentTUI(theme=ui_theme, rich_renderer=rich_renderer)
