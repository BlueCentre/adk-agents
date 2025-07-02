"""Debugging Agent Implementation."""

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

# Import codebase search tool from the tools module
from ...tools import codebase_search_tool
from ...tools.filesystem import (
    configure_approval_tool,
    edit_file_tool,
    list_dir_tool,
    read_file_tool,
)
from ...tools.search import google_search_grounding
from ...tools.shell_command import (
    check_command_exists_tool,
    check_shell_command_safety_tool,
    configure_shell_approval_tool,
    configure_shell_whitelist_tool,
    execute_vetted_shell_command_tool,
)
from ...tools.system_info import get_os_info
from . import prompt

debugging_agent = LlmAgent(
    model="gemini-1.5-pro-001",
    name="debugging_agent",
    description="Agent specialized in debugging code and fixing issues",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    tools=[
        read_file_tool,
        list_dir_tool,
        configure_approval_tool,
        edit_file_tool,
        configure_shell_approval_tool,
        configure_shell_whitelist_tool,
        check_command_exists_tool,
        check_shell_command_safety_tool,
        execute_vetted_shell_command_tool,
        get_os_info,
        google_search_grounding,
        codebase_search_tool,
    ],
    output_key="debugging",
    generate_content_config=GenerateContentConfig(
        temperature=0.8,
        top_p=0.95,
        max_output_tokens=4096,
    ),
)

# Placeholder for actual tool implementation
