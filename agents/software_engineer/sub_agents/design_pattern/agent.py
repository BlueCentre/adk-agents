"""Design Pattern Agent Implementation."""

from google.adk.agents import LlmAgent

from ... import config as agent_config
from ...tools.code_search import codebase_search_tool
from ...tools.filesystem import (
    edit_file_content_tool,
    list_directory_contents_tool,
    read_file_content_tool,
)
from ...tools.shell_command import execute_shell_command_tool
from . import prompt


def create_design_pattern_agent(name_prefix: str = "") -> LlmAgent:
    """
    Factory function to create a design pattern agent instance.

    Args:
        name_prefix: Optional prefix for the agent name to ensure uniqueness

    Returns:
        LlmAgent: Configured design pattern agent instance
    """
    agent_name = f"{name_prefix}design_pattern_agent" if name_prefix else "design_pattern_agent"

    return LlmAgent(
        model=agent_config.DEFAULT_SUB_AGENT_MODEL,
        name=agent_name,
        description="Agent specialized in applying design patterns and architectural principles",
        instruction=prompt.DESIGN_PATTERN_AGENT_INSTR,
        tools=[
            read_file_content_tool,
            list_directory_contents_tool,
            edit_file_content_tool,
            codebase_search_tool,
            execute_shell_command_tool,
            # google_search_grounding,
        ],
        output_key="design_pattern",
    )


# Create the default instance for backward compatibility
design_pattern_agent = create_design_pattern_agent()
